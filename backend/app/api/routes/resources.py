import uuid

from fastapi import APIRouter, HTTPException

from app.api.deps import SessionDep
from app.models import (
    ParseRssRequest,
    ParseRssResponse,
    Resource,
    ResourceCreate,
    Resources,
    ResourceUpdate,
)
from app.services.resource import (
    check_resource,
    create_resource,
    get_resources,
    parse_rss,
    update_resource,
)

router = APIRouter(prefix="/resources", tags=["resources"])


@router.get("/", response_model=Resources)
def read_resources(session: SessionDep, skip: int = 0, limit: int = 100) -> any:
    """
    Retrieve resources.
    """
    return get_resources(session=session, skip=skip, limit=limit)


@router.post("/add", response_model=Resource)
def add_resources(*, session: SessionDep, resource_in: ResourceCreate) -> any:
    """
    Create new resource.
    """
    exists = check_resource(session=session, url=resource_in.url)
    if exists:
        raise HTTPException(status_code=400, detail="资源已经存在")
    return create_resource(session=session, resource_in=resource_in)


@router.post("/update/{id}", response_model=ResourceUpdate)
def update_resources(
    *,
    session: SessionDep,
    id: uuid.UUID,
    resource_in: ResourceUpdate,
) -> any:
    """
    Update an resource.
    """
    return update_resource(session=session, id=id, item_in=resource_in)


@router.post("/parse-rss", response_model=ParseRssResponse, dependencies=[])
def crawl_resources(request: ParseRssRequest) -> any:
    """
    Crawl resource.
    """
    url = request.url
    _, enties = parse_rss(url)
    return {"data": enties}
