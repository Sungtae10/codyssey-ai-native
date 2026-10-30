"""데이터 API (CRUD 4개 + summary) 테스트."""
from __future__ import annotations

import datetime as dt


def test_list_and_filters(client):
    r = client.get("/api/data")
    assert r.status_code == 200 and r.json()["count"] == 251
    items = r.json()["items"]
    assert items[0]["date"] == "2025-10-16" and items[-1]["date"] == "2026-10-16"

    r = client.get("/api/data", params={"order": "desc", "limit": 3})
    assert [i["date"] for i in r.json()["items"]] == ["2026-10-16", "2026-10-15", "2026-10-14"]

    r = client.get("/api/data", params={"start": "2026-10-01", "end": "2026-10-16"})
    assert r.json()["count"] == 11

    assert client.get("/api/data", params={"limit": 0}).status_code == 422
    assert client.get("/api/data", params={"start": "2026-13-01"}).status_code == 422


def test_create_update_delete_flow(client):
    before = client.get("/api/data/summary").json()["count"]

    r = client.post("/api/data", json={"date": "2026-10-19", "value": 1333.5, "memo": "  직접 입력  "})
    assert r.status_code == 201, r.text
    rec = r.json()
    assert rec["memo"] == "직접 입력" and rec["id"]

    after = client.get("/api/data/summary").json()
    assert after["count"] == before + 1 and after["end_date"] == "2026-10-19"  # 캐시가 바로 갱신됨

    r = client.post("/api/data", json={"date": "2026-10-19", "value": 1, "memo": ""})
    assert r.status_code == 409  # 같은 날짜 중복

    r = client.put(f"/api/data/{rec['id']}", json={"value": 1340.25})
    assert r.status_code == 200 and r.json()["value"] == 1340.25 and r.json()["memo"] == "직접 입력"

    r = client.put(f"/api/data/{rec['id']}", json={"date": "2026-10-16"})
    assert r.status_code == 409  # 다른 레코드와 날짜 충돌

    assert client.put(f"/api/data/{rec['id']}", json={}).status_code == 422  # 바꿀 항목 없음
    assert client.put(f"/api/data/{rec['id']}", json={"value": False}).status_code == 422  # true/false 금지
    assert client.put(f"/api/data/{rec['id']}", json={"value": -1}).status_code == 422  # 0 이하 금지
    assert client.put("/api/data/notExistingId123", json={"value": 1}).status_code == 404
    assert client.put("/api/data/bad$id", json={"value": 1}).status_code == 422

    r = client.delete(f"/api/data/{rec['id']}")
    assert r.status_code == 200 and r.json() == {"id": rec["id"], "deleted": True}
    assert client.delete(f"/api/data/{rec['id']}").status_code == 404
    assert client.get("/api/data/summary").json()["count"] == before


def test_create_validation_messages(client):
    cases = [
        {"date": "2026/10/19", "value": 1},
        {"date": "2999-01-01", "value": 1},
        {"date": "1899-12-31", "value": 1},
        {"date": "2026-10-19", "value": "abc"},
        {"date": "2026-10-19", "value": 1e13},
        {"date": "2026-10-19", "value": 1, "memo": "가" * 201},
        {"value": 1},
        {"date": "2026-10-19", "value": True},
        {"date": "2026-10-19", "value": "1334.03"},
        {"date": "2026-10-19", "value": 0},
        {"date": "2026-10-19", "value": -5},
        {"date": "2026-10-19", "value": 1e8},
        {"date": (dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).date() + dt.timedelta(days=1)).isoformat(), "value": 1},
    ]
    for body in cases:
        r = client.post("/api/data", json=body)
        assert r.status_code == 422, body
        assert r.json()["detail"].startswith("입력값을 확인하세요")


def test_summary_shape(client):
    s = client.get("/api/data/summary").json()
    assert s["period"] == "2025-10-16 ~ 2026-10-16" and s["count"] == 251
    assert s["metrics"]["max"] == 1555.96 and s["metrics"]["max_date"] == "2026-06-05"
    assert s["metrics"]["min"] == 1334.03 and s["metrics"]["latest_date"] == "2026-10-16"
    assert s["trend"].startswith("하락") and s["trend_detail"]["window"] == 20
    assert len(s["monthly"]) == 13 and len(s["recent"]) == 10


def test_statistics_and_export(client):
    st = client.get("/api/data/statistics").json()
    assert st["count"] == 251 and st["moving_averages"]["ma20"] == 1353.11
    assert st["max_drawdown"]["start_date"] == "2026-06-05"

    r = client.get("/api/data/export", params={"format": "csv"})
    assert r.status_code == 200 and "attachment" in r.headers["content-disposition"]
    text = r.content.decode("utf-8")
    assert text.startswith("﻿date,value,memo") and len(text.strip().splitlines()) == 252

    r = client.get("/api/data/export", params={"format": "json"})
    assert r.status_code == 200 and len(r.json()) == 251
    assert client.get("/api/data/export", params={"format": "xml"}).status_code == 422
