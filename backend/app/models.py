import uuid
from datetime import datetime

from dateutil import parser
from pydantic import AnyHttpUrl, BaseModel, EmailStr, field_validator
from sqlalchemy import TEXT, String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlmodel import Column, Field, Relationship, SQLModel  # type: ignore

# 修改models.py文件后
# 生成migrate文件： alembic revision --autogenerate -m 'add resource model'
# 执行更新数据库： alembic upgrade head


# Shared properties
class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on creation
class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=40)


class UserRegister(SQLModel):
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=40)
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on update, all are optional
class UserUpdate(UserBase):
    email: EmailStr | None = Field(default=None, max_length=255)  # type: ignore
    password: str | None = Field(default=None, min_length=8, max_length=40)


class UserUpdateMe(SQLModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)


class UpdatePassword(SQLModel):
    current_password: str = Field(min_length=8, max_length=40)
    new_password: str = Field(min_length=8, max_length=40)


# Database model, database table inferred from class name
class User(UserBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    items: list["Item"] = Relationship(back_populates="owner", cascade_delete=True)


# Properties to return via API, id is always required
class UserPublic(UserBase):
    id: uuid.UUID


class UsersPublic(SQLModel):
    data: list[UserPublic]
    count: int


# Shared properties
class ItemBase(SQLModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)


# Properties to receive on item creation
class ItemCreate(ItemBase):
    pass


# Properties to receive on item update
class ItemUpdate(ItemBase):
    title: str | None = Field(default=None, min_length=1, max_length=255)  # type: ignore


# Database model, database table inferred from class name
class Item(ItemBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    title: str = Field(max_length=255)
    owner_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    owner: User | None = Relationship(back_populates="items")


# Properties to return via API, id is always required
class ItemPublic(ItemBase):
    id: uuid.UUID
    owner_id: uuid.UUID


class ItemsPublic(SQLModel):
    data: list[ItemPublic]
    count: int


# Generic message
class Message(SQLModel):
    message: str


# JSON payload containing access token
class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


# Contents of JWT token
class TokenPayload(SQLModel):
    sub: str | None = None


class NewPassword(SQLModel):
    token: str
    new_password: str = Field(min_length=8, max_length=40)


# Shared properties
class ResourceBase(SQLModel):
    url: str = Field(unique=True, index=True)
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default="", sa_column=Column(TEXT))
    resource_type: str | None = Field(default="", max_length=50)  # rss url
    tags: list[str] | None = Field(default=[], sa_column=Column(ARRAY(String(50))))
    is_active: bool = True
    status: str | None = Field(default="")  # 未处理，已处理
    last_parse_at: datetime | None = Field(default=datetime.now())

    @field_validator("url")
    def validate_url(cls, value: str) -> str:
        AnyHttpUrl(value)
        return value


class Resource(ResourceBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default=datetime.now())
    updated_at: datetime = Field(default=datetime.now())


class ResourceUpdate(ResourceBase):
    pass


class ResourceCreate(ResourceBase):
    pass


class Resources(SQLModel):
    data: list[Resource]
    count: int


class ArticleBase(SQLModel):
    resource_id: str = Field(index=True)
    url: str = Field(index=True, max_length=500)
    title: str = Field(min_length=1, max_length=255)
    abstract: str | None = Field(default="", sa_column=Column(TEXT))
    content: str | None = Field(default="", sa_column=Column(TEXT))
    ai_abstract: str | None = Field(default="", sa_column=Column(TEXT))
    ai_content: str | None = Field(default="", sa_column=Column(TEXT))
    tags: list[str] | None = Field(default=[], sa_column=Column(ARRAY(String(50))))
    cover: str | None = Field(default="")
    day: str | None = Field(default="")
    audio: str | None = Field(default="")
    publish_at: datetime | None = Field(default=datetime.now())
    article_type: str | None = Field(default="", max_length=50)  # ai聚合，原创，转载
    is_active: bool = True
    status: str | None = Field(
        default=""
    )  # 未处理，crawl_content,parse_content,tag_aggregate,generate_audio

    @field_validator("url")
    def validate_url(cls, value: str) -> str:
        if value != "":
            AnyHttpUrl(value)
        return value


class Article(ArticleBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default=datetime.now())
    updated_at: datetime = Field(default=datetime.now())


class ArticleUpdate(ArticleBase):
    pass


class ArticleCreate(ArticleBase):
    pass


class Articles(SQLModel):
    data: list[Article]
    count: int


class ArticlesUpdate(SQLModel):
    data: list[ArticleUpdate]
    count: int


# 解析rss请求
class ParseRssRequest(BaseModel):
    url: str


class RssEntiy(BaseModel):
    title: str
    link: str
    description: str
    published: datetime | str
    resource_id: str
    content: list[str]

    @field_validator("published")
    @classmethod
    def validate_published(cls, value):
        if isinstance(value, str):
            try:
                # 使用 dateutil.parser 来解析日期
                return parser.parse(value)
            except Exception as e:
                raise ValueError(f"Error parsing datetime: {e}")
        return value


class ParseRssResponse(BaseModel):
    data: list[RssEntiy]


# 抓取网页
class CrawlUrlRequest(BaseModel):
    url: str


# 解析网页
class ArticleCrawlRequest(BaseModel):
    url: str


class ArticleCrawlResponse(BaseModel):
    url: str
    html: str
    cleaned_html: str
    markdown: str
    links: dict[str, list[dict]]
    media: dict[str, list[dict]]


class AIDebugRequest(BaseModel):
    content: str
    system_prompt: str


class AIDebugResponse(BaseModel):
    content: str
    tags: list[str]
    abstarct: str
