import uuid
from datetime import datetime

from pydantic import AnyHttpUrl, EmailStr, field_validator
from sqlalchemy import String
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
    # url: AnyHttpUrl = Field(unique=True, index=True, max_length=500)
    url: str = Field(unique=True, index=True, max_length=500)
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default="", max_length=5000)
    resource_type: str | None = Field(default="", max_length=50)  # rss url
    tags: list[str] | None = Field(default=[], sa_column=Column(ARRAY(String(50))))
    is_active: bool = True

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
    resoure_id: str = Field(index=True, min_length=0, max_length=4024)
    url: str = Field(index=True, max_length=500)
    title: str = Field(min_length=1, max_length=255)
    abstract: str | None = Field(default="", max_length=5000)
    content: str | None = Field(default="")
    ai_abstract: str | None = Field(default="")
    ai_content: str | None = Field(default="")
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
