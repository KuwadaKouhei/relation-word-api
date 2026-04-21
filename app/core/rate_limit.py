from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import get_settings


def _key(request: Request) -> str:
    api_key = request.headers.get("x-api-key")
    if api_key:
        return f"apikey:{api_key}"
    return f"ip:{get_remote_address(request)}"


limiter = Limiter(
    key_func=_key,
    default_limits=[get_settings().rate_limit_default],
    storage_uri=get_settings().redis_url,
    headers_enabled=True,
)
