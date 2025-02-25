from fastapi import APIRouter

from app.api.deps import SessionDep
from app.models import Articles, ArticlesUpdate
from app.services.article import crawl_content, get_articles

router = APIRouter(prefix="/articles", tags=["articles"])


@router.get("/", response_model=Articles)
def read_resources(session: SessionDep, skip: int = 0, limit: int = 100) -> any:
    """
    Retrieve resources.
    """
    return get_articles(session=session, skip=skip, limit=limit)


@router.post("/crawl-content", response_model=ArticlesUpdate)
async def crawl() -> any:
    """
    Create new resource.
    """
    return await crawl_content(limit=1)
