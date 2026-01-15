"""
Error Information API Endpoints
"""
from fastapi import APIRouter
from typing import Dict

from app.core.error_explanations import get_error_explanation, explain_seeding_with_revoked_rights

router = APIRouter()

@router.get("/errors/explain")
async def explain_error(message: str) -> Dict:
    """Get explanation for an error message"""
    explanation = get_error_explanation(message)
    return {
        "error": message,
        "explanation": explanation
    }

@router.get("/errors/seeding-info")
async def seeding_info() -> Dict:
    """Get information about seeding with revoked rights"""
    return {
        "title": "Seeding avec droits révoqués",
        "explanation": explain_seeding_with_revoked_rights()
    }

@router.get("/errors/common")
async def common_errors() -> Dict:
    """Get list of common errors and their explanations"""
    from app.core.error_explanations import ERROR_EXPLANATIONS
    return {
        "commonErrors": ERROR_EXPLANATIONS
    }