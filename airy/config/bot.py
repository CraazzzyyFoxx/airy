from pydantic import BaseSettings


class BotConfig(BaseSettings):
    token: str
    dev_guilds: list[int]
    errors_trace_channel: int

    class Config:
        env_file = ".env"
        env_prefix = "bot_"


bot_config = BotConfig()
