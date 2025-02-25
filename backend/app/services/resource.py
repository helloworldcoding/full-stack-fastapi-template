import uuid
from datetime import datetime
from typing import Any

import feedparser
from sqlmodel import desc, func, select

from app.api.deps import SessionDep
from app.models import Article, Resource, ResourceCreate, Resources, ResourceUpdate
from app.services.article import query_article


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
    entries = []
    if resource_in.resource_type == "rss":
        feed, entries = parse_rss(resource_in.url)
        resource_in.title = (
            feed["title"] if resource_in.title == "" else resource_in.title
        )
        resource_in.description = (
            feed["description"]
            if resource_in.description == ""
            else resource_in.description
        )
    elif resource_in.resource_type == "url":
        entries = [
            {
                "title": resource_in.title,
                "link": resource_in.url,
                "description": resource_in.description,
                "published": datetime.now(),
                "published_parsed": datetime.now(),
            }
        ]
    item = Resource.model_validate(resource_in)
    session.add(item)
    session.commit()
    session.refresh(item)
    # 批量创建 Article
    articles_to_add = []
    for entry in entries:
        article = query_article(session=session, url=entry["link"])
        if not article:
            article = Article(
                resoure_id=item.id,
                url=entry["link"],
                title=entry["title"],
                abstract=entry["description"],
                publish_at=entry["published"],
                is_active=False,
            )
            articles_to_add.append(article)
    if articles_to_add:
        session.add_all(articles_to_add)
        session.commit()
        session.refresh(item)
    return item


def parse_rss(url: str):
    d = feedparser.parse(url)
    entries = []
    for entry in d.entries:
        entries.append(
            {
                "title": entry.title,
                "link": entry.link,
                "description": entry.description,
                "published": entry.published,
                "published_parsed": entry.published_parsed,
            }
        )
    feed = {
        "title": d.feed.title,
        "link": d.feed.link,
        "description": d.feed.description,
        "published": getattr(d.feed, "published", datetime.now()),
        "published_parsed": getattr(d.feed, "published_parsed", datetime.now()),
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
