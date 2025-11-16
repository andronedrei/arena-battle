"""
Unified Network Manager - handles both Survival and KOTH modes dynamically.

Waits for first client to select game mode, then initializes that mode.
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
        MSG_TYPE_GAME_END,
    MSG_TYPE_SELECT_MODE,
    MSG_TYPE_MODE_SELECTED,
    GAME_MODE_SURVIVAL,
    GAME_MODE_KOTH,
    NETWORK_HOST,
    NETWORK_PORT,
    SIMULATION_TICK_RATE,
    WEBSOCKET_ROUTE,
)
from common.states.state_bullet import StateBullet
from common.states.state_entity import StateEntity
from server.config import REQUIRED_CLIENTS_TO_START
from server.gameplay.game_manager import GameManager
from server.gameplay.game_manager_koth import GameManagerKOTH
from common.logger import get_logger

# KOTH-specific imports
import sys
import os
# Add path for KOTH files
koth_path = os.path.join(os.path.dirname(__file__), '..', '..', 'common')
if koth_path not in sys.path:
    sys.path.insert(0, koth_path)

try:
    from koth_config import MSG_TYPE_KOTH_STATE
except ImportError:
    MSG_TYPE_KOTH_STATE = 0x10  # Fallback

logger = get_logger(__name__)


class NetworkManagerUnified:
    """
    Unified WebSocket server supporting multiple game modes.
    
    Workflow:
    1. Clients connect and wait in lobby
    2. First client selects game mode from menu
    3. Server creates appropriate GameManager
    4. All clients are notified and game starts
    """
    
    def __init__(self, wall_config_file: str) -> None:
        """
        Initialize unified network manager.
        
        Args:
            wall_config_file: Path to walls configuration file.
        """
        self.app = Quart(__name__)
        self.wall_config_file = wall_config_file
        self.game_manager = None
        self.game_mode = None
        
        # MODIFICAT: Track individual client states
        self.clients: dict = {}  # ws -> {'ready': bool, 'mode': int|None}
        
        self.required_clients = REQUIRED_CLIENTS_TO_START
        self.game_task: asyncio.Task | None = None
        
        # ȘTERS: self.mode_locked - nu mai avem nevoie
        
        # Register WebSocket endpoint
        @self.app.websocket(WEBSOCKET_ROUTE)
        async def ws_handler() -> None:
            await self.handle_client()
    
    # Connection management
    
    async def handle_client(self) -> None:
        """Handle individual client connection lifecycle."""
        ws = websocket._get_current_object()

        self.clients[ws] = {'ready': False, 'mode': None}
        
        try:
            client_id = getattr(ws, 'id', None) or id(ws)
        except Exception:
            client_id = id(ws)
        
        logger.info("Client connected: %s (total=%d)", client_id, len(self.clients))
        
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
                    
                    # Handle mode selection
                    if msg_type == MSG_TYPE_SELECT_MODE and len(data) >= 2:
                        selected_mode = data[1] if isinstance(data, bytes) else ord(data[1])
                        await self._handle_mode_selection(selected_mode, client_id, ws)
                    
                    # Handle ready message
                    elif msg_type == MSG_TYPE_CLIENT_READY:
                        self.clients[ws]['ready'] = True
                        
                        ready_count = sum(1 for c in self.clients.values() if c['ready'])
                        connected_count = len(self.clients)
                        logger.info(
                            "Client %s READY (%d/%d) required=%d",
                            client_id,
                            ready_count,
                            connected_count,
                            self.required_clients,
                        )
                        
                        can_start = await self._check_can_start()
                        
                        if can_start and not self.game_task and self.game_manager is not None:
                            logger.info("Starting game: mode=%s ready=%d connected=%d", 
                                    "KOTH" if self.game_mode == GAME_MODE_KOTH else "Survival",
                                    ready_count, connected_count)
                            await self._send_to_all(bytes([MSG_TYPE_START_GAME]))
                            self.game_task = asyncio.create_task(self._game_loop())
        
        except asyncio.CancelledError:
            pass
        finally:
            if ws in self.clients:
                del self.clients[ws]
            
            # Stop game if not enough clients
            if len(self.clients) < self.required_clients:
                if self.game_task:
                    self.game_task.cancel()
                    self.game_task = None
                if self.game_manager:
                    self.game_manager.is_running = False
    
    async def _handle_mode_selection(self, mode: int, client_id, ws) -> None:
        """
        Handle game mode selection from client.
        
        Args:
            mode: Selected game mode (GAME_MODE_SURVIVAL or GAME_MODE_KOTH).
            client_id: ID of client that selected the mode.
            ws: WebSocket of the client.
        """
        mode_name = "KOTH" if mode == GAME_MODE_KOTH else "Survival"
        logger.info("Client %s selected mode: %s", client_id, mode_name)
        
        # Store this client's mode selection
        self.clients[ws]['mode'] = mode
        
        # Check if all clients have selected a mode
        modes_selected = [c['mode'] for c in self.clients.values() if c['mode'] is not None]
        
        if len(modes_selected) == 0:
            return
        
        # Check if all selected modes are the same
        if len(set(modes_selected)) == 1:
            # All clients agree on the mode!
            agreed_mode = modes_selected[0]
            
            # Create game manager if not exists or mode changed
            if self.game_mode != agreed_mode:
                self.game_mode = agreed_mode
                
                if agreed_mode == GAME_MODE_KOTH:
                    self.game_manager = GameManagerKOTH(self.wall_config_file)
                    logger.info("Created GameManagerKOTH - all clients agreed on KOTH")
                else:
                    self.game_manager = GameManager(self.wall_config_file)
                    logger.info("Created GameManager - all clients agreed on Survival")
                
                # Notify all clients of the agreed mode
                await self._send_to_all(bytes([MSG_TYPE_MODE_SELECTED, agreed_mode]))
                logger.info("All clients agree on mode: %s", mode_name)
        else:
            # Clients have different modes selected - wait for consensus
            logger.info("Clients have different mode selections - waiting for consensus")
            logger.debug("Current modes: %s", modes_selected)
    
    
    async def _check_can_start(self) -> bool:
        """
        Check if game can start.
        
        Requirements:
        - All clients must have selected a mode
        - All clients must have selected the SAME mode
        - All clients must be ready
        - Minimum required_clients must be met
        
        Returns:
            True if game can start, False otherwise.
        """
        if len(self.clients) < self.required_clients:
            return False
        
        # Check all clients are ready
        if not all(c['ready'] for c in self.clients.values()):
            return False
        
        # Check all clients have selected a mode
        modes = [c['mode'] for c in self.clients.values()]
        if None in modes:
            logger.info("Cannot start - not all clients have selected a mode")
            return False
        
        # Check all modes are the same
        if len(set(modes)) != 1:
            logger.info("Cannot start - clients selected different modes: %s", modes)
            return False
        
        return True
    
    
    # Game loop
    
    async def _game_loop(self) -> None:
        """Main game loop with separated simulation and broadcast rates."""
        if self.game_manager is None:
            logger.error("Cannot start game loop - game_manager is None")
            return
        
        self.game_manager.is_running = True
        
        sim_dt = 1.0 / SIMULATION_TICK_RATE
        broadcast_interval = 1.0 / NETWORK_UPDATE_RATE
        
        # CRITICA: Spawn agents pentru modul curent
        self.game_manager.spawn_test_agents()
        logger.info("Spawned agents for %s mode", "KOTH" if self.game_mode == GAME_MODE_KOTH else "Survival")
        
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
            logger.info("Game loop cancelled")
        finally:
            # Notify clients that the game ended so they can see winner
            try:
                winner = 0
                if self.game_manager and getattr(self.game_manager, "winner_team", None) is not None:
                    try:
                        winner = int(self.game_manager.winner_team)
                    except Exception:
                        winner = 0

                logger.info("Game ended - broadcasting GAME_END (winner=%s) to clients", winner)
                # Send winner as second byte
                await self._send_to_all(bytes([MSG_TYPE_GAME_END, winner]))
            except Exception:
                logger.exception("Failed to broadcast GAME_END")

            # Wait a short delay so clients can show the message, then disconnect them
            try:
                disconnect_delay = 5.0
                logger.info("Waiting %.1fs before disconnecting clients", disconnect_delay)
                await asyncio.sleep(disconnect_delay)

                # Close all client websockets
                clients_snapshot = list(self.clients.keys())
                for c in clients_snapshot:
                    try:
                        await c.close()
                    except Exception:
                        logger.exception("Error closing client websocket")

                # Clear client list
                self.clients.clear()
                logger.info("All clients disconnected after game end")
            except Exception:
                logger.exception("Error during post-game client disconnect sequence")
            
            
    # Broadcasting
    
    async def _send_to_all(self, msg: bytes) -> None:
        """Send message to all connected clients."""
        if self.clients:
            await asyncio.gather(
                *(client.send(msg) for client in self.clients),
                return_exceptions=True,
            )
    
    async def _broadcast(self) -> None:
        """Pack and broadcast game state based on current mode."""
        if self.game_manager is None:
            return
        
        # Entities (both modes)
        entity_states = [agent.state for agent in self.game_manager.agents.values()]
        entities_bytes = StateEntity.pack_entities(entity_states)
        if entities_bytes:
            await self._send_to_all(bytes([MSG_TYPE_ENTITIES]) + entities_bytes)
        
        # Bullets (both modes)
        bullet_states = [bullet.state for bullet in self.game_manager.bullets.values()]
        bullets_bytes = StateBullet.pack_bullets(bullet_states)
        if bullets_bytes:
            await self._send_to_all(bytes([MSG_TYPE_BULLETS]) + bullets_bytes)
        
        # KOTH state (only for KOTH mode)
        if self.game_mode == GAME_MODE_KOTH and hasattr(self.game_manager, 'koth_state'):
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
        logger.info("Starting unified server on %s:%d", host, port)
        logger.info("Waiting for clients to select game mode...")
        self.app.run(host=host, port=port)