"""Adapter tests for CubeSat Digital Twin Phase 1."""
import pytest
import asyncio
from app.adapters.firms import FIRMSAdapter
from app.adapters.weather import WeatherAdapter
from app.adapters.celes_trak import CelesTrakAdapter
from app.adapters.gibs import GIBSAdapter


def run_async(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_firms_adapter_handles_no_key():
    adapter = FIRMSAdapter(api_key="")
    result = run_async(adapter.get_global_hotspots(days=1))
    assert isinstance(result, list)


def test_weather_adapter():
    adapter = WeatherAdapter()
    result = run_async(adapter.get_weather(35.0, -120.0))
    assert isinstance(result, dict)


def test_air_quality_adapter():
    adapter = WeatherAdapter()
    result = run_async(adapter.get_air_quality(35.0, -120.0))
    assert isinstance(result, dict)


def test_celes_trak_adapter_handles_invalid():
    adapter = CelesTrakAdapter()
    result = run_async(adapter.get_tle("99999"))
    assert isinstance(result, dict)


def test_gibs_adapter():
    adapter = GIBSAdapter()
    url = run_async(adapter.get_wms_url())
    assert isinstance(url, str)
    assert "WMS" in url or "wms" in url.lower()
