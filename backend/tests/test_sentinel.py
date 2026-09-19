"""Tests for Copernicus Sentinel integration — all external calls mocked."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.sentinel.schemas import SentinelScene, SentinelObservationResult, SentinelStatus
from datetime import datetime, timezone


def _make_scene(scene_id="S2A_20260919T065231_N0500_R123_T33UXP", cloud_cover=3.7):
    return SentinelScene(
        scene_id=scene_id,
        product_id=f"PROD_{scene_id}",
        datetime=datetime(2026, 9, 19, 6, 52, 31, tzinfo=timezone.utc),
        cloud_cover=cloud_cover,
        bbox=[78.35, 14.15, 78.65, 14.45],
        geometry={"type": "Polygon", "coordinates": []},
        data_coverage=95.0,
        platform="sentinel-2",
    )


# ── Schema tests ──────────────────────────────────────────────────────

def test_sentinel_scene_schema():
    scene = _make_scene()
    assert scene.scene_id.startswith("S2A_")
    assert scene.cloud_cover == 3.7
    assert scene.platform == "sentinel-2"


def test_sentinel_observation_result_schema():
    result = SentinelObservationResult(
        observation_id="OBS-0001",
        scene_id="S2A_TEST",
        acquisition_time="2026-09-19T06:52:31Z",
        cloud_cover=3.7,
        aoi=[78.35, 14.15, 78.65, 14.45],
        true_color_url="base64data",
        ndvi_url="base64data",
        false_color_url="base64data",
        metadata={"product": "S2MSI2A"},
        available=True,
    )
    d = result.model_dump()
    assert d["available"] is True
    assert d["observation_id"] == "OBS-0001"


def test_sentinel_status_schema():
    status = SentinelStatus(
        enabled=True,
        authenticated=True,
        service="Copernicus Sentinel-2 L2A",
        last_request=None,
        last_success=None,
        cache_hits=0,
        cache_misses=0,
        last_error=None,
        current_scene=None,
    )
    d = status.model_dump()
    assert d["enabled"] is True
    assert "client_secret" not in d


# ── Cache tests ───────────────────────────────────────────────────────

def test_cache_set_get_metadata():
    from app.sentinel.cache import SentinelCache
    cache = SentinelCache()
    key = ("meta", (78.35, 14.15, 78.65, 14.45), "2026-09-19")
    cache.set_metadata(key, {"scene_id": "TEST_SCENE", "cloud_cover": 5.0})
    result = cache.get_metadata(key)
    assert result is not None
    assert result["scene_id"] == "TEST_SCENE"


def test_cache_miss():
    from app.sentinel.cache import SentinelCache
    cache = SentinelCache()
    result = cache.get_metadata(("meta", (0, 0, 1, 1), "2026-01-01"))
    assert result is None
    stats = cache.get_stats()
    assert stats["misses"] >= 1


def test_cache_image():
    from app.sentinel.cache import SentinelCache
    cache = SentinelCache()
    key = ("img", "true_color", (0, 0, 1, 1), "SCENE_1")
    cache.set_image(key, b"\x89PNG\r\n")
    result = cache.get_image(key)
    assert result == b"\x89PNG\r\n"


# ── Auth tests ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_auth_success():
    from app.sentinel.auth import SentinelAuth
    auth = SentinelAuth()

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "access_token": "test_token_123",
        "expires_in": 600,
    }
    mock_response.raise_for_status = MagicMock()

    mock_client_instance = AsyncMock()
    mock_client_instance.post.return_value = mock_response
    mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
    mock_client_instance.__aexit__ = AsyncMock(return_value=False)

    with patch("app.sentinel.auth.settings") as mock_settings:
        mock_settings.SH_CLIENT_ID = "test_id"
        mock_settings.SH_CLIENT_SECRET = "test_secret"

        with patch("app.sentinel.auth.httpx.AsyncClient", return_value=mock_client_instance):
            token = await auth.get_token()
            assert token == "test_token_123"
            assert auth.is_authenticated()


@pytest.mark.asyncio
async def test_auth_failure_empty_credentials():
    from app.sentinel.auth import SentinelAuth
    auth = SentinelAuth()

    with patch("app.sentinel.auth.settings") as mock_settings:
        mock_settings.SH_CLIENT_ID = ""
        mock_settings.SH_CLIENT_SECRET = ""

        token = await auth.get_token()
        assert token == ""
        assert not auth.is_authenticated()


# ── Catalog tests ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_catalog_search_success():
    from app.sentinel.catalog import SentinelCatalog
    catalog = SentinelCatalog()

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "features": [
            {
                "id": "S2A_20260919T065231_N0500_R123_T33UXP",
                "properties": {
                    "datetime": "2026-09-19T06:52:31Z",
                    "eo:cloud_cover": 3.7,
                    "platform": "sentinel-2",
                    "s2:datacoverage": 95.0,
                },
                "geometry": {"type": "Polygon", "coordinates": []},
                "bbox": [78.35, 14.15, 78.65, 14.45],
                "assets": {},
            }
        ]
    }
    mock_response.raise_for_status = MagicMock()

    mock_client_instance = AsyncMock()
    mock_client_instance.post.return_value = mock_response
    mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
    mock_client_instance.__aexit__ = AsyncMock(return_value=False)

    with patch("app.sentinel.catalog.httpx.AsyncClient", return_value=mock_client_instance):
        scenes = await catalog.search_scenes(
            bbox=[78.35, 14.15, 78.65, 14.45],
            datetime_range="2026-09-19T00:00:00Z/2026-09-19T23:59:59Z",
            max_cloud_cover=50.0,
            max_results=5,
        )
        assert len(scenes) == 1
        assert scenes[0].cloud_cover == 3.7


@pytest.mark.asyncio
async def test_catalog_search_empty():
    from app.sentinel.catalog import SentinelCatalog
    catalog = SentinelCatalog()

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"features": []}
    mock_response.raise_for_status = MagicMock()

    mock_client_instance = AsyncMock()
    mock_client_instance.post.return_value = mock_response
    mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
    mock_client_instance.__aexit__ = AsyncMock(return_value=False)

    with patch("app.sentinel.catalog.httpx.AsyncClient", return_value=mock_client_instance):
        scenes = await catalog.search_scenes(
            bbox=[0, 0, 1, 1],
            datetime_range="2020-01-01T00:00:00Z/2020-01-01T23:59:59Z",
            max_cloud_cover=10.0,
            max_results=5,
        )
        assert len(scenes) == 0


@pytest.mark.asyncio
async def test_catalog_search_error():
    from app.sentinel.catalog import SentinelCatalog
    catalog = SentinelCatalog()

    mock_client_instance = AsyncMock()
    mock_client_instance.post.side_effect = Exception("Network error")
    mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
    mock_client_instance.__aexit__ = AsyncMock(return_value=False)

    with patch("app.sentinel.catalog.httpx.AsyncClient", return_value=mock_client_instance):
        scenes = await catalog.search_scenes(
            bbox=[0, 0, 1, 1],
            datetime_range="2026-01-01T00:00:00Z/2026-01-01T23:59:59Z",
            max_cloud_cover=50.0,
            max_results=5,
        )
        assert len(scenes) == 0


# ── Process API tests ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_process_true_color():
    from app.sentinel.process import SentinelProcess
    process = SentinelProcess()

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b"\x89PNG_true_color_data"
    mock_response.raise_for_status = MagicMock()

    mock_client_instance = AsyncMock()
    mock_client_instance.post.return_value = mock_response
    mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
    mock_client_instance.__aexit__ = AsyncMock(return_value=False)

    with patch("app.sentinel.process.httpx.AsyncClient", return_value=mock_client_instance):
        data = await process.get_true_color("test_token", [78.35, 14.15, 78.65, 14.45])
        assert data == b"\x89PNG_true_color_data"


@pytest.mark.asyncio
async def test_process_ndvi():
    from app.sentinel.process import SentinelProcess
    process = SentinelProcess()

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b"\x89PNG_ndvi_data"
    mock_response.raise_for_status = MagicMock()

    mock_client_instance = AsyncMock()
    mock_client_instance.post.return_value = mock_response
    mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
    mock_client_instance.__aexit__ = AsyncMock(return_value=False)

    with patch("app.sentinel.process.httpx.AsyncClient", return_value=mock_client_instance):
        data = await process.get_ndvi("test_token", [78.35, 14.15, 78.65, 14.45])
        assert data == b"\x89PNG_ndvi_data"


@pytest.mark.asyncio
async def test_process_false_color():
    from app.sentinel.process import SentinelProcess
    process = SentinelProcess()

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b"\x89PNG_false_color_data"
    mock_response.raise_for_status = MagicMock()

    mock_client_instance = AsyncMock()
    mock_client_instance.post.return_value = mock_response
    mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
    mock_client_instance.__aexit__ = AsyncMock(return_value=False)

    with patch("app.sentinel.process.httpx.AsyncClient", return_value=mock_client_instance):
        data = await process.get_false_color("test_token", [78.35, 14.15, 78.65, 14.45])
        assert data == b"\x89PNG_false_color_data"


@pytest.mark.asyncio
async def test_process_error_returns_empty():
    from app.sentinel.process import SentinelProcess
    process = SentinelProcess()

    mock_client_instance = AsyncMock()
    mock_client_instance.post.side_effect = Exception("Timeout")
    mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
    mock_client_instance.__aexit__ = AsyncMock(return_value=False)

    with patch("app.sentinel.process.httpx.AsyncClient", return_value=mock_client_instance):
        data = await process.get_true_color("token", [0, 0, 1, 1])
        assert data == b""


# ── Client integration tests (mocked) ─────────────────────────────────

@pytest.mark.asyncio
async def test_client_observe_success():
    from app.sentinel.client import SentinelClient
    client = SentinelClient()

    mock_scene = _make_scene()

    with patch.object(client._catalog, "search_scenes", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = [mock_scene]

        with patch.object(client._auth, "get_token", new_callable=AsyncMock) as mock_token:
            mock_token.return_value = "test_token"

            with patch.object(client._process, "get_true_color", new_callable=AsyncMock) as mock_tc:
                mock_tc.return_value = b"\x89PNG_tc"

                with patch.object(client._process, "get_ndvi", new_callable=AsyncMock) as mock_ndvi:
                    mock_ndvi.return_value = b"\x89PNG_ndvi"

                    with patch.object(client._process, "get_false_color", new_callable=AsyncMock) as mock_fc:
                        mock_fc.return_value = b"\x89PNG_fc"

                        result = await client.observe(
                            observation_id="OBS-0001",
                            lat=14.31,
                            lon=78.52,
                            datetime_str="2026-09-19",
                        )
                        assert result.available is True
                        assert result.scene_id.startswith("S2A_")
                        assert result.true_color_url != ""


@pytest.mark.asyncio
async def test_client_observe_no_scenes():
    from app.sentinel.client import SentinelClient
    client = SentinelClient()

    with patch.object(client._catalog, "search_scenes", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = []
        result = await client.observe(
            observation_id="OBS-0002",
            lat=0.0,
            lon=0.0,
            datetime_str="2020-01-01",
        )
        assert result.available is False
        assert "No matching" in result.error


@pytest.mark.asyncio
async def test_client_observe_auth_failure():
    from app.sentinel.client import SentinelClient
    client = SentinelClient()

    mock_scene = _make_scene()

    with patch.object(client._catalog, "search_scenes", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = [mock_scene]

        with patch.object(client._auth, "get_token", new_callable=AsyncMock) as mock_token:
            mock_token.return_value = None

            result = await client.observe(
                observation_id="OBS-0003",
                lat=14.31,
                lon=78.52,
                datetime_str="2026-09-19",
            )
            assert result.available is False
            assert "authenticat" in result.error.lower()


def test_client_status():
    from app.sentinel.client import SentinelClient
    client = SentinelClient()
    status = client.get_status()
    assert isinstance(status, SentinelStatus)
    d = status.model_dump()
    assert "enabled" in d
    assert "authenticated" in d
    assert "client_secret" not in d
    assert "access_token" not in d


# ── API endpoint tests ────────────────────────────────────────────────

def test_sentinel_status_endpoint():
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    resp = client.get("/api/v1/sentinel/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "enabled" in data
    assert "authenticated" in data
    assert "client_secret" not in data
    assert "access_token" not in data


def test_sentinel_observe_disabled():
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    resp = client.post("/api/v1/sentinel/observe", json={
        "observation_id": "OBS-TEST",
        "latitude": 14.31,
        "longitude": 78.52,
        "datetime": "2026-09-19",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "observation_id" in data


def test_sentinel_observe_endpoint_structure():
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    resp = client.post("/api/v1/sentinel/observe", json={
        "observation_id": "OBS-0042",
        "latitude": 37.75,
        "longitude": -122.42,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["observation_id"] == "OBS-0042"
    assert "available" in data
