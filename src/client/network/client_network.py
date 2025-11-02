import asyncio
import websockets
import threading


class ClientNetwork:
    """
    Minimal WebSocket client that runs in background thread.
    Receives packets and calls scene callbacks.
    """
    
    def __init__(self, scene, uri: str = "ws://localhost:8765/ws"):
        self.scene = scene
        self.uri = uri
        self.running = False
    
    def start(self):
        """Start network thread (non-blocking)."""
        self.running = True
        thread = threading.Thread(target=self._run_loop, daemon=True)
        thread.start()
        print("Network client started")
    
    def stop(self):
        """Stop network thread."""
        self.running = False
    
    def _run_loop(self):
        """Run WebSocket connection in background thread."""
        asyncio.run(self._connect())
    
    async def _connect(self):
        """Connect to server and receive loop."""
        try:
            async with websockets.connect(self.uri) as ws:
                print(f"Connected to {self.uri}")
                
                async for message in ws:
                    if not self.running:
                        break
                    
                    try:
                        await self._handle_message(message)
                    except Exception as e:
                        print(f"Error handling message: {e}")
        
        except Exception as e:
            print(f"Connection error: {e}")
        finally:
            print("Disconnected from server")
    
    async def _handle_message(self, data: bytes):
        """Parse message type and route to scene."""
        if not data or len(data) < 1:
            return
        
        msg_type = data[0]
        payload = data[1:]
        
        if msg_type == 0x01:  # Init (walls)
            print(f"Received init: {len(payload)} bytes")
        
        elif msg_type == 0x02:  # Entities update
            self.scene.on_entities_update(payload)
        
        elif msg_type == 0x03:  # Walls update
            self.scene.on_walls_update(payload)
