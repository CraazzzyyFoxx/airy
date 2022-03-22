from pydantic import BaseSettings


class LavalinkConfig(BaseSettings):
    url: str
    password: str

    class Config:
        env_file = ".env"
        env_prefix = "lavalink_"


lavalink_config = LavalinkConfig()
