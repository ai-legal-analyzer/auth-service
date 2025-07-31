from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Integer
from sqlalchemy.orm import mapped_column, Mapped

from app.backend.db import Base

class RevokedToken(Base):
    __tablename__ = 'revoked_tokens'

    jti: Mapped[str] = mapped_column(String(30), primary_key=True)
    revoked_at = mapped_column(DateTime, default=datetime.now(timezone.utc))
    user_id: Mapped[int] = mapped_column(Integer)

