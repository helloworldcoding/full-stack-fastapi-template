from fastapi import APIRouter

from app.api.deps import SessionDep
from app.models import (
    AIDebugRequest,
    AIDebugResponse,
    ArticleCrawlRequest,
    ArticleCrawlResponse,
    Articles,
    ArticlesUpdate,
)
from app.services.article import crawl_content, crawl_url, get_articles

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


@router.post("/crawl", response_model=ArticleCrawlResponse, dependencies=[])
async def crawl_resources(request: ArticleCrawlRequest) -> any:
    """
    Crawl resource.
    """
    url = request.url
    try:
        rr = await crawl_url(url)
        return rr
    except Exception as err:
        return {"error": str(err)}


@router.post("ai-debug", response_model=AIDebugResponse, dependencies=[])
async def ai_debug(request: AIDebugRequest) -> any:
    """
    调试大模型system prompt
    """
    print(request.content)
    pass
