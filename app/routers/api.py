from fastapi import APIRouter
from . import hospitals, scraper

router = APIRouter()

# specific routers
router.include_router(
    hospitals.router,
    prefix="/hospitals",
    tags=["hospitals"]
)

router.include_router(
    scraper.router,
    prefix="/scraper",
    tags=["scraper"]
) 