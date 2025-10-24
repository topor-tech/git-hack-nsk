from fastapi import APIRouter
from .login import router as login_router
from .projects import router as projects_router
from .commits import router as commits_router

# Create main router for sfera API
router = APIRouter(prefix="/sfera", tags=["sfera"])

# Include all sub-routers
router.include_router(login_router)
router.include_router(projects_router)
router.include_router(commits_router)
