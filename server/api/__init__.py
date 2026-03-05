"""
FormNest — API Router Registration
"""

from fastapi import APIRouter

from server.api.auth import router as auth_router
from server.api.forms import router as forms_router
from server.api.projects import router as projects_router
from server.api.public import router as public_router_routes
from server.api.submissions import router as submissions_router
from server.api.submissions import submissions_auth_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(projects_router)
api_router.include_router(forms_router)
api_router.include_router(submissions_auth_router)

# Public routes — no /api/v1 prefix
public_router = APIRouter()
public_router.include_router(submissions_router)
public_router.include_router(public_router_routes)

__all__ = ["api_router", "public_router"]
