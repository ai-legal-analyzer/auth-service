from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.backend.db import Base


class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    first_name: Mapped[str] = mapped_column(String(50), index=True)
    last_name: Mapped[str] = mapped_column(String(50), index=True)
    username: Mapped[str] = mapped_column(
        String(30),
        unique=True,
        index=True,
        doc='Unique username for login'
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        doc="Users email address"
    )
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(default=True)
    is_admin: Mapped[bool] = mapped_column(default=False)
    is_verified: Mapped[bool] = mapped_column(default=False)

    def __repr__(self):
        return f'<User(id={self.id}, username={self.username}, email={self.email})>'
