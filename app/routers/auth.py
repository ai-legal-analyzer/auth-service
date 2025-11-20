from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional
import uuid

import jwt
from fastapi import APIRouter, status, Depends, HTTPException, Response
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.sync import update

from app.backend.db_depends import get_db
from app.models.user import User
from app.models.tokens import RevokedToken
from app.schemas import CreateUser

SECRET_KEY = '30ee8e1faadb9974647186858ad7eedab17d859ae2180c6c3da1a4781bb13c62'
ALGORITHM = 'HS256'

ACCESS_TOKEN_EXPIRE_MINUTES = 20
REFRESH_TOKEN_EXPIRE_DAYS = 7

router = APIRouter(prefix='/auth', tags=['auth'])
bcrypt_context = CryptContext(schemes=['bcrypt'], deprecated='auto')

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_user(
        db: Annotated[AsyncSession, Depends(get_db)],
        create_user: CreateUser
):
    # Сначала проверяем существование пользователя
    existing_user = await db.execute(
        select(User).where(
            (User.username == create_user.username) |
            (User.email == create_user.email)
        )
    )
    existing_user = existing_user.scalar_one_or_none()

    if existing_user:
        if existing_user.username == create_user.username:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": {
                        "code": "user_already_exists",
                        "message": "Пользователь с указанным именем уже существует.",
                        "target": "username"
                    }
                }
            )
        elif existing_user.email == create_user.email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": {
                        "code": "user_already_exists",
                        "message": "Пользователь с указанным email уже зарегистрирован.",
                        "target": "email"
                    }
                }
            )

    # Создаем пользователя
    result = await db.execute(
        insert(User).values(
            first_name=create_user.first_name,
            last_name=create_user.last_name,
            username=create_user.username,
            email=create_user.email,
            hashed_password=bcrypt_context.hash(create_user.password)
        )
    )
    await db.commit()

    return {
        'status_code': status.HTTP_201_CREATED,
        'transaction': 'Successful',
        'user_id': result.inserted_primary_key[0] if result.inserted_primary_key else None
    }


async def authenticate_user(db: Annotated[AsyncSession, Depends(get_db)], username: str, password: str):
    user = await db.scalar(select(User).where(User.username == username))
    if not user or not bcrypt_context.verify(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid authentication credentials',
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def create_access_token(username: str, user_id: int, is_admin: bool, is_verified: bool, expires_delta: timedelta):
    payload = {
        'sub': username,
        'id': user_id,
        'is_admin': is_admin,
        'is_verified': is_verified,
        'exp': datetime.now(timezone.utc) + expires_delta
    }

    payload['exp'] = int(payload['exp'].timestamp())
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


async def create_refresh_token(username: str, user_id: int, expires_delta: timedelta):
    payload = {
        'sub': username,
        'id': user_id,
        'jti': str(uuid.uuid4()),
        'type': 'refresh',
        'exp': datetime.now(timezone.utc) + expires_delta
    }
    payload['exp'] = int(payload['exp'].timestamp())
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


@router.post('/token')
async def login(db: Annotated[AsyncSession, Depends(get_db)],
                form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    user = await authenticate_user(db, form_data.username, form_data.password)

    access_token = await create_access_token(
        user.username,
        user.id,
        user.is_admin,
        user.is_verified,
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    refresh_token = await create_refresh_token(
        user.username,
        user.id,
        expires_delta=timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )

    return {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'token_type': 'bearer'
    }


@router.post('/refresh', status_code=status.HTTP_201_CREATED)
async def refresh_token(refresh_token: str, db: Annotated[AsyncSession, Depends(get_db)]):
    try:
        payload: dict = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])

        if payload.get('type') != 'refresh':
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Invalid token type'
            )

        current_time = datetime.now(timezone.utc).timestamp()
        if payload['exp'] < current_time:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Refresh token expired'
            )

        revoked_token = await db.scalar(
            select(RevokedToken).where(RevokedToken.jti == payload['jti'])
        )
        if revoked_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Token revoked'
            )

        user = await db.scalar(select(User).where(User.id == payload['id']))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='User not found'
            )

        new_access_token = await create_access_token(
            user.username,
            user.id,
            user.is_admin,
            user.is_verified,
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )

        return {
            'access_token': new_access_token,
            'token_time': 'bearer'
        }
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Refresh token expired'
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid refresh token'
        )


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    try:
        payload: dict = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str | None = payload.get('sub')
        user_id: int | None = payload.get('id')
        is_admin: bool | None = payload.get('is_admin')
        is_verified: bool | None = payload.get('is_verified')
        expire: int | None = payload.get('exp')

        if username is None or user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Could not validate user'
            )
        if expire is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='No access token supplied'
            )
        if not isinstance(expire, int):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Invalid token format'
            )

        current_time = datetime.now(timezone.utc).timestamp()

        if expire < current_time:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Token expired!'
            )

        return {
            'username': username,
            'id': user_id,
            'is_admin': is_admin,
            'is_verified': is_verified,
        }
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Token expired!'
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Could not validate user'
        )
    except jwt.exceptions:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Could not validate user'
        )


@router.get('/read_current_user')
async def read_current_user(user: dict = Depends(get_current_user)):
    return {'User': user}


@router.post('/logout')
async def logout(
        refresh_token: str,
        db: Annotated[AsyncSession, Depends(get_db)],
        get_user: dict = Depends(get_current_user)
):
    try:
        payload: dict = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])

        await db.execute(insert(RevokedToken).values(
            jti=payload['jti'],
            user_id=get_user['id']
        ))
        await db.commit()

        return {'message': 'Successfully logged out'}

    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Invalid token'
        )
