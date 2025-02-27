from fastapi import APIRouter, HTTPException

from app.api.deps import SessionDep
from app.models import (
    AIAggregateRequest,
    AIDebugRequest,
    AIDebugResponse,
    ArticleCrawlRequest,
    ArticleCrawlResponse,
    ArticleCreate,
    Articles,
    ArticleSave,
    ArticlesUpdate,
    AudioRequest,
)
from app.services.article import (
    aggregate_content_list,
    crawl_content,
    crawl_url,
    debug_ai,
    get_articles,
    get_audio,
    save_article,
)

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


@router.post("/ai-debug", response_model=AIDebugResponse, dependencies=[])
async def ai_debug(request: AIDebugRequest) -> any:
    """
    调试大模型system prompt
    """
    print(request.content)
    try:
        return debug_ai(request.content, request.system_prompt)
    except Exception as err:
        raise HTTPException(status_code=400, detail=str(err))


@router.post("/aggregate", response_model=AIDebugResponse, dependencies=[])
def aggregate_contents(request: AIAggregateRequest) -> any:
    """
    聚合文章内容
    """
    content_list = request.content_list
    system_prompt = request.system_prompt
    try:
        answer = aggregate_content_list(content_list, system_prompt)
        return {"answer": answer}
    except Exception as err:
        raise HTTPException(status_code=400, detail=str(err))


@router.post("/audio", response_model=AIDebugResponse, dependencies=[])
def tts(request: AudioRequest) -> any:
    """
    生成音频
    """
    content = request.content
    sound = request.sound
    if request.start:
        content = request.start + "\n" + content
    if request.end:
        content = content + "\n" + request.end
    try:
        url = get_audio(content, sound)
        return {"answer": url}
    except Exception as err:
        raise HTTPException(status_code=400, detail=str(err))


@router.post("/save", response_model=ArticleCreate, dependencies=[])
def save_it(request: ArticleSave) -> any:
    """
    保存文章
    """
    return save_article(request)
