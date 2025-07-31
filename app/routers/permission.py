from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.backend.db_depends import get_db
from app.models.user import User
from app.routers.auth import get_current_user

router = APIRouter(prefix='/permission', tags=['permission'])


@router.patch('/set-admin-permission')
async def set_admin_permission(db: Annotated[AsyncSession, Depends(get_db)],
                               get_user: Annotated[dict, Depends(get_current_user)], user_id: int):
    if get_user.get('is_admin'):
        user = await db.scalar(select(User).where(User.id == user_id))

        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='User not found'
            )
        if not user.is_admin:
            await db.execute(update(User).where(User.id == user_id).values(is_admin=True))
            await db.commit()
            return {
                'status_code': status.HTTP_200_OK,
                'detail': 'User is now admin'
            }
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='User is already admin'
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You don't have admin permission"
        )


@router.patch('/revoke-admin-permission')
async def revoke_admin_permission(db: Annotated[AsyncSession, Depends(get_db)],
                                  get_user: Annotated[dict, Depends(get_current_user)], user_id: int):
    if get_user.get('is_admin'):
        user = await db.scalar(select(User).where(User.id == user_id))
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='User not found'
            )
        if user.is_admin:
            await db.execute(update(User).where(User.id == user_id).values(is_admin=False))
            await db.commit()
            return {
                'status_code': status.HTTP_200_OK,
                'detail': 'User is not now admin'
            }
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='User is already not admin'
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You don't have admin permission"
        )


@router.delete('/delete')
async def delete_user(db: Annotated[AsyncSession, Depends(get_db)],
                      get_user: Annotated[dict, Depends(get_current_user)], user_id: int):
    if get_user.get('is_admin'):
        user = await db.scalar(select(User).where(User.id == user_id))

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='User not found'
            )

        if user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can't delete admin user"
            )

        if user.is_active:
            await db.execute(update(User).where(User.id == user_id).values(is_active=False))
            await db.commit()
            return {
                'status_code': status.HTTP_200_OK,
                'detail': 'User is deleted'
            }
        else:
            return {
                'status_code': status.HTTP_200_OK,
                'detail': 'User has already been deleted'
            }
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You don't have admin permission"
        )
