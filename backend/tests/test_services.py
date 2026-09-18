"""Tests for new Phase 5U-V services."""
import pytest
import time
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timezone, timedelta


# ── TLE Service ─────────────────────────────────────────────────────────

class TestTLEService:
    def test_init_default(self):
        from app.services.tle_service import TLEService
        svc = TLEService()
        assert svc.is_valid is False
        assert svc.tle_line1 is None

    def test_init_custom_norad(self):
        from app.services.tle_service import TLEService
        svc = TLEService(norad_id="25544")
        assert svc._norad_id == "25544"

    def test_load_direct_valid(self):
        from app.services.tle_service import TLEService
        svc = TLEService()
        l1 = "1 25544U 98067A   24100.50000000  .00016717  00000-0  10270-3 0  9994"
        l2 = "2 25544  51.6400 200.0000 0007000  50.0000 310.0000 15.49000000400000"
        with patch("app.services.tle_service.EPOCH_MAX_AGE_DAYS", 1000):
            svc.load_direct(l1, l2, "TEST SAT")
        assert svc.is_valid is True
        assert svc.tle_line1 == l1

    def test_load_direct_invalid_format(self):
        from app.services.tle_service import TLEService
        svc = TLEService()
        with patch("app.services.tle_service.EPOCH_MAX_AGE_DAYS", 1000):
            svc.load_direct("INVALID", "ALSO_INVALID", "BAD")
        assert svc.is_valid is False

    def test_load_direct_short_lines(self):
        from app.services.tle_service import TLEService
        svc = TLEService()
        with patch("app.services.tle_service.EPOCH_MAX_AGE_DAYS", 1000):
            svc.load_direct("1 SHORT", "2 SHORT", "SHORT")
        assert svc.is_valid is False

    def test_parse_epoch_valid(self):
        from app.services.tle_service import TLEService
        svc = TLEService()
        l1 = "1 25544U 98067A   24100.50000000  .00016717  00000-0  10270-3 0  9994"
        epoch = svc._parse_epoch(l1)
        assert epoch is not None
        assert epoch.year == 2024

    def test_parse_epoch_invalid(self):
        from app.services.tle_service import TLEService
        svc = TLEService()
        assert svc._parse_epoch("1 BAD") is None

    def test_validate_tle_valid(self):
        from app.services.tle_service import TLEService
        svc = TLEService()
        l1 = "1 25544U 98067A   24100.50000000  .00016717  00000-0  10270-3 0  9994"
        l2 = "2 25544  51.6400 200.0000 0007000  50.0000 310.0000 15.49000000400000"
        assert svc._validate_tle(l1, l2, datetime.now(timezone.utc) - timedelta(days=30)) is True

    def test_validate_tle_stale(self):
        from app.services.tle_service import TLEService
        svc = TLEService()
        l1 = "1 25544U 98067A   24100.50000000  .00016717  00000-0  10270-3 0  9994"
        l2 = "2 25544  51.6400 200.0000 0007000  50.0000 310.0000 15.49000000400000"
        assert svc._validate_tle(l1, l2, datetime(2020, 1, 1, tzinfo=timezone.utc)) is False

    def test_validate_tle_empty(self):
        from app.services.tle_service import TLEService
        assert TLEService()._validate_tle("", "", None) is False

    def test_get_status(self):
        from app.services.tle_service import TLEService
        svc = TLEService()
        status = svc.get_status()
        assert "norad_id" in status and "valid" in status

    def test_initialize_fallback(self):
        from app.services import tle_service as tle_mod
        from app.services.tle_service import TLEService, CACHE_DIR
        norad = "99999"
        cache_file = CACHE_DIR / f"tle_{norad}.json"
        if cache_file.exists():
            cache_file.unlink()
        svc = TLEService(norad_id=norad)
        old_val = tle_mod.EPOCH_MAX_AGE_DAYS
        tle_mod.EPOCH_MAX_AGE_DAYS = 1000
        try:
            with patch.object(tle_mod.TLEService, '_fetch_from_celestrak', return_value=None):
                l1, l2 = svc.initialize()
        finally:
            tle_mod.EPOCH_MAX_AGE_DAYS = old_val
        assert l1 is not None and svc.is_valid is True

    def test_parse_tle_text_valid(self):
        from app.services.tle_service import TLEService
        text = "ISS (ZARYA)\n1 25544U 98067A   24100.50000000  .00016717  00000-0  10270-3 0  9994\n2 25544  51.6400 200.0000 0007000  50.0000 310.0000 15.49000000400000"
        result = TLEService._parse_tle_text(text, "25544")
        assert result is not None and result["name"] == "ISS (ZARYA)"

    def test_parse_tle_text_too_few_lines(self):
        from app.services.tle_service import TLEService
        assert TLEService._parse_tle_text("l1\nl2", "25544") is None

    def test_refresh_with_mock(self):
        from app.services.tle_service import TLEService
        svc = TLEService()
        l1 = "1 25544U 98067A   24100.50000000  .00016717  00000-0  10270-3 0  9994"
        l2 = "2 25544  51.6400 200.0000 0007000  50.0000 310.0000 15.49000000400000"
        with patch("app.services.tle_service.EPOCH_MAX_AGE_DAYS", 1000), \
             patch.object(TLEService, '_fetch_from_celestrak', return_value={"name": "T", "line1": l1, "line2": l2}):
            status = svc.refresh()
        assert status["valid"] is True


# ── Downlink Service ────────────────────────────────────────────────────

class TestDownlinkService:
    def _make_obs(self, obs_id="OBS-001", priority="HIGH"):
        from app.models.observation import Observation
        return Observation(
            observation_id=obs_id, timestamp=datetime.now(timezone.utc),
            spacecraft_id="CSAT-001", latitude=35.0, longitude=-120.0,
            altitude_km=500.0, image_path="test.jpg", image_width=1920,
            image_height=1080, capture_mode="auto", camera_status="nominal",
            priority=priority,
        )

    def test_init(self):
        from app.services.downlink import DownlinkService
        svc = DownlinkService(rate_bytes_s=2048.0)
        s = svc.get_status()
        assert s["queue_size"] == 0

    def test_queue_observation(self):
        from app.services.downlink import DownlinkService
        item = DownlinkService().queue_observation(self._make_obs())
        assert item.observation_id == "OBS-001" and item.image_size_bytes > 0

    def test_start_transfer(self):
        from app.services.downlink import DownlinkService
        from app.models.downlink import TransferState
        svc = DownlinkService()
        item = svc.queue_observation(self._make_obs())
        assert svc.start_transfer(item, "GS-001", datetime.now(timezone.utc)) is True
        assert item.status == TransferState.TRANSFERRING

    def test_start_transfer_not_queued(self):
        from app.services.downlink import DownlinkService
        from app.models.downlink import TransferState, DownlinkItem
        item = DownlinkItem(observation_id="OBS", status=TransferState.TRANSMITTED, image_size_bytes=1024)
        assert DownlinkService().start_transfer(item, "GS", datetime.now(timezone.utc)) is False

    def test_update_transfer_complete(self):
        from app.services.downlink import DownlinkService
        from app.models.downlink import TransferState
        svc = DownlinkService(rate_bytes_s=1e9, config={"band": "ka_band"})
        item = svc.queue_observation(self._make_obs())
        svc.start_transfer(item, "GS", datetime.now(timezone.utc))
        assert svc.update_transfer(item, 10.0, datetime.now(timezone.utc)) == TransferState.TRANSMITTED

    def test_update_transfer_paused_no_station(self):
        from app.services.downlink import DownlinkService
        from app.models.downlink import TransferState
        svc = DownlinkService(rate_bytes_s=1.0)
        item = svc.queue_observation(self._make_obs())
        svc.start_transfer(item, "GS", datetime.now(timezone.utc))
        assert svc.update_transfer(item, 0.1, datetime.now(timezone.utc), station_visible=False) == TransferState.PAUSED

    def test_update_transfer_paused_low_power(self):
        from app.services.downlink import DownlinkService
        from app.models.downlink import TransferState
        svc = DownlinkService(rate_bytes_s=1.0)
        item = svc.queue_observation(self._make_obs())
        svc.start_transfer(item, "GS", datetime.now(timezone.utc))
        assert svc.update_transfer(item, 0.1, datetime.now(timezone.utc), battery_soc=5.0) == TransferState.PAUSED

    def test_update_transfer_resume(self):
        from app.services.downlink import DownlinkService
        from app.models.downlink import TransferState
        svc = DownlinkService(rate_bytes_s=1.0)
        item = svc.queue_observation(self._make_obs())
        svc.start_transfer(item, "GS", datetime.now(timezone.utc))
        svc.update_transfer(item, 0.1, datetime.now(timezone.utc), station_visible=False)
        assert svc.update_transfer(item, 0.1, datetime.now(timezone.utc), station_visible=True, battery_soc=50.0) == TransferState.TRANSFERRING

    def test_prioritize_item(self):
        from app.services.downlink import DownlinkService
        svc = DownlinkService()
        item = svc.queue_observation(self._make_obs())
        assert svc.prioritize_item("OBS-001", "CRITICAL") is True
        assert item.priority == "CRITICAL"

    def test_prioritize_nonexistent(self):
        from app.services.downlink import DownlinkService
        assert DownlinkService().prioritize_item("NOPE", "HIGH") is False

    def test_get_transfer_status(self):
        from app.services.downlink import DownlinkService
        svc = DownlinkService()
        svc.queue_observation(self._make_obs())
        s = svc.get_transfer_status("OBS-001")
        assert s is not None and s["observation_id"] == "OBS-001"

    def test_set_band(self):
        from app.services.downlink import DownlinkService
        svc = DownlinkService()
        svc.set_band("x_band")
        assert svc.effective_rate_bytes_s == 100 * 1024

    def test_queue_summary(self):
        from app.services.downlink import DownlinkService
        svc = DownlinkService()
        svc.queue_observation(self._make_obs())
        summary = svc.get_queue_summary()
        assert len(summary["queued"]) == 1


# ── Fire Correlation Service ────────────────────────────────────────────

class TestFireCorrelation:
    def _make_obs(self):
        from app.models.observation import Observation
        return Observation(
            observation_id="OBS-CORR", timestamp=datetime.now(timezone.utc),
            spacecraft_id="CSAT-001", latitude=35.0, longitude=-120.0,
            altitude_km=500.0, image_path="test.jpg", image_width=1920,
            image_height=1080, capture_mode="auto", camera_status="nominal",
            smoke_probability=0.8,
        )

    def test_init(self):
        from app.services.fire_correlation import FireCorrelationService
        svc = FireCorrelationService()
        status = svc.get_status()
        assert "weights" in status

    def test_firms_score_empty(self):
        from app.services.fire_correlation import FireCorrelationService
        assert FireCorrelationService()._compute_firms_score([], 50.0) == 0.0

    def test_firms_score_with_detections(self):
        from app.services.fire_correlation import FireCorrelationService
        dets = [
            {"distance_km": 5.0, "confidence_level": 0.8, "frp": 50.0},
            {"distance_km": 20.0, "confidence_level": 0.5, "frp": 20.0},
        ]
        score = FireCorrelationService()._compute_firms_score(dets, 50.0)
        assert 0.0 < score <= 1.0

    def test_firms_score_max_one(self):
        from app.services.fire_correlation import FireCorrelationService
        dets = [{"distance_km": 0.0, "confidence_level": 1.0, "frp": 200.0}] * 20
        assert FireCorrelationService()._compute_firms_score(dets, 50.0) <= 1.0

    def test_weather_score_hot_dry_windy(self):
        from app.services.fire_correlation import FireCorrelationService
        score = FireCorrelationService()._compute_weather_score({"temperature": 40.0, "humidity": 10.0, "wind_speed": 35.0})
        assert score == 1.0

    def test_weather_score_cold_humid(self):
        from app.services.fire_correlation import FireCorrelationService
        score = FireCorrelationService()._compute_weather_score({"temperature": 5.0, "humidity": 80.0, "wind_speed": 2.0})
        assert score == 0.0

    def test_weather_score_none_values(self):
        from app.services.fire_correlation import FireCorrelationService
        assert FireCorrelationService()._compute_weather_score({}) == 0.0

    def test_determine_priority(self):
        from app.services.fire_correlation import FireCorrelationService
        svc = FireCorrelationService()
        assert svc._determine_priority(0.8) == "CRITICAL"
        assert svc._determine_priority(0.6) == "HIGH"
        assert svc._determine_priority(0.4) == "MEDIUM"
        assert svc._determine_priority(0.1) == "LOW"

    @pytest.mark.asyncio
    async def test_correlate_observation_none(self):
        from app.services.fire_correlation import FireCorrelationService
        result = await FireCorrelationService().correlate_observation(None)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_correlate_observation_mock(self):
        from app.services.fire_correlation import FireCorrelationService
        from app.adapters.firms import FIRMSAdapter
        from app.adapters.weather import WeatherAdapter
        firms = MagicMock(spec=FIRMSAdapter)
        firms.get_detections_near_point = AsyncMock(return_value=[
            {"lat": 35.0, "lon": -120.0, "distance_km": 5.0, "confidence": 0.8, "frp": 50.0, "confidence_level": 0.8}
        ])
        weather = MagicMock(spec=WeatherAdapter)
        weather.get_weather = AsyncMock(return_value={"temperature": 35.0, "humidity": 20.0, "wind_speed": 20.0})
        svc = FireCorrelationService(firms_adapter=firms, weather_adapter=weather)
        result = await svc.correlate_observation(self._make_obs())
        assert "fused_fire_probability" in result


# ── Fault Recovery Service ──────────────────────────────────────────────

class TestFaultRecovery:
    def test_init(self):
        from app.services.fault_recovery import FaultRecoveryService
        assert len(FaultRecoveryService().get_status()["records"]) == 6

    def test_camera_recovery_success(self):
        from app.services.fault_recovery import FaultRecoveryService
        evt = FaultRecoveryService().check_camera("error", sim_time_s=200.0)
        assert evt is not None and evt.success is True

    def test_camera_recovery_pending(self):
        from app.services.fault_recovery import FaultRecoveryService
        evt = FaultRecoveryService().check_camera("error", sim_time_s=10.0)
        assert evt is not None and evt.success is False

    def test_camera_no_error(self):
        from app.services.fault_recovery import FaultRecoveryService
        assert FaultRecoveryService().check_camera("nominal", 0.0) is None

    def test_comm_recovery(self):
        from app.services.fault_recovery import FaultRecoveryService
        svc = FaultRecoveryService()
        evt = svc.check_comm("degraded", 0.0)
        assert evt is not None and evt.success is True and svc.comm_backup_active is True

    def test_comm_no_issue(self):
        from app.services.fault_recovery import FaultRecoveryService
        assert FaultRecoveryService().check_comm("nominal", 0.0) is None

    def test_gps_recovery(self):
        from app.services.fault_recovery import FaultRecoveryService
        svc = FaultRecoveryService()
        pos = {"lat": 35.0, "lon": -120.0, "alt": 500.0}
        evt = svc.check_gps("lost", pos, 10.0)
        assert evt is not None and evt.success is True

    def test_gps_propagated_position(self):
        from app.services.fault_recovery import FaultRecoveryService
        svc = FaultRecoveryService()
        pos = {"lat": 35.0, "lon": -120.0, "alt": 500.0}
        svc.check_gps("lost", pos, 10.0)
        assert svc.get_gps_propagated_position() == pos

    def test_battery_recovery(self):
        from app.services.fault_recovery import FaultRecoveryService
        evt = FaultRecoveryService().check_battery(5.0)
        assert evt is not None and evt.success is True

    def test_battery_no_issue(self):
        from app.services.fault_recovery import FaultRecoveryService
        assert FaultRecoveryService().check_battery(50.0) is None

    def test_thermal_recovery(self):
        from app.services.fault_recovery import FaultRecoveryService
        svc = FaultRecoveryService()
        evt = svc.check_thermal(90.0)
        assert evt is not None and evt.success is True and svc.heaters_off is True

    def test_thermal_no_issue(self):
        from app.services.fault_recovery import FaultRecoveryService
        assert FaultRecoveryService().check_thermal(25.0) is None

    def test_obc_recovery(self):
        from app.services.fault_recovery import FaultRecoveryService
        svc = FaultRecoveryService()
        svc._last_heartbeat_time = time.time() - 100
        evt = svc.check_obc()
        assert evt is not None and evt.success is True

    def test_obc_no_issue(self):
        from app.services.fault_recovery import FaultRecoveryService
        svc = FaultRecoveryService()
        svc.update_heartbeat()
        assert svc.check_obc() is None

    def test_manual_trigger(self):
        from app.services.fault_recovery import FaultRecoveryService, RecoveryAction
        evt = FaultRecoveryService().manual_trigger(RecoveryAction.CAMERA_REBOOT)
        assert evt.action == RecoveryAction.CAMERA_REBOOT

    def test_reset(self):
        from app.services.fault_recovery import FaultRecoveryService
        svc = FaultRecoveryService()
        svc.check_comm("degraded", 0.0)
        svc.reset()
        assert svc.get_status()["comm_backup_active"] is False

    def test_max_retries_exceeded(self):
        from app.services.fault_recovery import FaultRecoveryService
        svc = FaultRecoveryService(config=MagicMock(
            camera_max_retries=1, camera_cooldown_s=999,
            comm_max_retries=1, comm_cooldown_s=999,
            gps_max_retries=1, gps_cooldown_s=999,
            thermal_max_retries=1, thermal_cooldown_s=999,
            obc_max_retries=1, obc_cooldown_s=999,
            battery_soc_shed_threshold=10.0, obc_heartbeat_timeout_s=30.0,
        ))
        svc.check_battery(5.0)
        assert svc.check_battery(5.0) is None


# ── EPS Model ───────────────────────────────────────────────────────────

class TestEPSModel:
    def test_init(self):
        from app.services.eps_model import EPSModel
        s = EPSModel().get_status()
        assert s["battery"]["soc_percent"] == 85.0

    def test_solar_generation_sunlit(self):
        from app.services.eps_model import EPSModel
        gen = EPSModel().update_solar({"sun_vector": [1, 0, 0], "position_km": [0, 0, 6871]}, 0.0)
        assert gen >= 0.0

    def test_solar_generation_eclipse(self):
        from app.services.eps_model import EPSModel
        gen = EPSModel().update_solar({"sun_vector": [-1, 0, 0], "position_km": [0, 0, 6871]}, 0.0)
        assert gen == 0.0

    def test_update_consumption_idle(self):
        from app.services.eps_model import EPSModel
        assert EPSModel().update_consumption(mission_mode="IDLE") > 0

    def test_update_consumption_capturing(self):
        from app.services.eps_model import EPSModel
        assert EPSModel().update_consumption(mission_mode="CAPTURING", camera_active=True) > 0

    def test_battery_charging(self):
        from app.services.eps_model import EPSModel
        eps = EPSModel()
        eps.state.solar_panel.generation_w = 2.0
        eps.state.total_consumption_w = 1.0
        assert eps.update_battery(3600.0).soc_percent >= 85.0

    def test_battery_discharging(self):
        from app.services.eps_model import EPSModel
        eps = EPSModel()
        eps.state.solar_panel.generation_w = 0.0
        eps.state.total_consumption_w = 3.0
        assert eps.update_battery(3600.0).soc_percent <= 85.0

    def test_battery_voltage(self):
        from app.services.eps_model import EPSModel
        eps = EPSModel()
        eps.state.solar_panel.generation_w = 0.0
        eps.state.total_consumption_w = 3.0
        bat = eps.update_battery(3600.0)
        assert 0.0 < bat.voltage_v < 12.0

    def test_effective_capacity_temp(self):
        from app.services.eps_model import BatteryState
        assert BatteryState(temperature_c=50.0).effective_capacity_wh() < 40.0

    def test_load_shedding(self):
        from app.services.eps_model import EPSModel
        eps = EPSModel()
        eps.update_consumption(mission_mode="DOWNLINKING", comms_active=True)
        assert len(eps.shed_loads(target_consumption_w=0.5)) > 0

    def test_restore_loads(self):
        from app.services.eps_model import EPSModel
        eps = EPSModel()
        eps.shed_loads(target_consumption_w=0.5)
        eps.restore_loads()
        assert len(eps.state.shed_loads) == 0

    def test_budget_events(self):
        from app.services.eps_model import EPSModel
        eps = EPSModel()
        eps.state.battery.soc_percent = 5.0
        eps._check_budget_events()
        assert "EMERGENCY_POWER" in eps.state.budget_events

    def test_reset(self):
        from app.services.eps_model import EPSModel
        eps = EPSModel()
        eps.reset()
        assert eps.state.battery.soc_percent == 85.0

    def test_subsystem_power(self):
        from app.services.eps_model import SubsystemPower
        assert SubsystemPower(name="t", nominal_w=5.0, duty_cycle=0.5).current_w == 2.5
        assert SubsystemPower(name="t", nominal_w=5.0, is_shed=True).current_w == 0.0


# ── Thermal Model ───────────────────────────────────────────────────────

class TestThermalModel:
    def test_init(self):
        from app.services.thermal_model import ThermalModel
        temps = ThermalModel().get_node_temperatures()
        assert "obc" in temps and temps["obc"] == 25.0

    def test_update_sunlight(self):
        from app.services.thermal_model import ThermalModel
        nodes = ThermalModel().update(dt_seconds=1.0, orbital_state={"in_sunlight": True, "sun_angle_deg": 30.0})
        assert "obc" in nodes

    def test_update_eclipse(self):
        from app.services.thermal_model import ThermalModel
        nodes = ThermalModel().update(dt_seconds=1.0, orbital_state={"in_sunlight": False})
        assert "obc" in nodes

    def test_heater_activation(self):
        from app.services.thermal_model import ThermalModel, ThermalNodeConfig
        configs = {
            name: ThermalNodeConfig(name=name, mass_kg=0.15, specific_heat_j_kg_k=896,
                                    area_m2=0.008, emissivity=0.9, min_temp_c=20, max_temp_c=70)
            for name in ("obc", "battery", "camera", "comms", "structure")
        }
        tm = ThermalModel(node_configs=configs)
        tm.nodes["obc"].temperature_c = 16.0
        tm.update(dt_seconds=1.0)
        assert tm.nodes["obc"].heater_on is True

    def test_thermal_mode(self):
        from app.services.thermal_model import ThermalModel
        tm = ThermalModel()
        tm.update(dt_seconds=1.0)
        assert tm.get_overall_mode().value in ("NOMINAL", "WARMING", "COOLING", "CRITICAL_HOT", "CRITICAL_COLD")

    def test_get_trends(self):
        from app.services.thermal_model import ThermalModel
        ThermalModel().update(dt_seconds=1.0)
        trends = ThermalModel().get_trends()
        assert "obc" in trends

    def test_predict_time_to_limit(self):
        from app.services.thermal_model import ThermalModel
        tm = ThermalModel()
        tm.nodes["obc"].temperature_c = 50.0
        tm.nodes["obc"].temp_rate_per_s = 0.5
        assert tm.predict_time_to_limit("obc") is not None

    def test_reset(self):
        from app.services.thermal_model import ThermalModel
        tm = ThermalModel()
        tm.update(dt_seconds=5.0)
        tm.reset()
        assert tm.get_node_temperatures()["obc"] == 25.0


# ── Resource Manager ────────────────────────────────────────────────────

class TestResourceManager:
    def test_bounded_list(self):
        from app.core.resource_manager import BoundedList
        bl = BoundedList(max_size=3)
        for i in range(10):
            bl.append(i)
        assert len(bl) == 3 and bl.dropped_count > 0

    def test_bounded_list_recent(self):
        from app.core.resource_manager import BoundedList
        bl = BoundedList(max_size=5)
        for i in range(5):
            bl.append(i)
        assert bl.get_recent(3) == [4, 3, 2]

    def test_bounded_list_bool(self):
        from app.core.resource_manager import BoundedList
        bl = BoundedList(max_size=5)
        assert not bl
        bl.append(1)
        assert bl

    def test_bounded_dict(self):
        from app.core.resource_manager import BoundedDict
        bd = BoundedDict(max_size=3)
        bd.put("k1", "v1")
        assert bd.get("k1") == "v1" and bd.get("miss") is None

    def test_bounded_dict_eviction(self):
        from app.core.resource_manager import BoundedDict
        bd = BoundedDict(max_size=3)
        for i in range(10):
            bd.put(f"k{i}", f"v{i}")
        assert len(bd) == 3 and bd.dropped_count > 0

    def test_bounded_dict_contains(self):
        from app.core.resource_manager import BoundedDict
        bd = BoundedDict(max_size=3)
        bd.put("a", 1)
        assert "a" in bd and "b" not in bd

    def test_ttl_cache(self):
        from app.core.resource_manager import TTLCache
        c = TTLCache(max_age_minutes=60)
        c.put("k", "v")
        assert c.get("k") == "v"

    def test_ttl_cache_expiry(self):
        from app.core.resource_manager import TTLCache
        from datetime import timedelta
        c = TTLCache(max_age_minutes=0.0001)
        c.put("k", "v")
        c._entries["k"] = (c._entries["k"][0], datetime.now(timezone.utc) - timedelta(hours=1))
        assert c.get("k") is None

    def test_ttl_cache_cleanup(self):
        from app.core.resource_manager import TTLCache
        from datetime import timedelta
        c = TTLCache(max_age_minutes=0.0001)
        c.put("k", "v")
        c._entries["k"] = (c._entries["k"][0], datetime.now(timezone.utc) - timedelta(hours=1))
        assert c.cleanup_expired() == 1

    def test_resource_monitor_counter(self):
        from app.core.resource_manager import ResourceMonitor
        rm = ResourceMonitor()
        rm.increment_counter("t", 5)
        rm.decrement_counter("t", 2)
        stats = rm.get_stats()
        assert stats["counters"]["t"] == 3

    def test_degradation_state(self):
        from app.core.resource_manager import DegradationState
        ds = DegradationState(memory_warning_mb=100, memory_critical_mb=200)
        ds.update(50.0)
        assert ds.is_normal
        ds.update(150.0)
        assert ds.is_warning
        ds.update(250.0)
        assert ds.is_critical

    def test_cleanup_scheduler_start_stop(self):
        from app.core.resource_manager import CleanupScheduler
        cs = CleanupScheduler(interval_seconds=1)
        cs.start()
        assert cs._running is True
        cs.stop()
        assert cs._running is False
