import uuid
from datetime import datetime, timedelta
from typing import Any

from crawl4ai import AsyncWebCrawler
from sqlalchemy import or_  # 添加这个导入
from sqlmodel import Session, create_engine, desc, func, select

from app.api.deps import SessionDep
from app.core.config import settings
from app.models import Article, ArticleCreate, Articles, ArticleUpdate
from app.services.llm import (
    deal_content_parse_ret,
    get_content_parse_system_prompt,
    get_tag_aggregate_system_prompt,
    request_ai,
)
from app.services.tts import bk_tts

engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))


def get_articles(session: SessionDep, skip: int = 0, limit: int = 100) -> Any:
    """
    Retrieve articles.
    """
    count_statement = select(func.count()).select_from(Article)
    count = session.exec(count_statement).one()
    statement = (
        select(Article).order_by(desc(Article.created_at)).offset(skip).limit(limit)
    )
    items = session.exec(statement).all()
    return Articles(data=items, count=count)


def create_article(*, session: SessionDep, article_in: ArticleCreate) -> Any:
    """
    Create new  article.
    """
    item = Article.model_validate(article_in)
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


def update_article(
    *,
    session: SessionDep,
    id: uuid.UUID,
    item_in: ArticleUpdate,
) -> any:
    """
    Update an article.
    """
    item = session.get(Article, id)
    if not item:
        return None
    update_dict = item_in.model_dump(exclude_unset=True)
    update_dict["updated_at"] = datetime.now()
    item.sqlmodel_update(update_dict)
    session.add(item)
    session.commit()
    return item


def query_article(session: SessionDep, url: str = "", day: str = "") -> Article:
    """
    通过url、day获取文章，判断文章是否已经抓取了
    """
    statement = select(Article).where(Article.url == url)
    if day:
        statement = statement.where(Article.day == day)
    return session.exec(statement).first()


async def crawl_content(limit: int = 1) -> Articles | None:
    """
    Get content
    """
    # 创建新的数据库会话
    update_list = []
    with Session(engine) as session:
        articles = (
            select(Article)
            .where(Article.is_active.is_(False))
            .order_by(desc(Article.created_at))
            .limit(limit)
        )
        urls = []
        for article in session.exec(articles).all():
            urls.append((article.url, article.id))
        if not urls:
            print("not article to crawl")
            return
        async with AsyncWebCrawler() as crawler:
            for url, article_id in urls:
                try:
                    result = await crawler.arun(
                        url=url,
                    )
                    # 直接通过 ID 获取文章实例
                    article = session.get(Article, article_id)
                    if article:
                        article.content = result.markdown_v2.raw_markdown
                        article.is_active = True
                        article.status = "crawl_content"
                        article.updated_at = datetime.now()
                        session.add(article)
                        session.commit()
                        session.refresh(article)
                        article.content = ""
                        update_list.append(article)
                except Exception as err:
                    print(f"crawl {url} error", err)
    return Articles(data=update_list, count=len(update_list))


async def ai_parse_content(limit: int = 10):
    """
    AI parse content
    """
    with Session(engine) as session:
        stmt = (
            select(Article)
            .where(
                Article.is_active.is_(True),
                Article.content != "",
                or_(
                    Article.ai_content == "",
                    Article.ai_content.is_(None),
                ),
            )
            .order_by(desc(Article.created_at))
            .limit(limit)
        )
        articles = session.exec(stmt).all()
        if not articles:
            print("not article to parse content ")
            return
        for article in articles:
            try:
                system_prompt = get_content_parse_system_prompt()
                ret = request_ai("gpt-4o-mini", article.content, system_prompt)
                if ret["status_code"] != 200:
                    print(f"parse {article.url} content error")
                    continue
                result = deal_content_parse_ret(ret["answer"])
                article.ai_content = result["content"]
                article.ai_abstract = result["abstract"]
                article.tags = result["tags"]
                article.status = "parse_content"
                article.updated_at = datetime.now()
                session.add(article)
                session.commit()
            except Exception as err:
                print(f"parse {article.url} content error", err)


def aggregate_by_tag() -> list[str]:
    """
    Get all unique tags from Article table
    """
    with Session(engine) as session:
        # Using unnest since tags is stored as an ARRAY type
        statement = select(Article).where(
            Article.is_active.is_(True),
            Article.content != "",
            Article.ai_content != "",
            Article.status == "parse_content",
            Article.created_at > datetime.now() - timedelta(hours=1),
        )
        articles = session.exec(statement).all()
        if not articles:
            print("not article to aggregate by tag")
            return
        tags = []
        article_ids = []
        for article in articles:
            tags.extend(article.tags)
            article_ids.append(article.id)
        tags = list(set(tags))
        sp = get_tag_aggregate_system_prompt()
        for tag in tags:
            tmp_list = [article for article in articles if tag in article.tags]
            query = ""
            resource_ids = []
            for article in tmp_list:
                query += f"\n{article.content}\n"
                resource_ids.append(str(article.id))
            try:
                ret = request_ai("gpt-4o-mini", query, sp)
                if ret["status_code"] != 200:
                    print(f"parse {article.url} content error")
                    continue
                result = deal_content_parse_ret(ret["answer"])
                combined_tags = (
                    result["tags"] if tag in result["tags"] else [tag] + result["tags"]
                )
                article_data = ArticleCreate(
                    url="",
                    title=f"{tag}-聚合",
                    ai_abstract=result["abstract"],
                    ai_content=result["content"],
                    content=query,
                    tags=combined_tags,
                    article_type="ai聚合",
                    resource_id=",".join(resource_ids),
                )
                # Convert ArticleCreate to Article model
                article = Article.model_validate(article_data)
                session.add(article)
                session.commit()
            except Exception as err:
                print(f"aggregate {tag} error", err)
                print(f"Error details: {repr(err)}")
                continue

        # update article status to tag_aggregate if id in article_ids
        update_stmt = select(Article).where(Article.id.in_(article_ids))
        articles_to_update = session.exec(update_stmt).all()
        for article in articles_to_update:
            article.status = "tag_aggregate"
            article.updated_at = datetime.now()
            session.add(article)
            session.commit()


def generate_audio() -> list[str]:
    """
    Generate audio for articles
    """
    with Session(engine) as session:
        stmt = (
            select(Article)
            .where(
                Article.is_active.is_(True),
                Article.content != "",
                Article.ai_content != "",
                Article.audio == "",
                Article.article_type == "ai聚合",
                Article.created_at > datetime.now() - timedelta(hours=1),
            )
            .order_by(desc(Article.created_at))
            .limit(10)
        )
        articles = session.exec(stmt).all()
        if not articles:
            print("not article to generate audio")
            return
        for article in articles:
            try:
                audio_url = bk_tts(article.ai_content)
                article.audio = audio_url
                article.status = "generate_audio"
                article.updated_at = datetime.now()
                session.add(article)
                session.commit()
            except Exception as err:
                print(f"generate audio {article.id} content error", err)
