#!/usr/bin/env python3
"""
End-to-end smoke test for the 2U CubeSat Wildfire Smoke Detection Digital Twin.

Run backend first:
    cd backend
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

Then from project root:
    python scripts/test_system.py

Optional:
    python scripts/test_system.py --base-url http://localhost:8000 --duration 45
"""

from __future__ import annotations

import argparse
import sys
import time
from typing import Any

import requests


DEFAULT_BASE_URL = "http://localhost:8000"
DEFAULT_DURATION = 45

PASS = "\u2705"
FAIL = "\u274c"
WARN = "\u26a0\ufe0f"


class TestRunner:
    def __init__(self, base_url: str, timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.passed = 0
        self.failed = 0
        self.warnings = 0

    def url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def check(
        self,
        name: str,
        method: str,
        path: str,
        expected_status: tuple[int, ...] = (200,),
        **kwargs: Any,
    ) -> requests.Response | None:
        try:
            response = requests.request(
                method,
                self.url(path),
                timeout=self.timeout,
                **kwargs,
            )

            if response.status_code in expected_status:
                print(f"{PASS} {name} [{response.status_code}]")
                self.passed += 1
                return response

            print(
                f"{FAIL} {name} "
                f"[expected {expected_status}, got {response.status_code}]"
            )
            print(f"    {response.text[:500]}")
            self.failed += 1
            return response

        except requests.RequestException as exc:
            print(f"{FAIL} {name}")
            print(f"    {exc}")
            self.failed += 1
            return None

    def soft_check(
        self,
        name: str,
        method: str,
        path: str,
        expected_status: tuple[int, ...] = (200,),
        **kwargs: Any,
    ) -> requests.Response | None:
        """
        Non-critical test. A missing optional integration produces a warning
        rather than failing the whole test run.
        """
        try:
            response = requests.request(
                method,
                self.url(path),
                timeout=self.timeout,
                **kwargs,
            )

            if response.status_code in expected_status:
                print(f"{PASS} {name} [{response.status_code}]")
                self.passed += 1
                return response

            print(
                f"{WARN} {name} "
                f"[optional, got {response.status_code}]"
            )
            self.warnings += 1
            return response

        except requests.RequestException as exc:
            print(f"{WARN} {name} [optional unavailable]")
            print(f"    {exc}")
            self.warnings += 1
            return None

    def json(self, response: requests.Response | None) -> dict[str, Any]:
        if response is None:
            return {}

        try:
            data = response.json()
            return data if isinstance(data, dict) else {"data": data}
        except ValueError:
            return {}

    def summary(self) -> None:
        print()
        print("=" * 72)
        print("TEST SUMMARY")
        print("=" * 72)
        print(f"{PASS} Passed   : {self.passed}")
        print(f"{FAIL} Failed   : {self.failed}")
        print(f"{WARN} Warnings  : {self.warnings}")
        print("=" * 72)

        if self.failed:
            print(f"{FAIL} SYSTEM TEST FAILED")
        else:
            print(f"{PASS} SYSTEM TEST COMPLETED")


def wait_for_observation(
    runner: TestRunner,
    duration: int,
    poll_interval: int = 3,
) -> dict[str, Any] | None:
    print()
    print("Waiting for a simulated observation...")

    deadline = time.time() + duration

    while time.time() < deadline:
        response = runner.check(
            "Observation API",
            "GET",
            "/api/v1/observations",
        )

        if response is not None and response.status_code == 200:
            data = runner.json(response)

            # Support common response shapes.
            observations = (
                data.get("observations")
                or data.get("items")
                or data.get("data")
            )

            if isinstance(observations, list) and observations:
                observation = observations[-1]

                print()
                print("Latest observation:")
                print("-" * 50)

                for key in (
                    "id",
                    "observation_id",
                    "timestamp",
                    "latitude",
                    "longitude",
                    "altitude_km",
                    "priority",
                    "ai_status",
                    "ai_provider",
                    "ai_model",
                    "ai_smoke_score",
                    "confidence",
                ):
                    if key in observation:
                        print(f"{key:20}: {observation[key]}")

                return observation

        time.sleep(poll_interval)

    return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="2U CubeSat Digital Twin end-to-end test"
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help="Backend URL",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=DEFAULT_DURATION,
        help="Seconds to wait for an observation",
    )

    args = parser.parse_args()

    runner = TestRunner(args.base_url)

    print("=" * 72)
    print("2U CUBESAT DIGITAL TWIN \u2014 END-TO-END SYSTEM TEST")
    print("=" * 72)
    print(f"Backend: {args.base_url}")
    print()

    # ------------------------------------------------------------------
    # 1. BACKEND HEALTH
    # ------------------------------------------------------------------

    health = runner.check(
        "Backend health",
        "GET",
        "/api/v1/health",
    )

    if health is None:
        print()
        print("Backend is unreachable.")
        print("Start it with:")
        print(
            "  cd backend && "
            "uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
        )
        return 1

    # ------------------------------------------------------------------
    # 2. CONFIGURATION
    # ------------------------------------------------------------------

    config_response = runner.check(
        "System configuration",
        "GET",
        "/api/v1/config",
    )

    config = runner.json(config_response)

    if config:
        print()
        print("Configuration snapshot:")
        print("-" * 50)

        for key in (
            "ai_mode",
            "ai_provider",
            "orbit_mode",
            "tle_source",
            "simulation_speed",
        ):
            if key in config:
                print(f"{key:20}: {config[key]}")

    # ------------------------------------------------------------------
    # 3. AI STATUS
    # ------------------------------------------------------------------

    ai_response = runner.check(
        "AI service status",
        "GET",
        "/api/v1/ai/status",
    )

    ai_status = runner.json(ai_response)

    if ai_status:
        print()
        print("AI status:")
        print("-" * 50)

        for key in (
            "mode",
            "primary_provider",
            "failover_enabled",
            "timeout_seconds",
            "retry_count",
        ):
            if key in ai_status:
                print(f"{key:20}: {ai_status[key]}")

    # ------------------------------------------------------------------
    # 4. ORBIT / TLE
    # ------------------------------------------------------------------

    tle_response = runner.soft_check(
        "TLE service status",
        "GET",
        "/api/v1/tle/status",
    )

    if tle_response:
        tle_status = runner.json(tle_response)

        print()
        print("TLE status:")
        print("-" * 50)

        for key in (
            "mode",
            "source",
            "status",
            "satellite",
            "age_hours",
        ):
            if key in tle_status:
                print(f"{key:20}: {tle_status[key]}")

    # ------------------------------------------------------------------
    # 5. GROUND NETWORK
    # ------------------------------------------------------------------

    ground_response = runner.soft_check(
        "Ground network",
        "GET",
        "/api/v1/ground-station/network",
    )

    if ground_response:
        ground = runner.json(ground_response)

        stations = (
            ground.get("stations")
            or ground.get("data")
            or []
        )

        if isinstance(stations, list):
            print(f"\nGround stations detected: {len(stations)}")

    # ------------------------------------------------------------------
    # 6. SUBSYSTEM STATUS
    # ------------------------------------------------------------------

    runner.check(
        "Spacecraft state",
        "GET",
        "/api/v1/spacecraft/state",
    )

    runner.check(
        "Power subsystem",
        "GET",
        "/api/v1/spacecraft/power",
    )

    runner.check(
        "Thermal subsystem",
        "GET",
        "/api/v1/spacecraft/thermal",
    )

    runner.check(
        "ADCS / attitude",
        "GET",
        "/api/v1/spacecraft/attitude",
    )

    runner.check(
        "Telemetry endpoint",
        "GET",
        "/api/v1/telemetry/latest",
    )

    # ------------------------------------------------------------------
    # 7. ENVIRONMENT
    # ------------------------------------------------------------------

    runner.soft_check(
        "Weather integration",
        "GET",
        "/api/v1/environment/weather",
    )

    runner.soft_check(
        "Air quality integration",
        "GET",
        "/api/v1/environment/air-quality",
    )

    runner.soft_check(
        "FIRMS integration",
        "GET",
        "/api/v1/environment/hotspots",
    )

    runner.soft_check(
        "FIRMS adapter status",
        "GET",
        "/api/v1/firms/status",
    )

    runner.soft_check(
        "Correlation status",
        "GET",
        "/api/v1/correlation/status",
    )

    # ------------------------------------------------------------------
    # 8. START SIMULATION
    # ------------------------------------------------------------------

    print()
    print("Starting simulation...")

    runner.check(
        "Start simulation",
        "POST",
        "/api/v1/simulation/start",
    )

    # ------------------------------------------------------------------
    # 9. WATCH LIVE STATE
    # ------------------------------------------------------------------

    print()
    print("Watching live spacecraft state for 8 seconds...")

    start = time.time()

    while time.time() - start < 8:
        state_response = runner.check(
            "Live spacecraft state",
            "GET",
            "/api/v1/spacecraft/state",
        )

        if state_response:
            state = runner.json(state_response)

            if state:
                lat = state.get("latitude")
                lon = state.get("longitude")
                alt = state.get("altitude_km")

                if lat is not None:
                    print(
                        f"    Position: "
                        f"{lat:.3f}, {lon:.3f} @ {alt:.1f} km"
                    )

        time.sleep(2)

    # ------------------------------------------------------------------
    # 10. WAIT FOR OBSERVATION
    # ------------------------------------------------------------------

    observation = wait_for_observation(
        runner,
        duration=args.duration,
    )

    if observation is None:
        print()
        print(
            f"{WARN} No observation appeared within "
            f"{args.duration}s."
        )
        runner.warnings += 1

    # ------------------------------------------------------------------
    # 11. OBSERVATION HISTORY
    # ------------------------------------------------------------------

    runner.check(
        "Observation history",
        "GET",
        "/api/v1/history/observations",
    )

    runner.check(
        "Event history",
        "GET",
        "/api/v1/history/events",
    )

    runner.check(
        "Telemetry history",
        "GET",
        "/api/v1/history/telemetry",
    )

    # ------------------------------------------------------------------
    # 12. DOWNLINK
    # ------------------------------------------------------------------

    runner.check(
        "Downlink status",
        "GET",
        "/api/v1/downlink/status",
    )

    runner.check(
        "Downlink queue",
        "GET",
        "/api/v1/downlink/queue",
    )

    # ------------------------------------------------------------------
    # 13. FAULT / RECOVERY SYSTEM
    # ------------------------------------------------------------------

    runner.soft_check(
        "Recovery status",
        "GET",
        "/api/v1/recovery/status",
    )

    runner.soft_check(
        "EPS status",
        "GET",
        "/api/v1/eps/status",
    )

    runner.soft_check(
        "Thermal model status",
        "GET",
        "/api/v1/thermal/status",
    )

    # ------------------------------------------------------------------
    # 14. REPLAY
    # ------------------------------------------------------------------

    runner.soft_check(
        "Replay sessions",
        "GET",
        "/api/v1/replay/sessions",
    )

    # ------------------------------------------------------------------
    # 15. EXPORTS
    # ------------------------------------------------------------------

    export_response = runner.soft_check(
        "Observation export",
        "GET",
        "/api/v1/export/observations",
        params={"format": "json"},
    )

    if export_response is not None:
        content_type = export_response.headers.get(
            "content-type",
            "",
        )
        print(f"    Export content-type: {content_type}")

    runner.soft_check(
        "Telemetry export",
        "GET",
        "/api/v1/export/telemetry",
        params={"format": "json"},
    )

    # ------------------------------------------------------------------
    # 16. SYSTEM RESOURCES
    # ------------------------------------------------------------------

    runner.soft_check(
        "System resources",
        "GET",
        "/api/system/resources",
    )

    # ------------------------------------------------------------------
    # 17. FINAL TELEMETRY
    # ------------------------------------------------------------------

    final_telemetry = runner.check(
        "Final telemetry",
        "GET",
        "/api/v1/telemetry/latest",
    )

    if final_telemetry:
        telemetry = runner.json(final_telemetry)

        print()
        print("Final telemetry snapshot:")
        print("-" * 50)

        for key in (
            "timestamp",
            "packet_sequence",
            "mission_mode",
            "ai_status",
            "ai_provider",
            "ai_smoke_score",
            "priority",
        ):
            if key in telemetry:
                print(f"{key:20}: {telemetry[key]}")

    # ------------------------------------------------------------------
    # 18. STOP + RESET
    # ------------------------------------------------------------------

    print()
    print("Stopping simulation...")

    runner.check(
        "Stop simulation",
        "POST",
        "/api/v1/simulation/stop",
    )

    runner.check(
        "Reset simulation",
        "POST",
        "/api/v1/simulation/reset",
    )

    # ------------------------------------------------------------------
    # SUMMARY
    # ------------------------------------------------------------------

    runner.summary()

    return 1 if runner.failed else 0


if __name__ == "__main__":
    sys.exit(main())
