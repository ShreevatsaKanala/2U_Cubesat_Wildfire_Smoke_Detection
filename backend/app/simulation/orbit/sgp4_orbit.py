"""
SGP4 Orbit Service for CubeSat Digital Twin.

This module provides orbit propagation using the SGP4 model for accurate
satellite position prediction, with a fallback analytical circular orbit
model for Phase 1 development and testing.

NOTE: All orbital parameters here are SIMULATION ORBIT parameters for the
digital twin, not actual flight orbit parameters.
"""

from datetime import datetime, timezone, timedelta
import logging
import math
from typing import Optional

logger = logging.getLogger(__name__)

# SGP4 constants
MU_EARTH = 398600.4418  # km^3/s^2
R_EARTH = 6371.0  # km

# Default orbital parameters for simulation
DEFAULT_ALTITUDE_KM = 500.0
DEFAULT_INCLINATION_DEG = 97.4  # Sun-synchronous approximation
DEFAULT_ECCENTRICITY = 0.0  # Circular orbit
DEFAULT_RAAN_DEG = 0.0
DEFAULT_ARG_PERIGEE_DEG = 0.0
DEFAULT_MEAN_ANOMALY_DEG = 0.0


class SGP4OrbitService:
    """
    Orbit service using SGP4 propagator with analytical fallback.

    Provides satellite position and velocity computation for the CubeSat
    Digital Twin simulation. Can operate in two modes:

    1. SGP4 mode: Uses TLE data for accurate propagation
    2. Analytical fallback: Simple circular orbit model for Phase 1

    The default configuration uses a 500 km altitude sun-synchronous
    orbit suitable for Earth observation missions.
    """

    def __init__(self, config: dict):
        """
        Initialize orbit service with configuration.

        Args:
            config: Dictionary containing orbital parameters. Accepts either:
                - TLE data: {"tle_line1": "...", "tle_line2": "..."}
                - Keplerian elements: {"semi_major_axis_km": float,
                    "eccentricity": float, "inclination_deg": float,
                    "raan_deg": float, "arg_perigee_deg": float,
                    "mean_anomaly_deg": float, "epoch": datetime}
                - Simple altitude: {"altitude_km": float, "inclination_deg": float}
                - Empty dict {} for defaults
        """
        self.config = config or {}
        self._use_sgp4 = False
        self._satrec = None
        self._epoch = datetime.now(timezone.utc)

        # Parse configuration
        if "tle_line1" in self.config and "tle_line2" in self.config:
            self._init_from_tle(self.config["tle_line1"], self.config["tle_line2"])
        elif "semi_major_axis_km" in self.config:
            self._init_from_keplerian(self.config)
        else:
            self._init_from_altitude(
                self.config.get("altitude_km", DEFAULT_ALTITUDE_KM),
                self.config.get("inclination_deg", DEFAULT_INCLINATION_DEG)
            )

    def _init_from_tle(self, tle_line1: str, tle_line2: str):
        """Initialize from Two-Line Element set."""
        try:
            from sgp4.api import Satrec, WGS72
            self._satrec = Satrec.twoline2rv(tle_line1, tle_line2, WGS72)
            self._use_sgp4 = True
            self._epoch = datetime.now(timezone.utc)
        except ImportError:
            logger.warning("SGP4 library not available, falling back to analytical model")
            self._init_from_altitude(DEFAULT_ALTITUDE_KM, DEFAULT_INCLINATION_DEG)

    def _init_from_keplerian(self, keplerian: dict):
        """Initialize from Keplerian orbital elements."""
        self._semi_major_axis = keplerian.get("semi_major_axis_km", R_EARTH + DEFAULT_ALTITUDE_KM)
        self._eccentricity = keplerian.get("eccentricity", DEFAULT_ECCENTRICITY)
        self._inclination_rad = math.radians(keplerian.get("inclination_deg", DEFAULT_INCLINATION_DEG))
        self._raan_rad = math.radians(keplerian.get("raan_deg", DEFAULT_RAAN_DEG))
        self._arg_perigee_rad = math.radians(keplerian.get("arg_perigee_deg", DEFAULT_ARG_PERIGEE_DEG))
        self._mean_anomaly_rad = math.radians(keplerian.get("mean_anomaly_deg", DEFAULT_MEAN_ANOMALY_DEG))
        self._epoch = keplerian.get("epoch", datetime.now(timezone.utc))
        self._use_sgp4 = False

    def _init_from_altitude(self, altitude_km: float, inclination_deg: float):
        """Initialize from altitude and inclination for circular orbit."""
        self._altitude_km = altitude_km
        self._semi_major_axis = R_EARTH + altitude_km
        self._inclination_rad = math.radians(inclination_deg)
        self._eccentricity = 0.0
        self._use_sgp4 = False

    def _solve_kepler_equation(self, mean_anomaly: float, tolerance: float = 1e-8) -> float:
        """
        Solve Kepler's equation M = E - e*sin(E) using Newton-Raphson.

        Args:
            mean_anomaly: Mean anomaly in radians
            tolerance: Convergence tolerance

        Returns:
            Eccentric anomaly in radians
        """
        E = mean_anomaly  # Initial guess
        for _ in range(100):
            f = E - self._eccentricity * math.sin(E) - mean_anomaly
            f_prime = 1.0 - self._eccentricity * math.cos(E)
            delta = f / f_prime
            E -= delta
            if abs(delta) < tolerance:
                break
        return E

    def _analytical_propagate(self, timestamp: datetime) -> dict:
        """
        Propagate orbit analytically using Keplerian mechanics.

        Uses Kepler's equation to solve for true anomaly, then converts
        to ECI position/velocity for circular or elliptical orbits.

        Args:
            timestamp: Current simulation time

        Returns:
            Dictionary with position_eci, velocity_eci, latitude, longitude,
            altitude_km, velocity_km_s
        """
        # Compute time elapsed since epoch
        dt_seconds = (timestamp - self._epoch).total_seconds()

        # Compute orbital period: T = 2*pi*sqrt(a^3/mu)
        period = 2 * math.pi * math.sqrt(self._semi_major_axis ** 3 / MU_EARTH)

        # Mean motion (radians per second)
        mean_motion = 2 * math.pi / period

        # Mean anomaly at current time
        mean_anomaly = (self._mean_anomaly_rad if hasattr(self, '_mean_anomaly_rad')
                       else 0.0) + mean_motion * dt_seconds

        # Normalize to [0, 2*pi]
        mean_anomaly = mean_anomaly % (2 * math.pi)

        # Solve Kepler's equation for eccentric anomaly
        eccentric_anomaly = self._solve_kepler_equation(mean_anomaly)

        # True anomaly (for circular orbit, this equals eccentric anomaly)
        if self._eccentricity < 1e-10:
            true_anomaly = eccentric_anomaly
        else:
            true_anomaly = 2 * math.atan2(
                math.sqrt(1 + self._eccentricity) * math.sin(eccentric_anomaly / 2),
                math.sqrt(1 - self._eccentricity) * math.cos(eccentric_anomaly / 2)
            )

        # Radius from center of Earth
        r = self._semi_major_axis * (1 - self._eccentricity * math.cos(eccentric_anomaly))

        # Position in orbital plane
        x_orbital = r * math.cos(true_anomaly)
        y_orbital = r * math.sin(true_anomaly)

        # Velocity in orbital plane (for circular orbit)
        v_orbital = math.sqrt(MU_EARTH * (2 / r - 1 / self._semi_major_axis))
        vx_orbital = -v_orbital * math.sin(true_anomaly)
        vy_orbital = v_orbital * math.cos(true_anomaly)

        # Rotation matrices for orbital plane to ECI
        cos_raan = math.cos(self._raan_rad if hasattr(self, '_raan_rad') else 0)
        sin_raan = math.sin(self._raan_rad if hasattr(self, '_raan_rad') else 0)
        cos_inc = math.cos(self._inclination_rad)
        sin_inc = math.sin(self._inclination_rad)
        cos_arg = math.cos(self._arg_perigee_rad if hasattr(self, '_arg_perigee_rad') else 0)
        sin_arg = math.sin(self._arg_perigee_rad if hasattr(self, '_arg_perigee_rad') else 0)

        # Transform to ECI coordinates
        position_eci = [
            x_orbital * (cos_raan * cos_arg - sin_raan * sin_arg * cos_inc) -
            y_orbital * (cos_raan * sin_arg + sin_raan * cos_arg * cos_inc),
            x_orbital * (sin_raan * cos_arg + cos_raan * sin_arg * cos_inc) -
            y_orbital * (sin_raan * sin_arg - cos_raan * cos_arg * cos_inc),
            x_orbital * (sin_arg * sin_inc) + y_orbital * (cos_arg * sin_inc)
        ]

        velocity_eci = [
            vx_orbital * (cos_raan * cos_arg - sin_raan * sin_arg * cos_inc) -
            vy_orbital * (cos_raan * sin_arg + sin_raan * cos_arg * cos_inc),
            vx_orbital * (sin_raan * cos_arg + cos_raan * sin_arg * cos_inc) -
            vy_orbital * (sin_raan * sin_arg - cos_raan * cos_arg * cos_inc),
            vx_orbital * (sin_arg * sin_inc) + vy_orbital * (cos_arg * sin_inc)
        ]

        # Compute lat/lon/alt from ECI
        altitude_km = r - R_EARTH
        velocity_km_s = math.sqrt(sum(v ** 2 for v in velocity_eci))

        # Convert ECI to geodetic (simplified - assumes Earth-centered)
        x, y, z = position_eci
        latitude = math.degrees(math.atan2(z, math.sqrt(x ** 2 + y ** 2)))
        longitude = math.degrees(math.atan2(y, x))

        # Normalize longitude to [-180, 180]
        while longitude > 180:
            longitude -= 360
        while longitude < -180:
            longitude += 360

        return {
            "latitude": latitude,
            "longitude": longitude,
            "altitude_km": altitude_km,
            "velocity_km_s": velocity_km_s,
            "position_eci": position_eci,
            "velocity_eci": velocity_eci
        }

    def update(self, timestamp: datetime) -> dict:
        """
        Update satellite position and velocity.

        Args:
            timestamp: Current simulation time (UTC)

        Returns:
            Dictionary containing:
                - latitude: Geodetic latitude in degrees
                - longitude: Geodetic longitude in degrees
                - altitude_km: Altitude above Earth surface in km
                - velocity_km_s: Orbital velocity magnitude in km/s
                - position_eci: [x, y, z] position in ECI frame (km)
                - velocity_eci: [vx, vy, vz] velocity in ECI frame (km/s)
        """
        if self._use_sgp4 and self._satrec is not None:
            try:
                from sgp4.api import Satrec
                jd = timestamp.timestamp() / 86400.0 + 2440587.5
                e, r, v = self._satrec.sgp4(jd, 0)
                if e == 0:
                    x, y, z = r
                    vx, vy, vz = v
                    altitude_km = math.sqrt(x**2 + y**2 + z**2) - R_EARTH
                    velocity_km_s = math.sqrt(vx**2 + vy**2 + vz**2)
                    latitude = math.degrees(math.atan2(z, math.sqrt(x**2 + y**2)))
                    longitude = math.degrees(math.atan2(y, x))
                    while longitude > 180:
                        longitude -= 360
                    while longitude < -180:
                        longitude += 360
                    return {
                        "latitude": latitude,
                        "longitude": longitude,
                        "altitude_km": altitude_km,
                        "velocity_km_s": velocity_km_s,
                        "position_eci": list(r),
                        "velocity_eci": list(v)
                    }
            except Exception as e:
                logger.warning("SGP4 propagation failed: %s, using analytical model", e)

        # Fallback to analytical model
        return self._analytical_propagate(timestamp)

    def get_ground_track(self, start_time: datetime, end_time: datetime,
                         step_seconds: float = 60.0) -> list:
        """
        Compute ground track over a time period.

        Args:
            start_time: Start of ground track computation
            end_time: End of ground track computation
            step_seconds: Time step between points (default 60s)

        Returns:
            List of dictionaries with lat/lon/alt/velocity for each time step
        """
        ground_track = []
        current_time = start_time

        while current_time <= end_time:
            state = self.update(current_time)
            ground_track.append({
                "timestamp": current_time.isoformat(),
                "latitude": state["latitude"],
                "longitude": state["longitude"],
                "altitude_km": state["altitude_km"],
                "velocity_km_s": state["velocity_km_s"]
            })
            current_time = current_time + timedelta(seconds=step_seconds)

        return ground_track
