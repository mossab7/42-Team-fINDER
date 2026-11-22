import httpx
import pytest

from app.core.config import Settings
from app.services import avatars
from app.services.avatars import InvalidAvatarURL, fetch_avatar, validate_avatar_url


def test_avatar_url_is_restricted_to_official_42_cdn():
    valid = "https://cdn.intra.42.fr/users/example.jpg"
    assert validate_avatar_url(valid) == valid
    for invalid in (
        "http://cdn.intra.42.fr/users/example.jpg",
        "https://cdn.intra.42.fr.evil.test/example.jpg",
        "https://example.test/avatar.jpg",
    ):
        with pytest.raises(InvalidAvatarURL):
            validate_avatar_url(invalid)


@pytest.mark.asyncio
async def test_avatar_is_downloaded_with_api_client_and_then_cached(tmp_path, monkeypatch):
    calls = 0

    class FakeClient:
        def __init__(self, settings):
            assert settings.ft_client_id == "id"

        async def request(self, method, url):
            nonlocal calls
            calls += 1
            assert method == "GET"
            assert url.startswith("https://cdn.intra.42.fr/")
            return httpx.Response(200, headers={"content-type": "image/jpeg"}, content=b"jpeg-bytes")

        async def close(self):
            return None

    monkeypatch.setattr(avatars, "FortyTwoClient", FakeClient)
    settings = Settings(
        ft_client_id="id",
        ft_client_secret="secret",
        demo_mode=False,
        avatar_cache_directory=str(tmp_path),
    )
    url = "https://cdn.intra.42.fr/users/example.jpg"
    first_path, first_type, first_hit = await fetch_avatar(url, settings)
    second_path, second_type, second_hit = await fetch_avatar(url, settings)

    assert first_path == second_path
    assert first_path.read_bytes() == b"jpeg-bytes"
    assert first_type == second_type == "image/jpeg"
    assert first_hit is False and second_hit is True
    assert calls == 1
