from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "CubeSat Digital Twin"
    VERSION: str = "0.3.0"
    SIMULATION_SPEED: float = 1.0
    TELEMETRY_FREQUENCY_HZ: float = 1.0
    OBSERVATION_INTERVAL_S: float = 30.0

    # ML configuration
    ML_MODE: str = "mock"  # "mock" or "real"
    ML_MODEL_PATH: str = "data/models/best_model.pt"
    ML_MODEL_NAME: str = "smoke-classifier"
    ML_MODEL_VERSION: str = "0.1.0"
    ML_INPUT_RESOLUTION: list = [224, 224]
    ML_SMOKE_THRESHOLD: float = 0.5
    ML_DEVICE: str = "cpu"

    # AI Vision configuration
    AI_MODE: str = "mock"  # "mock" or "live"
    AI_PROVIDER: str = "openrouter"  # "openrouter" or "groq"
    OPENROUTER_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    OPENROUTER_MODEL: str = "google/gemini-2.0-flash-001"
    GROQ_MODEL: str = "qwen/qwen3.6-27b"
    AI_TIMEOUT_SECONDS: int = 30
    AI_MAX_IMAGE_MB: int = 10
    AI_IMAGE_MAX_DIMENSION: int = 1024
    AI_TEMPERATURE: float = 0
    AI_RETRY_COUNT: int = 2
    AI_FAILOVER_ENABLED: bool = True
    AI_MAX_REQUESTS_PER_MINUTE: int = 10

    # AI Vision configuration
    AI_MODE: str = "mock"  # "mock" or "live"
    AI_PROVIDER: str = "openrouter"  # "openrouter" or "groq"
    AI_TIMEOUT_SECONDS: int = 30
    AI_RETRY_COUNT: int = 2
    AI_FAILOVER_ENABLED: bool = True
    AI_MAX_REQUESTS_PER_MINUTE: int = 10
    AI_TEMPERATURE: float = 0.0
    AI_IMAGE_MAX_DIMENSION: int = 1024
    AI_MAX_IMAGE_MB: float = 10.0
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "google/gemini-2.0-flash-001"
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "qwen/qwen3.6-27b"

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
