"""
CTF Network Manager - extends base network with CTF state broadcasting.

Handles client connections and broadcasts CTF game state alongside entities.
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
    MSG_TYPE_CTF_STATE,
    NETWORK_HOST,
    NETWORK_PORT,
    SIMULATION_TICK_RATE,
    WEBSOCKET_ROUTE,
)
from common.states.state_bullet import StateBullet
from common.states.state_entity import StateEntity
from common.states.state_ctf import StateCTF, StateCTFFlag
from server.config import REQUIRED_CLIENTS_TO_START
from common.logger import get_logger

logger = get_logger(__name__)


class NetworkManagerCTF:
    """
    WebSocket server for CTF game state synchronization.
    
    Extends base network manager with CTF-specific state broadcasting.
    """
    
    def __init__(self, game_manager) -> None:
        """
        Initialize CTF network manager.
        
        Args:
            game_manager: GameManagerCTF instance.
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
                            logger.info("Starting CTF game: ready=%d connected=%d", ready_count, connected_count)
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
        """Main CTF game loop with separated simulation and broadcast rates."""
        self.game_manager.is_running = True
        
        sim_dt = 1.0 / SIMULATION_TICK_RATE
        broadcast_interval = 1.0 / NETWORK_UPDATE_RATE
        
        # Spawn agents (configured in server/config.py)
        from server.config import TEAM_A_SPAWNS_CTF, TEAM_B_SPAWNS_CTF
        self.game_manager.spawn_test_agents(TEAM_A_SPAWNS_CTF, TEAM_B_SPAWNS_CTF)
        
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
        
        # CTF state
        flag_a = self.game_manager.flag_team_a
        flag_b = self.game_manager.flag_team_b
        
        ctf_state = StateCTF(
            team_a_captures=self.game_manager.team_a_captures,
            team_b_captures=self.game_manager.team_b_captures,
            flag_team_a=StateCTFFlag(
                x=flag_a.x,
                y=flag_a.y,
                carrier_id=flag_a.carrier_id,
                at_base=(flag_a.state == 0),  # FlagState.AT_BASE
            ),
            flag_team_b=StateCTFFlag(
                x=flag_b.x,
                y=flag_b.y,
                carrier_id=flag_b.carrier_id,
                at_base=(flag_b.state == 0),  # FlagState.AT_BASE
            ),
            time_elapsed=self.game_manager.time_elapsed,
            max_time=self.game_manager.game_manager.__dict__.get('CTF_MAX_DURATION', 300.0) if hasattr(self.game_manager, 'game_manager') else 300.0,
            max_captures=self.game_manager.game_manager.__dict__.get('CTF_MAX_CAPTURES', 3) if hasattr(self.game_manager, 'game_manager') else 3,
            game_over=self.game_manager.game_over,
            winner_team=self.game_manager.winner_team,
        )
        
        # Import config values directly
        from common.ctf_config import CTF_MAX_DURATION, CTF_MAX_CAPTURES
        ctf_state.max_time = CTF_MAX_DURATION
        ctf_state.max_captures = CTF_MAX_CAPTURES
        
        ctf_bytes = ctf_state.pack()
        if ctf_bytes:
            await self._send_to_all(bytes([MSG_TYPE_CTF_STATE]) + ctf_bytes)
    
    # Server management
    
    def run(self, host: str = NETWORK_HOST, port: int = NETWORK_PORT) -> None:
        """
        Start WebSocket server.
        
        Args:
            host: Bind address.
            port: Listen port.
        """
        logger.info(f"Starting CTF server on {host}:{port}")
        self.app.run(host=host, port=port)
