"""
Configuration API Endpoints
"""
from fastapi import APIRouter, HTTPException, Depends
from app.models.schemas import ConfigSchema, SuccessResponse
from app.services.seeder_service import seeder_service
from app.core.bittorrent_client import list_available_clients
from app.core.auth import verify_token
import logging

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(verify_token)])


@router.get("/config")
async def get_config():
    """Get current configuration"""
    config = seeder_service.get_config()
    return config


@router.put("/config")
async def update_config(config: ConfigSchema):
    """Update configuration"""
    try:
        config_dict = config.model_dump()
        logger.debug(f"🔧 API: Received config update payload: {config_dict}")
        await seeder_service.update_config(config_dict)
        
        # Get the updated config to ensure consistency
        updated_config = seeder_service.get_config()
        logger.info("✅ API: Configuration updated successfully")
        
        return SuccessResponse(
            message="Configuration updated successfully",
            data=updated_config  # Return actual saved config
        )
    except ValueError as ve:
        # Validation errors from Pydantic - user friendly
        error_msg = str(ve)
        logger.warning(f"⚠️ API: Config validation error: {error_msg}")
        raise HTTPException(status_code=400, detail=error_msg)
    except Exception as e:
        # System errors - simplified for user
        logger.error(f"❌ API: Config update failed: {e}")
        if "permission" in str(e).lower():
            error_msg = "Save error: check config file permissions"
        elif "disk" in str(e).lower() or "space" in str(e).lower():
            error_msg = "Save error: insufficient disk space"
        elif "network" in str(e).lower():
            error_msg = "Network error while updating configuration"
        else:
            error_msg = "Internal error while updating configuration"
        
        raise HTTPException(status_code=500, detail=error_msg)


@router.get("/clients")
async def get_available_clients():
    """Get list of available client files"""
    clients = list_available_clients()
    return {"clients": clients}


@router.post("/config/reset")
async def reset_config():
    """Reset configuration to default values from environment"""
    try:
        from app.services.config_manager import ConfigManager
        
        logger.info("🔄 API: Config reset to defaults requested")
        # Use the canonical default builder so ALL fields are reset
        default_config = ConfigManager._default_config()
        
        await seeder_service.update_config(default_config)
        
        return SuccessResponse(
            message="Configuration reset to defaults",
            data=default_config
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

