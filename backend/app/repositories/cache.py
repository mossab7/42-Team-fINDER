from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import CacheEntry


class CacheRepository:
    def __init__(self, session: AsyncSession, ttl_seconds: int):
        self.session = session
        self.ttl = timedelta(seconds=ttl_seconds)

    async def get(self, namespace: str, key: str, *, allow_stale: bool = False) -> tuple[Any, datetime] | None:
        entry = await self.session.scalar(
            select(CacheEntry).where(CacheEntry.namespace == namespace, CacheEntry.cache_key == key)
        )
        if not entry:
            return None
        fetched_at = entry.fetched_at
        if fetched_at.tzinfo is None:
            fetched_at = fetched_at.replace(tzinfo=timezone.utc)
        if not allow_stale and datetime.now(timezone.utc) - fetched_at > self.ttl:
            return None
        return entry.payload, fetched_at

    async def put(self, namespace: str, key: str, payload: Any) -> datetime:
        now = datetime.now(timezone.utc)
        entry = await self.session.scalar(
            select(CacheEntry).where(CacheEntry.namespace == namespace, CacheEntry.cache_key == key)
        )
        if entry:
            entry.payload = payload
            entry.fetched_at = now
        else:
            self.session.add(CacheEntry(namespace=namespace, cache_key=key, payload=payload, fetched_at=now))
        await self.session.commit()
        return now

    async def clear(self, namespace: str | None = None) -> None:
        statement = delete(CacheEntry)
        if namespace:
            statement = statement.where(CacheEntry.namespace == namespace)
        await self.session.execute(statement)
        await self.session.commit()

