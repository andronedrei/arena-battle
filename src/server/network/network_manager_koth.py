"""
KOTH Network Manager - extends base network with KOTH state broadcasting.

Handles client connections and broadcasts KOTH game state alongside entities.
"""

import asyncio
import time

from quart import Quart, websocket

from common.config import (
    NETWORK_UPDATE_RATE,
    MSG_TYPE_BULLETS,
    MSG_TYPE_ENTITIES,
    MSG_TYPE_CLIENT_READY,
    MSG_TYPE_START_GAME,
    NETWORK_HOST,
    NETWORK_PORT,
    SIMULATION_TICK_RATE,
    WEBSOCKET_ROUTE,
)
from common.states.state_bullet import StateBullet
from common.states.state_entity import StateEntity
from server.config import REQUIRED_CLIENTS_TO_START
from common.logger import get_logger

from koth_config import MSG_TYPE_KOTH_STATE

logger = get_logger(__name__)


class NetworkManagerKOTH:
    """
    WebSocket server for KOTH game state synchronization.
    
    Extends base network manager with KOTH-specific state broadcasting.
    """
    
    def __init__(self, game_manager) -> None:
        """
        Initialize KOTH network manager.
        
        Args:
            game_manager: GameManagerKOTH instance.
        """
        self.app = Quart(__name__)
        self.game_manager = game_manager
        self.clients: dict = {}
        self.required_clients = REQUIRED_CLIENTS_TO_START
        self.game_task: asyncio.Task | None = None
        
        # Register WebSocket endpoint
        @self.app.websocket(WEBSOCKET_ROUTE)
        async def ws_handler() -> None:
            await self.handle_client()
    
    # Connection management
    
    async def handle_client(self) -> None:
        """Handle individual client connection lifecycle."""
        ws = websocket._get_current_object()
        self.clients[ws] = False
        
        try:
            client_id = getattr(ws, 'id', None) or id(ws)
        except Exception:
            client_id = id(ws)
        
        logger.info("Client connected: %s (connected=%d)", client_id, len(self.clients))
        
        try:
            while True:
                data = await websocket.receive()
                if not data:
                    continue
                
                if (isinstance(data, bytes) or isinstance(data, str)) and len(data) >= 1:
                    if isinstance(data, str):
                        raw = data
                        try:
                            msg_type = ord(raw[0])
                        except Exception:
                            raw_b = raw.encode('latin-1', errors='ignore')
                            msg_type = raw_b[0] if raw_b else None
                    else:
                        raw = data
                        msg_type = data[0]
                    
                    logger.debug("Received msg from %s: type=%s", client_id, msg_type)
                    
                    if msg_type == MSG_TYPE_CLIENT_READY:
                        self.clients[ws] = True
                        
                        ready_count = sum(1 for v in self.clients.values() if v)
                        connected_count = len(self.clients)
                        logger.info(
                            "Client %s READY (%d/%d) required=%d",
                            client_id,
                            ready_count,
                            connected_count,
                            self.required_clients,
                        )
                        
                        can_start = (
                            ready_count >= self.required_clients
                            or (connected_count > 0 and ready_count == connected_count)
                        )
                        
                        if can_start and not self.game_task:
                            logger.info("Starting KOTH game: ready=%d connected=%d", ready_count, connected_count)
                            await self._send_to_all(bytes([MSG_TYPE_START_GAME]))
                            self.game_task = asyncio.create_task(self._game_loop())
        
        except asyncio.CancelledError:
            pass
        finally:
            if ws in self.clients:
                del self.clients[ws]
            
            if len(self.clients) < self.required_clients:
                if self.game_task:
                    self.game_task.cancel()
                    self.game_task = None
                self.game_manager.is_running = False
    
    # Game loop
    
    async def _game_loop(self) -> None:
        """Main KOTH game loop with separated simulation and broadcast rates."""
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
                
                if current_time >= next_tick:
                    self.game_manager.update(sim_dt)
                    time_since_broadcast += sim_dt
                    
                    if time_since_broadcast >= broadcast_interval:
                        await self._broadcast()
                        time_since_broadcast = 0.0
                    
                    next_tick += sim_dt
                else:
                    sleep_time = max(0, next_tick - current_time)
                    await asyncio.sleep(sleep_time)
        
        except asyncio.CancelledError:
            self.game_manager.is_running = False
    
    # Broadcasting
    
    async def _send_to_all(self, msg: bytes) -> None:
        """Send message to all connected clients."""
        if self.clients:
            try:
                if len(msg) >= 1 and msg[0] == MSG_TYPE_START_GAME:
                    logger.info("Broadcasting START_GAME to %d client(s)", len(self.clients))
            except Exception:
                pass
            
            await asyncio.gather(
                *(client.send(msg) for client in self.clients),
                return_exceptions=True,
            )
    
    async def _broadcast(self) -> None:
        """Pack and broadcast game state."""
        # Entities
        entity_states = [agent.state for agent in self.game_manager.agents.values()]
        entities_bytes = StateEntity.pack_entities(entity_states)
        if entities_bytes:
            await self._send_to_all(bytes([MSG_TYPE_ENTITIES]) + entities_bytes)
        
        # Bullets
        bullet_states = [bullet.state for bullet in self.game_manager.bullets.values()]
        bullets_bytes = StateBullet.pack_bullets(bullet_states)
        if bullets_bytes:
            await self._send_to_all(bytes([MSG_TYPE_BULLETS]) + bullets_bytes)
        
        # KOTH state
        koth_bytes = self.game_manager.koth_state.pack()
        if koth_bytes:
            await self._send_to_all(bytes([MSG_TYPE_KOTH_STATE]) + koth_bytes)
    
    # Server management
    
    def run(self, host: str = NETWORK_HOST, port: int = NETWORK_PORT) -> None:
        """
        Start WebSocket server.
        
        Args:
            host: Bind address.
            port: Listen port.
        """
        self.app.run(host=host, port=port)