
from fastapi import (
    Depends,
)
from fastapi.security import  OAuth2PasswordBearer


oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/api/v1/auth/login')


class AuthService:
    @classmethod
    async def requires_authorization(cls, token: str = Depends(oauth2_scheme)):
        return token
