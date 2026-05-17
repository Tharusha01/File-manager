from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    data_dir: Path = Path("/data")
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 24 * 30

    username: str = "admin"
    password: str = "admin"

    listen_interfaces: str = "0.0.0.0:6881"

    upload_limit: int = 0  # 0 = unlimited, set to 0 to disable seeding after download

    cookie_name: str = "fm_token"
    cookie_secure: bool = False

    @property
    def downloads_dir(self) -> Path:
        return self.data_dir / "downloads"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "app.db"

    @property
    def resume_dir(self) -> Path:
        return self.data_dir / "resume"


settings = Settings()
