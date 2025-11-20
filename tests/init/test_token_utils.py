# tests/unit/test_token_utils.py
import pytest
from datetime import timedelta
from app.routers.auth import create_access_token, create_refresh_token
import jwt


class TestTokenCreation:

    @pytest.mark.asyncio
    async def test_create_access_token_structure(self):
        # Act
        token = await create_access_token(
            username="testuser",
            user_id=1,
            is_admin=False,
            is_verified=True,
            expires_delta=timedelta(minutes=20)
        )

        # Assert
        assert isinstance(token, str)
        assert len(token) > 0

        # Декодируем без проверки подписи для проверки структуры
        payload = jwt.decode(token, options={"verify_signature": False})

        assert payload['sub'] == 'testuser'
        assert payload['id'] == 1
        assert payload['is_admin'] is False
        assert payload['is_verified'] is True
        assert 'exp' in payload

    @pytest.mark.asyncio
    async def test_create_refresh_token_has_jti(self):
        # Act
        token = await create_refresh_token(
            username="testuser",
            user_id=1,
            expires_delta=timedelta(days=7)
        )

        # Assert
        payload = jwt.decode(token, options={"verify_signature": False})

        assert payload['type'] == 'refresh'
        assert 'jti' in payload
        assert len(payload['jti']) > 0  # UUID должен быть не пустым