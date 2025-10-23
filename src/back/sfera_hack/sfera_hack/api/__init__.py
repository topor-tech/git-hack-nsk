from fastapi import APIRouter

from .pulse import router as pulse_router
from .sfera import router as sfera_router

# Create main API router
router = APIRouter(prefix="/api")

# Include all sub-routers
router.include_router(sfera_router)
router.include_router(pulse_router)
