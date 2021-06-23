from pydantic import BaseSettings, AnyUrl


class MoltinSettings(BaseSettings):
    MOLTIN_URL: AnyUrl = "https://api.moltin.com"
    # MOLTEN_STORE_ID: str
    MOLTIN_CLIENT_ID: str
    # MOLTEN_CLIENT_SECRET: str

    class Config:
        env_file: str = ".env"
        env_file_encoding = "utf-8"



class Settings(BaseSettings):
    TG_BOT_TOKEN: str
    TG_BOT_ADMIN_ID: int

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = None
    REDIS_PASSWORD: str = None

    LOG_LEVEL: str = "DEBUG"

    PAYMENT_PROVIDER_TOKEN: str
    YANDEX_GEOCODER_APIKEY: str
    COURIER_TG_ID: int
    MAX_BUTTONS_IN_ROW: int = 4

    class Config:
        env_file: str = ".env"
        env_file_encoding = "utf-8"
