"""
WebSocket Connection Manager
Handles multiple concurrent connections with heartbeat
"""
import asyncio
from typing import Dict, Set
from fastapi import WebSocket
from datetime import datetime
from config.settings import settings
from utils.logger import setup_logger

logger = setup_logger(__name__)

class ConnectionManager:
    """Manages WebSocket connections"""
    
    def __init__(self):
        # Active connections: {call_id: WebSocket}
        self.active_connections: Dict[str, WebSocket] = {}
        
        # Connection metadata
        self.connection_info: Dict[str, dict] = {}
        
        # Heartbeat tasks
        self.heartbeat_tasks: Dict[str, asyncio.Task] = {}
        
        logger.info("✓ Connection Manager initialized")
    
    async def connect(self, websocket: WebSocket, call_id: str):
        """Accept new WebSocket connection"""
        await websocket.accept()
        self.active_connections[call_id] = websocket
        self.connection_info[call_id] = {
            "connected_at": datetime.utcnow(),
            "messages_sent": 0,
            "messages_received": 0,
            "last_activity": datetime.utcnow()
        }
        
        # Start heartbeat
        self.heartbeat_tasks[call_id] = asyncio.create_task(
            self._heartbeat(call_id)
        )
        
        logger.info(f"✓ Connection established: {call_id} (Total: {len(self.active_connections)})")
    
    def disconnect(self, call_id: str):
        """Remove connection"""
        if call_id in self.active_connections:
            # Cancel heartbeat
            if call_id in self.heartbeat_tasks:
                self.heartbeat_tasks[call_id].cancel()
                del self.heartbeat_tasks[call_id]
            
            # Remove connection
            del self.active_connections[call_id]
            del self.connection_info[call_id]
            
            logger.info(f"✗ Connection closed: {call_id} (Total: {len(self.active_connections)})")
    
    async def send_message(self, call_id: str, message: dict):
        """Send message to specific connection"""
        if call_id in self.active_connections:
            try:
                websocket = self.active_connections[call_id]
                await websocket.send_json(message)
                
                # Update stats
                self.connection_info[call_id]["messages_sent"] += 1
                self.connection_info[call_id]["last_activity"] = datetime.utcnow()
                
            except Exception as e:
                logger.error(f"Send error [{call_id}]: {str(e)}")
                self.disconnect(call_id)
    
    async def broadcast(self, message: dict, exclude: Set[str] = None):
        """Broadcast message to all connections"""
        exclude = exclude or set()
        
        for call_id in list(self.active_connections.keys()):
            if call_id not in exclude:
                await self.send_message(call_id, message)
    
    async def _heartbeat(self, call_id: str):
        """Send periodic heartbeat to keep connection alive"""
        try:
            while call_id in self.active_connections:
                await asyncio.sleep(settings.WS_HEARTBEAT_INTERVAL)
                
                if call_id in self.active_connections:
                    await self.send_message(call_id, {
                        "type": "heartbeat",
                        "timestamp": datetime.utcnow().isoformat()
                    })
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Heartbeat error [{call_id}]: {str(e)}")
    
    def get_connection_count(self) -> int:
        """Get number of active connections"""
        return len(self.active_connections)
    
    def get_connection_info(self, call_id: str) -> dict:
        """Get connection metadata"""
        return self.connection_info.get(call_id, {})
    
    def is_connected(self, call_id: str) -> bool:
        """Check if connection exists"""
        return call_id in self.active_connections
    
    async def close_all(self):
        """Close all connections"""
        logger.info("Closing all connections...")
        
        for call_id in list(self.active_connections.keys()):
            try:
                websocket = self.active_connections[call_id]
                await websocket.close()
            except:
                pass
            finally:
                self.disconnect(call_id)
        
        logger.info("✓ All connections closed")

# Singleton instance
manager = ConnectionManager()