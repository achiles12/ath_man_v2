from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    secret_key: str
    password_reset_token_expiry_hours: int = 1
    saas_admin_email: str
    cors_origins: str = "http://localhost:20305"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
