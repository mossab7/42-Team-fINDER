import hashlib
import os
import time
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

from app.core.config import Settings
from app.services.fortytwo import FortyTwoAPIError, FortyTwoClient


ALLOWED_AVATAR_HOST = "cdn.intra.42.fr"
CONTENT_TYPE_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


class InvalidAvatarURL(ValueError):
    pass


def validate_avatar_url(url: str) -> str:
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError as exc:
        raise InvalidAvatarURL("Invalid avatar URL") from exc
    if (
        parsed.scheme != "https"
        or parsed.hostname != ALLOWED_AVATAR_HOST
        or parsed.username is not None
        or parsed.password is not None
        or port not in (None, 443)
    ):
        raise InvalidAvatarURL("Only official 42 CDN avatar URLs are accepted")
    return url


def _cached_file(directory: Path, cache_key: str, ttl_seconds: int) -> tuple[Path, str] | None:
    now = time.time()
    for content_type, extension in CONTENT_TYPE_EXTENSIONS.items():
        path = directory / f"{cache_key}{extension}"
        if path.is_file() and now - path.stat().st_mtime <= ttl_seconds:
            return path, content_type
    return None


async def fetch_avatar(url: str, settings: Settings) -> tuple[Path, str, bool]:
    """Fetch a 42 avatar with backend OAuth and persist it in the local cache."""
    validate_avatar_url(url)
    directory = Path(settings.avatar_cache_directory)
    directory.mkdir(parents=True, exist_ok=True)
    cache_key = hashlib.sha256(url.encode("utf-8")).hexdigest()
    cached = _cached_file(directory, cache_key, settings.avatar_cache_ttl_seconds)
    if cached:
        return cached[0], cached[1], True

    client = FortyTwoClient(settings)
    try:
        response = await client.request("GET", url)
    finally:
        await client.close()

    content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
    extension = CONTENT_TYPE_EXTENSIONS.get(content_type)
    if extension is None:
        raise FortyTwoAPIError("42 CDN returned an unsupported avatar format")
    if not response.content or len(response.content) > settings.avatar_max_bytes:
        raise FortyTwoAPIError("42 CDN returned an invalid avatar size")

    path = directory / f"{cache_key}{extension}"
    temporary = directory / f".{cache_key}-{uuid4().hex}.tmp"
    try:
        temporary.write_bytes(response.content)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return path, content_type, False
