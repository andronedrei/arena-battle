# External libraries
import asyncio
import threading

import websockets


# Internal libraries
from common.config import (
    NETWORK_SERVER_URI,
    MSG_TYPE_ENTITIES,
    MSG_TYPE_WALLS,
    MSG_TYPE_BULLETS,
)


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
                async for message in ws:
                    if not self.running:
                        break

                    try:
                        await self._handle_message(message)
                    except (ValueError, RuntimeError):
                        continue
        except (
            OSError,
            websockets.exceptions.WebSocketException,
        ):
            pass

    async def _handle_message(self, data: bytes) -> None:
        """
        Parse and dispatch message to appropriate scene callback.

        Message format: [1 byte: type][remaining: payload]

        Args:
            data: Raw message bytes from server.
        """
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
