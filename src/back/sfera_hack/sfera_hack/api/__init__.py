from fastapi import APIRouter
from .sfera import router as sfera_router

# Create main API router
router = APIRouter(prefix="/api", tags=["api"])

# Include all sub-routers
router.include_router(sfera_router)
