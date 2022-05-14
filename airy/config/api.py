import typing as t

from pydantic import BaseSettings, UUID4, IPvAnyAddress, IPvAnyInterface, FilePath


class ApiConfig(BaseSettings):
    is_activated: bool
    secret: UUID4
    ip: IPvAnyAddress
    port: int
    ssl_cert: t.Optional[FilePath]
    ssl_key: t.Optional[FilePath]

    class Config:
        env_file = ".env"
        env_prefix = "api_"


api_config = ApiConfig()
