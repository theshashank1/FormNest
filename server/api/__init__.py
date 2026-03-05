"""
FormNest — API Router Registration
"""

from fastapi import APIRouter

from server.api.auth import router as auth_router
from server.api.forms import router as forms_router
from server.api.projects import router as projects_router
from server.api.submissions import router as submissions_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(projects_router)
api_router.include_router(forms_router)

# Public submission endpoint (no /api/v1 prefix)
public_router = APIRouter()
public_router.include_router(submissions_router)

__all__ = ["api_router", "public_router"]
