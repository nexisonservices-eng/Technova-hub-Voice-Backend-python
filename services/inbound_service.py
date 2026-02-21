"""
Inbound Call Service
Integrates with Node.js backend for enhanced inbound call management
"""
import asyncio
import aiohttp
from typing import Dict, Any, Optional
from utils.logger import setup_logger
from config.settings import settings

logger = setup_logger(__name__)


class InboundService:
    """Service for managing inbound calls and integration with Node.js backend"""

    def __init__(self):
        self.node_backend_url = settings.NODE_BACKEND_URL.rstrip('/')
        self.session = None
        self.timeout = aiohttp.ClientTimeout(total=settings.NODE_BACKEND_TIMEOUT)

    def _build_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if settings.NODE_BACKEND_INTERNAL_API_KEY:
            headers["x-internal-api-key"] = settings.NODE_BACKEND_INTERNAL_API_KEY
        return headers

    async def initialize(self):
        """Initialize HTTP session and connections"""
        self.session = aiohttp.ClientSession(
            timeout=self.timeout,
            headers=self._build_headers()
        )
        logger.info("? Inbound Service initialized")

    async def cleanup(self):
        """Cleanup resources"""
        if self.session:
            await self.session.close()

    async def _ensure_session(self):
        if not self.session:
            await self.initialize()

    async def _get_json_with_fallback(self, paths, method="get", json_payload=None):
        await self._ensure_session()
        last_error = None

        for path in paths:
            url = f"{self.node_backend_url}{path}"
            try:
                request_method = getattr(self.session, method.lower())
                async with request_method(url, json=json_payload) as response:
                    if 200 <= response.status < 400:
                        return await response.json()
                    last_error = f"{url} -> {response.status}"
            except Exception as exc:
                last_error = f"{url} -> {exc}"

        logger.error(f"All fallback endpoints failed: {last_error}")
        return None

    async def get_queue_status(self) -> Dict[str, Any]:
        try:
            data = await self._get_json_with_fallback([
                "/inbound/queues",
                "/api/inbound/queues",
            ])
            return data if data else self._get_mock_queue_data()
        except Exception as e:
            logger.error(f"Get queue status error: {str(e)}")
            return self._get_mock_queue_data()

    def _get_mock_queue_data(self) -> Dict[str, Any]:
        return {
            "sales": {"length": 2, "avg_wait": 45},
            "tech": {"length": 1, "avg_wait": 30},
            "billing": {"length": 0, "avg_wait": 0},
            "priority": {"length": 1, "avg_wait": 15}
        }

    async def get_analytics(self, period: str = "today") -> Dict[str, Any]:
        try:
            data = await self._get_json_with_fallback([
                f"/api/analytics/inbound?period={period}",
                f"/inbound/analytics?period={period}",
            ])
            return data if data else self._get_mock_analytics()
        except Exception as e:
            logger.error(f"Get analytics error: {str(e)}")
            return self._get_mock_analytics()

    def _get_mock_analytics(self) -> Dict[str, Any]:
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
        try:
            data = await self._get_json_with_fallback(
                ["/inbound/ivr/configs", "/api/inbound/ivr/configs"],
                method="post",
                json_payload={"menuName": menu_name, "config": config}
            )
            return data if data else {"success": False}
        except Exception as e:
            logger.error(f"Update IVR config error: {str(e)}")
            return {"success": False}

    async def test_ivr_menu(self, menu_name: str):
        try:
            data = await self._get_json_with_fallback(
                [f"/ivr/menus/{menu_name}/test", f"/api/ivr/menus/{menu_name}/test"],
                method="post"
            )
            return data if data else {"success": False}
        except Exception as e:
            logger.error(f"Test IVR error: {str(e)}")
            return {"success": False}

    async def health_check(self) -> Dict[str, Any]:
        health_status = {
            "nodejs_backend": False,
            "api_connection": False,
            "response_time_ms": 0,
            "retries": 0
        }

        start_time = asyncio.get_event_loop().time()

        try:
            await self._ensure_session()

            candidate_paths = ["/health/ping", "/health", "/"]
            timeout = aiohttp.ClientTimeout(total=settings.HEALTH_CHECK_TIMEOUT)

            for attempt in range(settings.HEALTH_CHECK_MAX_RETRIES):
                for path in candidate_paths:
                    url = f"{self.node_backend_url}{path}"
                    try:
                        async with self.session.get(url, timeout=timeout) as response:
                            elapsed = (asyncio.get_event_loop().time() - start_time) * 1000
                            health_status["response_time_ms"] = round(elapsed, 2)
                            health_status["api_connection"] = True

                            if 200 <= response.status < 400:
                                health_status["nodejs_backend"] = True
                                health_status["retries"] = attempt
                                return health_status
                    except Exception:
                        continue

                if attempt < settings.HEALTH_CHECK_MAX_RETRIES - 1:
                    wait_time = settings.HEALTH_CHECK_RETRY_DELAY * (settings.HEALTH_CHECK_RETRY_BACKOFF ** attempt)
                    health_status["retries"] = attempt + 1
                    await asyncio.sleep(wait_time)

        except Exception as e:
            logger.error(f"? Health check error: {str(e)}")

        elapsed = (asyncio.get_event_loop().time() - start_time) * 1000
        health_status["response_time_ms"] = round(elapsed, 2)
        return health_status


inbound_service = InboundService()


async def get_queue_status() -> Dict[str, Any]:
    return await inbound_service.get_queue_status()


async def get_analytics(period: str = "today") -> Dict[str, Any]:
    return await inbound_service.get_analytics(period)


async def health_check() -> Dict[str, bool]:
    return await inbound_service.health_check()
