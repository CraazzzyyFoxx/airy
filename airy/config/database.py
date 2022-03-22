from pydantic import BaseSettings


class DatabaseConfig(BaseSettings):
    db: str
    host: str
    password: str
    port: int
    user: str
    initialize: str
    migrate: str

    class Config:
        env_file = ".env"
        env_prefix = "postgres_"


db_config = DatabaseConfig()


tortoise_config = {
    "connections": {
        "default": {
            "engine": "tortoise.backends.asyncpg",
            "credentials": {
                "database": db_config.db,
                "host": db_config.host,  # db for docker
                "password": db_config.password,
                "port": db_config.port,
                "user": db_config.user,
            },
        }
    },
    "apps": {
        "main": {
            "models": ["airy.core.models.db"],
            "default_connection": "default",
        }
    },
}
