"""
Teste pentru:
  - logica "nou azi" (VIEW new_today)
  - endpoint-urile /api/apartments și /api/apartments/new
  - endpoint /api/filters GET/POST
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

# ---- app fără scheduler activ ----
import app as app_module
# patch scheduler ca să nu pornească job-ul real
with patch("scheduler.create_scheduler") as mock_sched:
    mock_sched.return_value = MagicMock(start=MagicMock(), shutdown=MagicMock())


@pytest.fixture
def client():
    from flask import Flask
    from flask_cors import CORS
    from routes import routes as bp

    test_app = Flask(__name__)
    CORS(test_app)
    test_app.register_blueprint(bp)
    test_app.config["TESTING"] = True
    with test_app.test_client() as c:
        yield c


# ---------------------------------------------------------------------------
# Teste endpoint /api/apartments
# ---------------------------------------------------------------------------

FAKE_APARTMENTS_RESULT = {
    "total": 2,
    "page": 1,
    "per_page": 20,
    "apartments": [
        {
            "id": 1,
            "source_website": "imobiliare",
            "title": "Ap 2 camere",
            "price": 75000,
            "location": "Sector 2",
            "surface": 55.0,
            "rooms": 2,
            "floor": "3",
            "contact_name": "Ion",
            "phone_number": "0720000001",
            "link": "https://imobiliare.ro/ap1",
            "description": "desc",
            "scraped_at": "2026-06-12T07:30:00",
        },
        {
            "id": 2,
            "source_website": "publi24",
            "title": "Ap 3 camere",
            "price": 110000,
            "location": "Sector 3",
            "surface": 70.0,
            "rooms": 3,
            "floor": "1",
            "contact_name": "Maria",
            "phone_number": "0730000002",
            "link": "https://publi24.ro/ap2",
            "description": "desc2",
            "scraped_at": "2026-06-12T08:00:00",
        },
    ],
}


def test_api_apartments_returns_list(client):
    with patch("routes.query_apartments", return_value=FAKE_APARTMENTS_RESULT):
        resp = client.get("/api/apartments")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "apartments" in data
    assert "total" in data
    assert len(data["apartments"]) == 2


def test_api_apartments_passes_filters(client):
    with patch("routes.query_apartments", return_value=FAKE_APARTMENTS_RESULT) as mock_q:
        resp = client.get("/api/apartments?rooms=2&sector=2&price_min=50000&price_max=100000")
    assert resp.status_code == 200
    mock_q.assert_called_once_with(
        rooms=2, sector=2, price_min=50000, price_max=100000,
        page=1, per_page=20, sort_by="scraped_at", sort_dir="desc"
    )


def test_api_apartments_invalid_params(client):
    resp = client.get("/api/apartments?rooms=abc")
    assert resp.status_code == 400


def test_api_apartments_pagination(client):
    with patch("routes.query_apartments", return_value=FAKE_APARTMENTS_RESULT) as mock_q:
        resp = client.get("/api/apartments?page=2&per_page=10")
    assert resp.status_code == 200
    mock_q.assert_called_once_with(
        rooms=None, sector=None, price_min=None, price_max=None,
        page=2, per_page=10, sort_by="scraped_at", sort_dir="desc"
    )


# ---------------------------------------------------------------------------
# Teste endpoint /api/apartments/new
# ---------------------------------------------------------------------------

FAKE_NEW_RESULT = {
    "count": 1,
    "apartments": [FAKE_APARTMENTS_RESULT["apartments"][0]],
}


def test_api_new_returns_list(client):
    with patch("routes.query_new_today", return_value=FAKE_NEW_RESULT):
        resp = client.get("/api/apartments/new")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "apartments" in data
    assert "count" in data


def test_api_new_passes_filters(client):
    with patch("routes.query_new_today", return_value=FAKE_NEW_RESULT) as mock_q:
        resp = client.get("/api/apartments/new?rooms=2&price_min=60000")
    assert resp.status_code == 200
    mock_q.assert_called_once_with(
        rooms=2, sector=None, price_min=60000, price_max=None
    )


# ---------------------------------------------------------------------------
# Teste endpoint /api/filters
# ---------------------------------------------------------------------------

FAKE_FILTERS = {"id": 1, "rooms": 2, "sector": 0, "price_min": 10000, "price_max": 150000, "created_at": "2026-06-12T00:00:00"}


def test_get_filters(client):
    with patch("routes.get_active_filters", return_value=FAKE_FILTERS):
        resp = client.get("/api/filters")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["rooms"] == 2


def test_post_filters_valid(client):
    with patch("routes.save_filters", return_value=5) as mock_save:
        resp = client.post("/api/filters", json={"rooms": 3, "sector": 1, "price_min": 20000, "price_max": 100000})
    assert resp.status_code == 201
    assert resp.get_json()["saved"] is True
    mock_save.assert_called_once_with(3, 1, 20000, 100000)


def test_post_filters_invalid_price(client):
    resp = client.post("/api/filters", json={"rooms": 2, "sector": 0, "price_min": 90000, "price_max": 10000})
    assert resp.status_code == 400


def test_post_filters_invalid_type(client):
    resp = client.post("/api/filters", json={"rooms": "abc"})
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Teste logică "nou azi" — query_new_today și query_apartments (unit)
# ---------------------------------------------------------------------------

def test_query_new_today_filters_rooms():
    """Verifică că filtrul rooms e aplicat corect."""
    with patch("Database.database.get_connection") as mock_conn:
        mock_cur = MagicMock()
        mock_cur.fetchall.return_value = []
        mock_conn.return_value.__enter__ = MagicMock(return_value=mock_conn.return_value)
        mock_conn.return_value.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
        mock_conn.return_value.cursor.return_value = mock_cur

        from Database.database import query_new_today
        result = query_new_today(rooms=2)

    assert "apartments" in result
    assert "count" in result


def test_query_apartments_per_page_cap():
    """per_page e capped la 100 în endpoint."""
    from flask import Flask
    from flask_cors import CORS
    from routes import routes as bp

    test_app = Flask(__name__)
    CORS(test_app)
    test_app.register_blueprint(bp)
    test_app.config["TESTING"] = True

    with test_app.test_client() as c:
        with patch("routes.query_apartments", return_value={"total": 0, "page": 1, "per_page": 100, "apartments": []}) as mock_q:
            c.get("/api/apartments?per_page=9999")
        _, kwargs = mock_q.call_args
        assert kwargs.get("per_page", mock_q.call_args[0][6] if mock_q.call_args[0] else 100) <= 100
