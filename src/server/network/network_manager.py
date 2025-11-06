"""
WebSocket server manager using Quart.
Handles client connections, game loop timing, and state broadcasting.
"""

from quart import Quart, websocket
import asyncio
import time
from common.states.state_entity import StateEntity
from common.states.state_bullet import StateBullet


# === NETWORK CONFIGURATION ===
WEBSOCKET_ROUTE = '/ws'
DEFAULT_HOST = '0.0.0.0'
DEFAULT_PORT = 8765

# Game timing
SIMULATION_TICK_RATE = 60  # Hz (internal simulation frequency)
BROADCAST_RATE = 20        # Hz (network update frequency)

REQUIRED_CLIENTS_TO_START = 2

MESSAGE_TYPE_ENTITIES = 0x02
MESSAGE_TYPE_WALL_CHANGES = 0x03
MESSAGE_TYPE_BULLETS = 0x04


class NetworkManager:
    """
    Quart-based WebSocket server for game state synchronization.
    
    Responsibilities:
    - Accept and manage client connections
    - Start game loop when minimum clients connect
    - Broadcast entity states at network rate
    - Clean up on client disconnect
    """
    
    def __init__(self, game_manager):
        """
        Initialize network manager with Quart app and game logic.
        
        Args:
            game_manager: GameManager instance handling simulation
        """
        self.app = Quart(__name__)
        self.game_manager = game_manager
        
        # Track connected clients
        self.clients = set()
        self.required_clients = REQUIRED_CLIENTS_TO_START
        
        # Background task for game loop
        self.game_task = None
        
        # Register WebSocket endpoint
        @self.app.websocket(WEBSOCKET_ROUTE)
        async def ws_handler():
            await self.handle_client()
    
    async def handle_client(self):
        """
        Handle individual client connection lifecycle.
        
        Flow:
        1. Add client to tracking set
        2. Start game loop if minimum clients reached
        3. Keep connection alive (autoplay, no input needed)
        4. Clean up on disconnect and stop game if needed
        """
        ws = websocket._get_current_object()
        self.clients.add(ws)
        print(f"[NETWORK] Client connected. Total: {len(self.clients)}")
        
        try:
            # Start game loop once we have enough clients
            if len(self.clients) == self.required_clients and not self.game_task:
                print(f"[NETWORK] {self.required_clients} clients ready. Starting game...")
                self.game_task = asyncio.create_task(self._game_loop())
            
            # Keep connection alive (no client input in autoplay mode)
            while True:
                await websocket.receive()
        
        except asyncio.CancelledError:
            pass
        finally:
            # Clean up on disconnect
            self.clients.discard(ws)
            print(f"[NETWORK] Client disconnected. Total: {len(self.clients)}")
            
            # Stop game if we drop below minimum clients
            if len(self.clients) < self.required_clients:
                if self.game_task:
                    self.game_task.cancel()
                    self.game_task = None
                self.game_manager.is_running = False
                print("[NETWORK] Game stopped (insufficient clients)")
    
    async def _game_loop(self):
        """
        Main server game loop with accurate timing.
        
        Separates simulation rate (60 Hz) from broadcast rate (20 Hz):
        - Simulation runs every frame for physics/AI accuracy
        - Network updates sent every 3rd frame to reduce bandwidth
        
        Uses perf_counter for accurate frame timing.
        """
        self.game_manager.is_running = True
        
        # Calculate timing parameters
        sim_dt = 1.0 / SIMULATION_TICK_RATE
        broadcast_interval = 1.0 / BROADCAST_RATE
        
        # Spawn initial agents for testing
        self.game_manager.spawn_test_agents()
        
        # Track next broadcast time
        next_tick = time.perf_counter()
        time_since_broadcast = 0.0
        
        try:
            while self.game_manager.is_running and len(self.clients) >= self.required_clients:
                current_time = time.perf_counter()
                
                # Execute simulation tick when time comes
                if current_time >= next_tick:
                    self.game_manager.update(sim_dt)
                    time_since_broadcast += sim_dt
                    
                    # Broadcast only at network rate
                    if time_since_broadcast >= broadcast_interval:
                        await self._broadcast()
                        time_since_broadcast = 0.0
                    
                    next_tick += sim_dt
                else:
                    # Sleep until next tick (prevents CPU spin-wait)
                    sleep_time = max(0, next_tick - current_time)
                    await asyncio.sleep(sleep_time)
        
        except asyncio.CancelledError:
            print("[NETWORK] Game loop cancelled")
            self.game_manager.is_running = False

    async def _send_to_all(self, msg: bytes):
        """Send message to all connected clients."""
        if self.clients:
            await asyncio.gather(
                *(client.send(msg) for client in self.clients),
                return_exceptions=True
            )


    async def _broadcast(self):
        """Pack and send each message type."""
        
        # Entities - pass list of states
        entity_states = [agent.state for agent in self.game_manager.agents.values()]
        entities_bytes = StateEntity.pack_entities(entity_states)
        if entities_bytes:
            await self._send_to_all(bytes([MESSAGE_TYPE_ENTITIES]) + entities_bytes)
        
        # Bullets - pass list of states
        bullet_states = [bullet.state for bullet in self.game_manager.bullets.values()]
        bullets_bytes = StateBullet.pack_bullets(bullet_states)
        if bullets_bytes:
            await self._send_to_all(bytes([MESSAGE_TYPE_BULLETS]) + bullets_bytes)

        # # Walls
        # wall_changes = self.game_manager.walls_state.pack_changes()
        # if wall_changes:
        #     await self._send_to_all(bytes([MESSAGE_TYPE_WALL_CHANGES]) + wall_changes)
        #     self.game_manager.walls_state.clear_buffer()

    
    def run(self, host=DEFAULT_HOST, port=DEFAULT_PORT):
        """
        Start Quart WebSocket server.
        
        Args:
            host: Bind address (default: 0.0.0.0 - all interfaces)
            port: Listen port (default: 8765)
        """
        print(f"[NETWORK] Starting server on ws://{host}:{port}{WEBSOCKET_ROUTE}")
        self.app.run(host=host, port=port)
