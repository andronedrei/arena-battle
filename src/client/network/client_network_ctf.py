"""
CTF Client Network - extends base client with CTF message handling.

Handles CTF state messages from server.
"""

import asyncio
import threading
import queue

import websockets

from common.config import (
    NETWORK_SERVER_URI,
    MSG_TYPE_ENTITIES,
    MSG_TYPE_WALLS,
    MSG_TYPE_BULLETS,
    MSG_TYPE_CLIENT_READY,
    MSG_TYPE_START_GAME,
    MSG_TYPE_CTF_STATE,
)
from common.logger import get_logger

logger = get_logger(__name__)


class ClientNetworkCTF:
    """
    WebSocket client for CTF game mode.
    
    Extends base client with CTF state message handling.
    """
    
    def __init__(self, scene, uri: str = NETWORK_SERVER_URI) -> None:
        """
        Initialize CTF network client.
        
        Args:
            scene: Scene object with on_*_update callback methods.
            uri: WebSocket server URI.
        """
        self.scene = scene
        self.uri = uri
        self.running = False
        self._send_queue = queue.Queue()
        self._ws = None
        self._connected = False
        self._ready_sent = False
    
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
        """Connect to server and receive messages until stopped."""
        try:
            async with websockets.connect(self.uri) as ws:
                self._ws = ws
                self._connected = True
                logger.info("Connected to CTF server: %s", self.uri)
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
        except (OSError, websockets.exceptions.WebSocketException):
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
        elif msg_type == MSG_TYPE_CTF_STATE:
            # New CTF-specific message
            self.scene.on_ctf_update(payload)
        elif msg_type == MSG_TYPE_START_GAME:
            logger.info("Received START_GAME from server")
            try:
                import sys
                from pyglet.clock import schedule_once
                
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
                            window_instance_inner.scene_manager.switch_to("gameplay_ctf")
                            logger.info("Switched to CTF gameplay scene")
                        else:
                            if attempt < 10:
                                schedule_once(lambda dt: _attempt_switch(attempt + 1, dt), 0.05)
                            else:
                                logger.warning("Failed to switch to CTF gameplay scene after multiple attempts")
                    except Exception as e:
                        logger.exception("Error switching scene on main thread: %s", e)
                
                schedule_once(lambda dt: _attempt_switch(0, dt), 0.0)
            except Exception as e:
                logger.exception("Error handling START_GAME: %s", e)
    
    # Outgoing message handling
    
    async def _drain_send_queue(self, ws) -> None:
        """Background task to send queued outgoing messages."""
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
                pass
    
    def send_ready(self) -> None:
        """Put a client-ready message into the outgoing queue."""
        if self._ready_sent:
            logger.info("Ready message already sent; skipping duplicate")
            return
        
        self._ready_sent = True
        self._send_queue.put(bytes([MSG_TYPE_CLIENT_READY]))
        logger.info("Enqueued ready message for CTF game")
