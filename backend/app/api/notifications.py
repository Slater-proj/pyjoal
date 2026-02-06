"""
Notification API Endpoints
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Dict, Optional
from app.services.notification_service import notification_service
from app.core.auth import verify_token
import logging

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(verify_token)])


class NotificationConfigUpdate(BaseModel):
    """Notification config update schema"""
    enabled: Optional[bool] = None
    gotify: Optional[Dict] = None
    webhook: Optional[Dict] = None
    events: Optional[Dict] = None
    rate_limit: Optional[Dict] = None


@router.get("/notifications/config")
async def get_notification_config():
    """Get current notification configuration"""
    return notification_service.config


@router.put("/notifications/config")
async def update_notification_config(config: NotificationConfigUpdate):
    """Update notification configuration"""
    update = {k: v for k, v in config.model_dump().items() if v is not None}
    notification_service.update_config(update)
    logger.info(f"📨 Notification config updated via API")
    return {"status": "ok", "config": notification_service.config}


@router.post("/notifications/test")
async def send_test_notification():
    """Send a test notification to verify configuration"""
    try:
        await notification_service.send_test()
        return {"status": "ok", "message": "Test notification sent"}
    except Exception as e:
        logger.error(f"Test notification failed: {e}")
        return {"status": "error", "message": str(e)}
