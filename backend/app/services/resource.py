import uuid
from datetime import datetime, timedelta
from typing import Any

import feedparser
from sqlalchemy import or_  # 添加这个导入
from sqlmodel import Session, create_engine, desc, func, select, update

from app.api.deps import SessionDep
from app.core.config import settings
from app.models import Article, Resource, ResourceCreate, Resources, ResourceUpdate
from app.services.article import query_article

engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))


def get_resources(session: SessionDep, skip: int = 0, limit: int = 100) -> Any:
    """
    Retrieve resources.
    """
    count_statement = select(func.count()).select_from(Resource)
    count = session.exec(count_statement).one()
    statement = (
        select(Resource).order_by(desc(Resource.created_at)).offset(skip).limit(limit)
    )
    items = session.exec(statement).all()
    return Resources(data=items, count=count)


def read_resource(session: SessionDep, id: uuid.UUID) -> Resource | None:
    """
    Get item by ID.
    """
    item = session.get(Resource, id)
    return item


def create_resource(*, session: SessionDep, resource_in: ResourceCreate) -> Any:
    """
    Create new  resource.
    """
    resource_in.status = "created"
    item = Resource.model_validate(resource_in)
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


def parse_resource():
    """
    解析内容,每一个小时，扫描一下资源，如果资源没有解析过，就解析一下
    """
    articles_to_add = []
    with Session(engine) as session:
        statement = select(Resource).where(
            or_(
                Resource.last_parse_at.is_(None),
                Resource.last_parse_at < datetime.now() - timedelta(hours=1),
            )
        )
        resources = session.exec(statement).all()
        entries = []
        for resource in resources:
            if resource.resource_type == "rss":
                try:
                    feed, entries = parse_rss(resource.url, resource.id)
                except Exception as err:
                    print(err)
                    continue
                resource.title = (
                    feed["title"] if resource.title == "" else resource.title
                )
                resource.description = (
                    feed["description"]
                    if resource.description == ""
                    else resource.description
                )
            elif resource.resource_type == "url":
                entries = [
                    {
                        "title": resource.title,
                        "link": resource.url,
                        "description": resource.description,
                        "published": datetime.now(),
                        "resource_id": resource.id,
                    }
                ]
        resource_ids = []
        for entry in entries:
            article = query_article(session=session, url=entry["link"])
            if not article:
                article = Article(
                    resource_id=entry["resource_id"],
                    url=entry["link"],
                    title=entry["title"],
                    abstract=entry["description"],
                    publish_at=entry["published"],
                    is_active=False,
                )
                resource_ids.append(entry["resource_id"])
                articles_to_add.append(article)
        if articles_to_add:
            session.add_all(articles_to_add)
            session.commit()
        if resource_ids:
            # 更新这些资源的 last_parse_at
            statement = (
                update(Resource)
                .where(Resource.id.in_(resource_ids))
                .values(last_parse_at=datetime.now())
            )
            session.exec(statement)
            session.commit()


def parse_rss(url: str, resource_id: str = ""):
    d = feedparser.parse(url)
    entries = []
    for entry in d.entries:
        content = []
        if hasattr(entry, "content"):
            if isinstance(entry.content, str):
                content.append(entry.content)
            elif isinstance(entry.content, list):
                for item in entry.content:
                    content.append(item.value)
        entries.append(
            {
                "title": entry.title,
                "link": entry.link,
                "description": entry.description,
                "published": entry.published,
                "resource_id": resource_id,
                "content": content,
            }
        )
    feed = {
        "title": d.feed.title,
        "link": d.feed.link,
        "description": d.feed.description,
        "published": getattr(d.feed, "published", datetime.now()),
    }
    return feed, entries


def update_resource(
    *,
    session: SessionDep,
    id: uuid.UUID,
    item_in: ResourceUpdate,
) -> any:
    """
    Update an resource.
    """
    item = session.get(Resource, id)
    if not item:
        return None
    update_dict = item_in.model_dump(exclude_unset=True)
    update_dict["updated_at"] = datetime.now()
    item.sqlmodel_update(update_dict)
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


def check_resource(session: SessionDep, url: str) -> Resource | None:
    statement = select(Resource).where(Resource.url == url)
    return session.exec(statement).first()
