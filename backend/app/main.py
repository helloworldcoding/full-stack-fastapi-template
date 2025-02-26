# from apscheduler.triggers.cron import CronTrigger
from contextlib import asynccontextmanager
from pathlib import Path

import sentry_sdk
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware

from app.api.main import api_router
from app.core.config import settings
from app.services.article import (
    aggregate_by_tag,
    ai_parse_content,
    crawl_content,
    generate_audio,
)
from app.services.resource import parse_resource

# 初始化调度器
scheduler = AsyncIOScheduler()


# 配置任务
def configure_scheduler():
    scheduler.add_job(
        parse_resource,
        trigger=IntervalTrigger(seconds=10),
        id="parse_resource",
        max_instances=1,  # 确保同一时间只有一个任务实例在运行
        coalesce=True,  # 如果错过了执行时间，只运行一次
    )
    # 每 10 秒执行一次（同步任务）
    scheduler.add_job(
        crawl_content,
        trigger=IntervalTrigger(seconds=20),
        id="crawl_content",
        max_instances=1,  # 确保同一时间只有一个任务实例在运行
        coalesce=True,  # 如果错过了执行时间，只运行一次
        kwargs={"limit": 1},
    )

    scheduler.add_job(
        ai_parse_content,
        trigger=IntervalTrigger(seconds=30),
        id="ai_parse_content",
        max_instances=1,  # 确保同一时间只有一个任务实例在运行
        coalesce=True,  # 如果错过了执行时间，只运行一次
        kwargs={"limit": 1},
    )

    scheduler.add_job(
        aggregate_by_tag,
        trigger=IntervalTrigger(seconds=40),
        id="aggregate_by_tag",
        max_instances=1,  # 确保同一时间只有一个任务实例在运行
        coalesce=True,  # 如果错过了执行时间，只运行一次
    )

    scheduler.add_job(
        generate_audio,
        trigger=IntervalTrigger(seconds=50),
        id="generate_audio",
        max_instances=1,  # 确保同一时间只有一个任务实例在运行
        coalesce=True,  # 如果错过了执行时间，只运行一次
    )

    # # 每天 8:30 执行一次（异步任务）
    # scheduler.add_job(
    #     async_cron_task,
    #     trigger=CronTrigger(hour=8, minute=30),
    #     id="cron_job",
    # )


def custom_generate_unique_id(route: APIRoute) -> str:
    return f"{route.tags[0]}-{route.name}"


if settings.SENTRY_DSN and settings.ENVIRONMENT != "local":
    sentry_sdk.init(dsn=str(settings.SENTRY_DSN), enable_tracing=True)


# 定义 FastAPI 生命周期管理器
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时逻辑
    print(f"Starting {app.title}...")
    print("Starting scheduler...")
    configure_scheduler()
    scheduler.start()
    try:
        yield  # 保持运行直到应用关闭
    finally:
        # 关闭时逻辑
        print("Shutting down scheduler...")
        print(f"Shutting down {app.title}...")
        scheduler.shutdown()


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    generate_unique_id_function=custom_generate_unique_id,
    lifespan=lifespan,
)


# Set all CORS enabled origins
if settings.all_cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.all_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix=settings.API_V1_STR)


current_dir = Path(__file__).parent
static_dir = current_dir / "static"
prefix = settings.STATIC_PREFIX
app.mount("/" + prefix, StaticFiles(directory=static_dir), name="static")
