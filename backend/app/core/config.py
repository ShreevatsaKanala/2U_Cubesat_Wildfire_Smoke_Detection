from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "CubeSat Digital Twin"
    VERSION: str = "0.2.0"
    SIMULATION_SPEED: float = 1.0
    TELEMETRY_FREQUENCY_HZ: float = 1.0
    OBSERVATION_INTERVAL_S: float = 30.0

    NASA_FIRMS_MAP_KEY: str = ""
    CESIUM_ION_TOKEN: str = ""
    CESIUM_ION_DEFAULT_ACCESS_TOKEN: str = ""

    OPEN_METEO_BASE_URL: str = "https://api.open-meteo.com/v1"
    NASA_FIRMS_BASE_URL: str = "https://firms.modaps.eosdis.nasa.gov/api"
    CELESTRAK_BASE_URL: str = "https://celestrak.org/NORAD/elements/gp.php"

    DATABASE_URL: str = "sqlite+aiosqlite:///./data/cubesat_twin.db"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


settings = Settings()
