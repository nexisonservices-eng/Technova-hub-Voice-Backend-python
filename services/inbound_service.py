"""
Inbound Call Service
Integrates with Node.js backend for enhanced inbound call management
"""
import asyncio
import aiohttp
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from utils.logger import setup_logger

logger = setup_logger(__name__)

class InboundService:
    """Service for managing inbound calls and integration with Node.js backend"""
    
    def __init__(self):
        # self.node_backend_url = "https://technova-hub-voice-backend-node-hxg7.onrender.com"
        self.node_backend_url = "http://localhost:5000"
        self.session = None
        
    async def initialize(self):
        """Initialize HTTP session and connections"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={"Content-Type": "application/json"}
        )
        logger.info("âœ“ Inbound Service initialized")
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.session:
            await self.session.close()
    

    
    async def get_queue_status(self) -> Dict[str, Any]:
        """
        Get current queue status from Node.js backend
        
        Returns:
            Queue information and statistics
        """
        try:
            if not self.session:
                await self.initialize()
            
            async with self.session.get(
                f"{self.node_backend_url}/inbound/queues"
            ) as response:
                if 200 <= response.status < 400:
                    queue_data = await response.json()
                    return queue_data
                else:
                    logger.error(f"Failed to get queue status: {response.status}")
                    return self._get_mock_queue_data()
                    
        except Exception as e:
            logger.error(f"Get queue status error: {str(e)}")
            return self._get_mock_queue_data()
    
    def _get_mock_queue_data(self) -> Dict[str, Any]:
        """Mock queue data for fallback"""
        return {
            "sales": {"length": 2, "avg_wait": 45},
            "tech": {"length": 1, "avg_wait": 30},
            "billing": {"length": 0, "avg_wait": 0},
            "priority": {"length": 1, "avg_wait": 15}
        }
    
    async def get_analytics(self, period: str = "today") -> Dict[str, Any]:
        """
        Get call analytics from Node.js backend
        
        Args:
            period: Time period for analytics
            
        Returns:
            Analytics data
        """
        try:
            if not self.session:
                await self.initialize()
            
            async with self.session.get(
                f"{self.node_backend_url}/inbound/analytics?period={period}"
            ) as response:
                if 200 <= response.status < 400:
                    analytics = await response.json()
                    return analytics
                else:
                    logger.error(f"Failed to get analytics: {response.status}")
                    return self._get_mock_analytics()
                    
        except Exception as e:
            logger.error(f"Get analytics error: {str(e)}")
            return self._get_mock_analytics()
    
    def _get_mock_analytics(self) -> Dict[str, Any]:
        """Mock analytics data for fallback"""
        return {
            "summary": {
                "totalCalls": 25,
                "inboundCalls": 15,
                "outboundCalls": 10,
                "completedCalls": 20,
                "successRate": 80,
                "avgDuration": 120
            },
            "ivrAnalytics": {
                "totalIVRCalls": 12,
                "ivrUsageRate": 80,
                "routingBreakdown": {"sales": 5, "tech": 4, "billing": 2, "ai": 1}
            },
            "aiMetrics": {
                "aiCalls": 8,
                "aiEngagementRate": 53,
                "avgResponseTime": 800
            }
        }
    
    async def update_ivr_config(self, menu_name: str, config: Dict[str, Any]):
        """
        Update IVR configuration in Node.js backend
        
        Args:
            menu_name: IVR menu name
            config: IVR configuration
        """
        try:
            if not self.session:
                await self.initialize()
            
            async with self.session.post(
                f"{self.node_backend_url}/inbound/ivr/configs",
                json={"menuName": menu_name, "config": config}
            ) as response:
                if 200 <= response.status < 400:
                    logger.info(f"IVR config updated: {menu_name}")
                    return await response.json()
                else:
                    logger.error(f"Failed to update IVR config: {response.status}")
                    return {"success": False}
                    
        except Exception as e:
            logger.error(f"Update IVR config error: {str(e)}")
            return {"success": False}
    
    async def test_ivr_menu(self, menu_name: str):
        """
        Test IVR menu configuration
        
        Args:
            menu_name: IVR menu name to test
        """
        try:
            if not self.session:
                await self.initialize()
            
            async with self.session.post(
                f"{self.node_backend_url}/inbound/ivr/test/{menu_name}"
            ) as response:
                if 200 <= response.status < 400:
                    logger.info(f"IVR test initiated: {menu_name}")
                    return await response.json()
                else:
                    logger.error(f"Failed to test IVR: {response.status}")
                    return {"success": False}
                    
        except Exception as e:
            logger.error(f"Test IVR error: {str(e)}")
            return {"success": False}
    
    async def health_check(self) -> Dict[str, bool]:
        """
        Check health of Node.js backend integration
        
        Returns:
            Health status of different components
        """
        health_status = {
            "nodejs_backend": False,
            "api_connection": False
        }
        
        try:
            if not self.session:
                await self.initialize()
            
            # Test Node.js backend health
            async with self.session.get(
                f"{self.node_backend_url}/health/ping",
                timeout=5
            ) as response:
                if 200 <= response.status < 400:
                    health_status["nodejs_backend"] = True
                    health_status["api_connection"] = True
                    logger.info("âœ“ Node.js backend health check passed")
                else:
                    logger.warning(f"Node.js backend returned status: {response.status}")
                    health_status["api_connection"] = True
            
        except asyncio.TimeoutError:
            logger.error("Health check timeout - Node.js backend not responding")
        except Exception as e:
            error_msg = str(e).lower()
            if "connection refused" in error_msg:
                logger.error("Node.js backend is not running - Connection refused")
            elif "timeout" in error_msg:
                logger.error("Health check timeout - Node.js backend not responding")
            else:
                logger.error(f"Health check error: {str(e)}")
        
        return health_status

# Global instance
inbound_service = InboundService()

# Export functions for easy access
async def get_queue_status() -> Dict[str, Any]:
    """Get current queue status"""
    return await inbound_service.get_queue_status()

async def get_analytics(period: str = "today") -> Dict[str, Any]:
    """Get call analytics"""
    return await inbound_service.get_analytics(period)

async def health_check() -> Dict[str, bool]:
    """Check service health"""
    return await inbound_service.health_check()

