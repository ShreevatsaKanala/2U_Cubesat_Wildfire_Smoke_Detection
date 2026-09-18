"""Downlink tests for CubeSat Digital Twin."""
import pytest
import random
from datetime import datetime, timezone


# ── Downlink Model Tests ────────────────────────────────────────────────

class TestDownlinkItem:
    def _item(self, size=1024, transmitted=0, status="queued"):
        from app.models.downlink import DownlinkItem, TransferState
        item = DownlinkItem(
            observation_id="OBS-001", priority="HIGH",
            image_size_bytes=size, bytes_transmitted=transmitted,
            status=status,
        )
        return item

    def test_progress_pct(self):
        from app.models.downlink import DownlinkItem
        item = self._item(size=1000, transmitted=500)
        assert item.progress_pct == 50.0

    def test_progress_pct_zero_size(self):
        from app.models.downlink import DownlinkItem
        item = self._item(size=0)
        assert item.progress_pct == 0.0

    def test_bytes_remaining(self):
        from app.models.downlink import DownlinkItem
        item = self._item(size=1000, transmitted=300)
        assert item.bytes_remaining == 700

    def test_bytes_remaining_complete(self):
        from app.models.downlink import DownlinkItem
        item = self._item(size=1000, transmitted=1000)
        assert item.bytes_remaining == 0

    def test_eta_seconds(self):
        from app.models.downlink import DownlinkItem, TransferState
        item = self._item(size=10000, transmitted=0, status=TransferState.TRANSFERRING)
        item._current_rate_bytes_s = 1000.0
        assert item.eta_seconds == 10.0

    def test_eta_seconds_not_transferring(self):
        from app.models.downlink import DownlinkItem
        item = self._item(size=10000, status="queued")
        assert item.eta_seconds == 0.0

    def test_eta_seconds_zero_rate(self):
        from app.models.downlink import DownlinkItem, TransferState
        item = self._item(size=10000, status=TransferState.TRANSFERRING)
        item._current_rate_bytes_s = 0.0
        assert item.eta_seconds == 0.0


# ── DownlinkQueue Tests ────────────────────────────────────────────────

class TestDownlinkQueue:
    def test_enqueue_priority_order(self):
        from app.models.downlink import DownlinkQueue, DownlinkItem
        q = DownlinkQueue()
        q.enqueue(DownlinkItem(observation_id="low", priority="LOW", image_size_bytes=100))
        q.enqueue(DownlinkItem(observation_id="crit", priority="CRITICAL", image_size_bytes=100))
        q.enqueue(DownlinkItem(observation_id="high", priority="HIGH", image_size_bytes=100))
        assert q.items[0].priority == "CRITICAL"
        assert q.items[1].priority == "HIGH"
        assert q.items[2].priority == "LOW"

    def test_get_queue_size(self):
        from app.models.downlink import DownlinkQueue, DownlinkItem
        q = DownlinkQueue()
        q.enqueue(DownlinkItem(observation_id="o1", image_size_bytes=100))
        assert q.get_queue_size() == 1

    def test_get_pending_items(self):
        from app.models.downlink import DownlinkQueue, DownlinkItem
        q = DownlinkQueue()
        q.enqueue(DownlinkItem(observation_id="o1", image_size_bytes=100))
        assert len(q.get_pending_items()) == 1

    def test_get_transferring_items(self):
        from app.models.downlink import DownlinkQueue, DownlinkItem, TransferState
        q = DownlinkQueue()
        q.enqueue(DownlinkItem(observation_id="o1", image_size_bytes=100, status=TransferState.TRANSFERRING))
        assert len(q.get_transferring_items()) == 1

    def test_get_completed_items(self):
        from app.models.downlink import DownlinkQueue, DownlinkItem, TransferState
        q = DownlinkQueue()
        q.enqueue(DownlinkItem(observation_id="o1", image_size_bytes=100, status=TransferState.TRANSMITTED))
        assert len(q.get_completed_items()) == 1

    def test_get_active_items(self):
        from app.models.downlink import DownlinkQueue, DownlinkItem, TransferState
        q = DownlinkQueue()
        q.enqueue(DownlinkItem(observation_id="o1", image_size_bytes=100, status=TransferState.TRANSFERRING))
        q.enqueue(DownlinkItem(observation_id="o2", image_size_bytes=100, status=TransferState.PAUSED))
        q.enqueue(DownlinkItem(observation_id="o3", image_size_bytes=100, status=TransferState.QUEUED))
        assert len(q.get_active_items()) == 2

    def test_overall_progress(self):
        from app.models.downlink import DownlinkQueue, DownlinkItem, TransferState
        q = DownlinkQueue()
        q.enqueue(DownlinkItem(observation_id="o1", image_size_bytes=1000, bytes_transmitted=500, status=TransferState.TRANSFERRING))
        q.enqueue(DownlinkItem(observation_id="o2", image_size_bytes=1000, status=TransferState.QUEUED))
        q.enqueue(DownlinkItem(observation_id="o3", image_size_bytes=1000, bytes_transmitted=1000, status=TransferState.TRANSMITTED))
        p = q.get_overall_progress()
        assert p["active_count"] == 1
        assert p["queued_count"] == 1
        assert p["completed_count"] == 1
        assert p["overall_progress_pct"] > 0


# ── DownlinkService Elevation-like Tests ────────────────────────────────

class TestDownlinkServiceElevation:
    def test_comm_loss_pause(self):
        from app.services.downlink import DownlinkService
        from app.models.downlink import TransferState
        from app.models.observation import Observation
        svc = DownlinkService(rate_bytes_s=1.0)
        obs = Observation(
            observation_id="OBS-ELEV", timestamp=datetime.now(timezone.utc),
            spacecraft_id="CSAT-001", latitude=35.0, longitude=-120.0, altitude_km=500.0,
            image_path="test.jpg", image_width=1920, image_height=1080,
            capture_mode="auto", camera_status="nominal",
        )
        item = svc.queue_observation(obs)
        svc.start_transfer(item, "GS-001", datetime.now(timezone.utc))
        status = svc.update_transfer(item, 0.1, datetime.now(timezone.utc), comm_loss=True)
        assert status == TransferState.PAUSED

    def test_priority_ascending_order(self):
        from app.services.downlink import DownlinkService
        from app.models.observation import Observation
        svc = DownlinkService()
        for p in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]:
            obs = Observation(
                observation_id=f"OBS-{p}", timestamp=datetime.now(timezone.utc),
                spacecraft_id="CSAT-001", latitude=35.0, longitude=-120.0, altitude_km=500.0,
                image_path="test.jpg", image_width=1920, image_height=1080,
                capture_mode="auto", camera_status="nominal", priority=p,
            )
            svc.queue_observation(obs)
        items = svc.queue.items
        priorities = [i.priority for i in items]
        assert priorities == ["CRITICAL", "HIGH", "MEDIUM", "LOW"]

    def test_multi_step_transfer(self):
        from app.services.downlink import DownlinkService
        from app.models.downlink import TransferState
        from app.models.observation import Observation
        svc = DownlinkService(rate_bytes_s=100.0, config={"band": "ka_band"})
        obs = Observation(
            observation_id="OBS-MULTI", timestamp=datetime.now(timezone.utc),
            spacecraft_id="CSAT-001", latitude=35.0, longitude=-120.0, altitude_km=500.0,
            image_path="test.jpg", image_width=1920, image_height=1080,
            capture_mode="auto", camera_status="nominal",
        )
        item = svc.queue_observation(obs)
        svc.start_transfer(item, "GS", datetime.now(timezone.utc))

        # Partial progress
        svc.update_transfer(item, 0.5, datetime.now(timezone.utc))
        assert item.bytes_transmitted > 0
        assert item.bytes_transmitted < item.image_size_bytes

        # Continue until complete
        for _ in range(100):
            if item.status == TransferState.TRANSMITTED:
                break
            svc.update_transfer(item, 1.0, datetime.now(timezone.utc))
        assert item.status == TransferState.TRANSMITTED

    def test_multi_item_queue_summary(self):
        from app.services.downlink import DownlinkService
        from app.models.observation import Observation
        svc = DownlinkService()
        for i in range(5):
            obs = Observation(
                observation_id=f"OBS-{i}", timestamp=datetime.now(timezone.utc),
                spacecraft_id="CSAT-001", latitude=35.0, longitude=-120.0, altitude_km=500.0,
                image_path="test.jpg", image_width=1920, image_height=1080,
                capture_mode="auto", camera_status="nominal",
            )
            svc.queue_observation(obs)
        summary = svc.get_queue_summary()
        assert len(summary["queued"]) == 5
