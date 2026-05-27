import secrets
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./ventas.db"
    debug: bool = False
    secret_key: str = ""
    admin_username: str = "admin"
    admin_password: str = "admin123"
    https_only: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    def get_secret_key(self) -> str:
        if self.secret_key:
            return self.secret_key
        try:
            with open(".secret_key", "r") as f:
                return f.read().strip()
        except FileNotFoundError:
            key = secrets.token_hex(32)
            with open(".secret_key", "w") as f:
                f.write(key)
            return key


settings = Settings()
