from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from sqlalchemy.engine import make_url

DEFAULT_SQLITE_URL = "sqlite:///./yorizo.db"
ASYNC_TO_SYNC_DRIVERS = {
    "mysql+asyncmy": "mysql+pymysql",
    "sqlite+aiosqlite": "sqlite",
}


class Settings(BaseSettings):
    db_host: str = Field(default="localhost", env="DB_HOST")
    db_port: int = Field(default=3306, env="DB_PORT")
    # NOTE: Azure App Service cannot use an app setting named "username";
    # use DB_USERNAME instead for environment configuration.
    db_username: str | None = Field(default=None, env="DB_USERNAME")
    db_password: str | None = Field(default=None, env="DB_PASSWORD")
    db_name: str | None = Field(default=None, env="DB_NAME")
    database_url: str | None = Field(default=None, env="DATABASE_URL")

    openai_api_key: str | None = Field(default=None, env="OPENAI_API_KEY")
    openai_model_chat: str = Field(default="gpt-4.1-mini", env="OPENAI_MODEL_CHAT")
    openai_model_embedding: str = Field(default="text-embedding-3-small", env="OPENAI_MODEL_EMBEDDING")
    rag_persist_dir: str = Field(default="./rag_store", env="RAG_PERSIST_DIR")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


def get_db_url(settings: "Settings") -> str:
    if settings.database_url:
        return settings.database_url

    if settings.db_username and settings.db_password and settings.db_name:
        return (
            f"mysql+asyncmy://{settings.db_username}:"
            f"{settings.db_password}@{settings.db_host}:{settings.db_port}/"
            f"{settings.db_name}"
        )

    return DEFAULT_SQLITE_URL


def normalize_db_url(url: str) -> str:
    """
    Convert async driver URLs to sync equivalents so they can be used
    with the current synchronous SQLAlchemy engine/session setup.
    """
    url_obj = make_url(url)
    driver = url_obj.drivername
    if driver in ASYNC_TO_SYNC_DRIVERS:
        url_obj = url_obj.set(drivername=ASYNC_TO_SYNC_DRIVERS[driver])
    return url_obj.render_as_string(hide_password=False)


settings = Settings()
