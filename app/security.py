import os
import random
import datetime
from typing import List

from fastapi import Depends, status
from fastapi.security import OAuth2PasswordBearer
from fastapi.exceptions import HTTPException
from jose import JWTError, jwt

from app import USER_SECRET, USER_URL

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=USER_URL)

WORDS: List[str] = []


async def get_username_from_token(token: str = Depends(oauth2_scheme)) -> str:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            USER_SECRET,
            audience="micro-rocket",
            issuer="user-manager",
            algorithms=["HS256"]
        )
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    return username


def get_random_word() -> str:
    global WORDS
    if len(WORDS) == 0:
        cwd = os.getcwd()
        with open(os.path.join(cwd, "app", "words.txt"), 'r') as f:
            WORDS = [w.strip() for w in f.readlines()]

    random.seed(datetime.datetime.utcnow().timestamp())
    return random.choice(WORDS)
