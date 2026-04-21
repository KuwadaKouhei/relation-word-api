from contextlib import asynccontextmanager

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.v1 import analogy, cascade, health, related, similarity
from app.core.config import get_settings
from app.core.logging import configure_logging, logger
from app.core.middleware import RequestLoggingMiddleware
from app.core.rate_limit import limiter
from app.services.ann import index as ann_index
from app.services.embedding import store


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    settings = get_settings()
    logger.info("startup_begin", env=settings.app_env)
    store.load(settings.model_ja_path)
    ann_index.load(settings.ann_index_path, settings.ann_labels_path)
    logger.info(
        "startup_complete", ready=store.is_ready(), ann_available=ann_index.available
    )
    yield
    logger.info("shutdown")


app = FastAPI(title="Relation Word API", version="0.1.0", lifespan=lifespan)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

Instrumentator(
    excluded_handlers=["/metrics", "/v1/health", "/v1/ready"],
).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

app.include_router(health.router, prefix="/v1", tags=["health"])
app.include_router(related.router, prefix="/v1", tags=["related"])
app.include_router(similarity.router, prefix="/v1", tags=["similarity"])
app.include_router(analogy.router, prefix="/v1", tags=["analogy"])
app.include_router(cascade.router, prefix="/v1", tags=["cascade"])
