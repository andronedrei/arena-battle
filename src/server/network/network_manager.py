# External libraries
import asyncio
import time

from quart import Quart, websocket


# Internal libraries
from common.config import (
    NETWORK_UPDATE_RATE,
    MSG_TYPE_BULLETS,
    MSG_TYPE_ENTITIES,
    NETWORK_HOST,
    NETWORK_PORT,
    SIMULATION_TICK_RATE,
    WEBSOCKET_ROUTE,
)
from common.states.state_bullet import StateBullet
from common.states.state_entity import StateEntity
from server.config import REQUIRED_CLIENTS_TO_START


class NetworkManager:
    """
    WebSocket server for game state synchronization using Quart.

    Manages client connections, runs game loop at configured rates,
    and broadcasts entity states to all connected clients.
    """

    def __init__(self, game_manager) -> None:
        """
        Initialize network manager.

        Args:
            game_manager: GameManager instance handling simulation.
        """
        self.app = Quart(__name__)
        self.game_manager = game_manager

        self.clients: set = set()
        self.required_clients = REQUIRED_CLIENTS_TO_START
        self.game_task: asyncio.Task | None = None

        # Register WebSocket endpoint
        @self.app.websocket(WEBSOCKET_ROUTE)
        async def ws_handler() -> None:
            await self.handle_client()

    # Connection management

    async def handle_client(self) -> None:
        """
        Handle individual client connection lifecycle.

        Adds client to tracking, starts game loop if minimum clients
        reached, maintains connection, and cleans up on disconnect.
        """
        ws = websocket._get_current_object()
        self.clients.add(ws)

        try:
            # Start game loop once minimum clients connect
            if (
                len(self.clients) == self.required_clients
                and not self.game_task
            ):
                self.game_task = asyncio.create_task(self._game_loop())

            # Keep connection alive
            while True:
                await websocket.receive()

        except asyncio.CancelledError:
            pass
        finally:
            self.clients.discard(ws)

            # Stop game if clients drop below minimum
            if len(self.clients) < self.required_clients:
                if self.game_task:
                    self.game_task.cancel()
                    self.game_task = None
                self.game_manager.is_running = False

    # Game loop

    async def _game_loop(self) -> None:
        """
        Main server game loop with separated simulation and broadcast rates.

        Simulation runs at SIMULATION_TICK_RATE Hz for physics accuracy.
        Network updates broadcast at BROADCAST_RATE Hz to reduce bandwidth.
        Uses perf_counter for accurate frame timing.
        """
        self.game_manager.is_running = True

        sim_dt = 1.0 / SIMULATION_TICK_RATE
        broadcast_interval = 1.0 / NETWORK_UPDATE_RATE

        self.game_manager.spawn_test_agents()

        next_tick = time.perf_counter()
        time_since_broadcast = 0.0

        try:
            while (
                self.game_manager.is_running
                and len(self.clients) >= self.required_clients
            ):
                current_time = time.perf_counter()

                # Execute simulation tick when time arrives
                if current_time >= next_tick:
                    self.game_manager.update(sim_dt)
                    time_since_broadcast += sim_dt

                    # Broadcast at network rate
                    if time_since_broadcast >= broadcast_interval:
                        await self._broadcast()
                        time_since_broadcast = 0.0

                    next_tick += sim_dt
                else:
                    # Sleep until next tick
                    sleep_time = max(0, next_tick - current_time)
                    await asyncio.sleep(sleep_time)

        except asyncio.CancelledError:
            self.game_manager.is_running = False

    # Broadcasting

    async def _send_to_all(self, msg: bytes) -> None:
        """
        Send message to all connected clients.

        Args:
            msg: Message bytes to broadcast.
        """
        if self.clients:
            await asyncio.gather(
                *(client.send(msg) for client in self.clients),
                return_exceptions=True,
            )

    async def _broadcast(self) -> None:
        """Pack and broadcast entity and bullet states."""
        # Entities
        entity_states = [
            agent.state for agent in self.game_manager.agents.values()
        ]
        entities_bytes = StateEntity.pack_entities(entity_states)
        if entities_bytes:
            await self._send_to_all(
                bytes([MSG_TYPE_ENTITIES]) + entities_bytes
            )

        # Bullets
        bullet_states = [
            bullet.state for bullet in self.game_manager.bullets.values()
        ]
        bullets_bytes = StateBullet.pack_bullets(bullet_states)
        if bullets_bytes:
            await self._send_to_all(
                bytes([MSG_TYPE_BULLETS]) + bullets_bytes
            )

        # # Walls (disabled - for future use)
        # wall_changes = self.game_manager.walls_state.pack_changes()
        # if wall_changes:
        #     await self._send_to_all(
        #         bytes([MESSAGE_TYPE_WALL_CHANGES]) + wall_changes
        #     )
        #     self.game_manager.walls_state.clear_buffer()

    # Server management

    def run(
        self, host: str = NETWORK_HOST, port: int = NETWORK_PORT
    ) -> None:
        """
        Start WebSocket server.

        Args:
            host: Bind address (0.0.0.0 for all interfaces).
            port: Listen port number.
        """
        self.app.run(host=host, port=port)
