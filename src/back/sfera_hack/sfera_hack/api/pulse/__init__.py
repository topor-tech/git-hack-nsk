from fastapi import APIRouter

from .gat_available_repos import router as get_available_repos_router
from .get_available_projects import router as get_available_projects_router
from .get_wip_branches import router as get_wip_branches_router
from .last_commits import router as last_commits_router
from .get_dashboard import router as get_dashboard_router
from .get_diffs_dashboard import router as get_diffs_dashboard_router

router = APIRouter(prefix="/pulse", tags=["pulse"])

router.include_router(get_available_projects_router)
router.include_router(get_available_repos_router)
router.include_router(get_wip_branches_router)
router.include_router(last_commits_router)
router.include_router(get_dashboard_router)
router.include_router(get_diffs_dashboard_router)