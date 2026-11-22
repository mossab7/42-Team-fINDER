import asyncio

import pytest
from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.database import CacheEntry


@pytest.mark.asyncio
async def test_metadata_scan_persistence_filters_and_exports(client):
    campuses = await client.get("/api/campuses")
    assert campuses.status_code == 200
    assert campuses.json()["source"] == "demo"
    assert set(campuses.json()["items"][0]) == {"id", "name", "city", "country"}
    async with SessionLocal() as session:
        entry = await session.scalar(select(CacheEntry).where(CacheEntry.cache_key == "all"))
        assert entry is not None
        assert entry.namespace == "campuses:demo"
    cached = await client.get("/api/campuses")
    assert cached.json()["fetched_at"] == campuses.json()["fetched_at"]
    refreshed = await client.get("/api/campuses?force_refresh=true")
    assert refreshed.json()["fetched_at"] >= cached.json()["fetched_at"]
    project_configuration = await client.get("/api/projects/101/configuration?campus_id=1")
    assert project_configuration.status_code == 200
    assert project_configuration.json()["max_team_size"] == 5
    assert project_configuration.json()["maximum_source"] == "group_rule"
    payload = {"campus_id":1,"campus_name":"Paris","project_id":101,"project_name":"ft_transcendence","promotion":{"type":"cursus_year","year":2024},"max_team_size":5,"include_unavailable":False,"force_refresh":False}
    response = await client.post("/api/scans", json=payload)
    assert response.status_code == 202
    scan_id = response.json()["id"]
    for _ in range(40):
        scan = (await client.get(f"/api/scans/{scan_id}")).json()
        if scan["status"] == "completed": break
        await asyncio.sleep(.03)
    assert scan["status"] == "completed"
    students = await client.get(f"/api/scans/{scan_id}/students", params={"search":"Ada","sort":"-level"})
    assert students.json()["total"] == 1
    teams = await client.get(f"/api/scans/{scan_id}/teams")
    assert teams.json()["total"] == 2
    csv_response = await client.get(f"/api/scans/{scan_id}/export?format=csv")
    assert csv_response.status_code == 200 and "record_type" in csv_response.text and "ada" in csv_response.text
    json_response = await client.get(f"/api/scans/{scan_id}/export?format=json")
    assert json_response.status_code == 200 and json_response.json()["summary"]["total_eligible_students"] == 5
    history = await client.get("/api/scans")
    assert len(history.json()) == 1


@pytest.mark.asyncio
async def test_error_and_validation_paths(client):
    assert (await client.get("/api/scans/missing")).status_code == 404
    invalid = await client.post("/api/scans", json={"campus_id":1,"project_id":1,"promotion":{"type":"date_range","start_date":"2025-02-01","end_date":"2025-01-01"}})
    assert invalid.status_code == 422
