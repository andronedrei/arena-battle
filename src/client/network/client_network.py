# External libraries
import asyncio
import threading
import queue

import websockets


# Internal libraries
from common.config import (
    NETWORK_SERVER_URI,
    MSG_TYPE_ENTITIES,
    MSG_TYPE_WALLS,
    MSG_TYPE_BULLETS,
    MSG_TYPE_CLIENT_READY,
    MSG_TYPE_START_GAME,
    MSG_TYPE_KOTH_STATE,
    MSG_TYPE_MODE_SELECTED,
    GAME_MODE_KOTH,
    GAME_MODE_SURVIVAL,
)
from common.logger import get_logger

logger = get_logger(__name__)


class ClientNetwork:
    """
    WebSocket client that runs in a background thread.

    Maintains connection to server and dispatches received packets
    to scene callbacks.
    """

    def __init__(self, scene, uri: str = NETWORK_SERVER_URI) -> None:
        """
        Initialize network client.

        Args:
            scene: Scene object with on_*_update callback methods.
            uri: WebSocket server URI.
        """
        self.scene = scene
        self.uri = uri
        self.running = False
        # Thread-safe queue for outgoing messages
        self._send_queue = queue.Queue()
        self._ws = None
        # indicate whether websocket is currently connected
        self._connected = False
        # ensure we only enqueue a ready message once per client instance
        self._ready_sent = False
        # Track selected game mode
        self.selected_mode = None

    # Connection management

    def start(self) -> None:
        """Start the network connection in a background thread."""
        self.running = True
        thread = threading.Thread(target=self._run_loop, daemon=True)
        thread.start()

    def stop(self) -> None:
        """Stop the network connection."""
        self.running = False

    # Internal loop

    def _run_loop(self) -> None:
        """Run the WebSocket connection in a background thread."""
        asyncio.run(self._connect())

    async def _connect(self) -> None:
        """
        Connect to server and receive messages until stopped.

        Handles connection errors gracefully and maintains connection state.
        """
        try:
            async with websockets.connect(self.uri) as ws:
                self._ws = ws
                self._connected = True
                logger.info("Connected to server: %s", self.uri)
                send_task = asyncio.create_task(self._drain_send_queue(ws))
                try:
                    async for message in ws:
                        if not self.running:
                            break

                        try:
                            await self._handle_message(message)
                        except (ValueError, RuntimeError):
                            continue
                finally:
                    send_task.cancel()
                    self._connected = False
        except (
            OSError,
            websockets.exceptions.WebSocketException,
        ):
            pass

    async def _handle_message(self, data: bytes) -> None:
        """Parse and dispatch message to appropriate scene callback."""
        if not data or len(data) < 1:
            return
        
        msg_type = data[0]
        payload = data[1:]
        
        if msg_type == MSG_TYPE_ENTITIES:
            self.scene.on_entities_update(payload)
        elif msg_type == MSG_TYPE_WALLS:
            self.scene.on_walls_update(payload)
        elif msg_type == MSG_TYPE_BULLETS:
            self.scene.on_bullets_update(payload)
        elif msg_type == MSG_TYPE_KOTH_STATE:
            # Handle KOTH state if scene supports it
            if hasattr(self.scene, 'on_koth_update'):
                self.scene.on_koth_update(payload)
        elif msg_type == MSG_TYPE_MODE_SELECTED:
            # Server confirmed mode selection
            if len(data) >= 2:
                mode = data[1]
                self.selected_mode = mode  # Store the mode
                mode_name = "KOTH" if mode == GAME_MODE_KOTH else "Survival"
                logger.info("Server confirmed mode: %s", mode_name)
        elif msg_type == MSG_TYPE_START_GAME:
            logger.info("Received START_GAME from server")
            try:
                import sys
                from pyglet.clock import schedule_once
                
                # Determine which scene to switch to based on selected mode
                def _attempt_switch(attempt: int, dt: float) -> None:
                    try:
                        main_mod_inner = sys.modules.get("__main__")
                        window_instance_inner = None
                        if main_mod_inner is not None:
                            window_instance_inner = getattr(main_mod_inner, "window_instance", None)
                        
                        if window_instance_inner is None:
                            try:
                                import client.main as client_main_mod_inner
                                window_instance_inner = getattr(client_main_mod_inner, "window_instance", None)
                            except Exception:
                                window_instance_inner = None
                        
                        if window_instance_inner and getattr(window_instance_inner, "scene_manager", None):
                            # Switch to correct scene based on mode
                            if self.selected_mode == GAME_MODE_KOTH:
                                scene_name = "gameplay_koth"
                                logger.info("Switching to KOTH gameplay scene")
                            else:
                                scene_name = "gameplay"
                                logger.info("Switching to Survival gameplay scene")
                            
                            window_instance_inner.scene_manager.switch_to(scene_name)
                            logger.info("Switched to %s scene", scene_name)
                        else:
                            if attempt < 10:
                                schedule_once(lambda dt: _attempt_switch(attempt + 1, dt), 0.05)
                            else:
                                logger.warning("Failed to switch to gameplay scene after multiple attempts")
                    except Exception as e:
                        logger.exception("Error switching scene on main thread: %s", e)
                
                schedule_once(lambda dt: _attempt_switch(0, dt), 0.0)
            except Exception as e:
                logger.exception("Error handling START_GAME: %s", e)

    # Outgoing message handling (thread-safe)

    async def _drain_send_queue(self, ws) -> None:
        """Background task to send queued outgoing messages over ws."""
        import queue as _queue

        while self.running:
            try:
                msg = self._send_queue.get_nowait()
            except _queue.Empty:
                await asyncio.sleep(0.05)
                continue

            try:
                await ws.send(msg)
            except Exception:
                # ignore send errors
                pass

    def send_ready(self) -> None:
        """Put a client-ready message into the outgoing queue (thread-safe)."""
        # avoid enqueueing multiple ready messages from repeated clicks
        if self._ready_sent:
            logger.info("Ready message already sent; skipping duplicate")
            return

        self._ready_sent = True
        self._send_queue.put(bytes([MSG_TYPE_CLIENT_READY]))
        logger.info("Enqueued ready message")