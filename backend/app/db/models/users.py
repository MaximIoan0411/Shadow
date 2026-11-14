"""Echipajul, conturile și tokenurile revocate."""
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base, UTCDateTime


class Crew(Base):
    """Un membru al echipajului. 4 rânduri, din seed. id = "cm-1" … "cm-4"."""

    __tablename__ = "crew"
    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(80))
    initials: Mapped[str] = mapped_column(String(4))
    role_title: Mapped[str] = mapped_column(String(80))
    is_cmo: Mapped[bool] = mapped_column(Boolean, default=False)


class User(Base):
    """Un cont. Câte unul pe astronaut + contul `earth`. Parola doar ca hash (security.passwords)."""

    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(16), primary_key=True)                 # "u-cm-2", "u-earth"
    username: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(80))
    initials: Mapped[str] = mapped_column(String(4))
    role: Mapped[str] = mapped_column(String(12))                                  # astronaut | cmo | earth
    crew_id: Mapped[str | None] = mapped_column(ForeignKey("crew.id"), nullable=True)  # None doar pentru earth


class RevokedToken(Base):
    """Tokenurile ieșite prin logout, până la expirare (security.tokens.revoke / is_revoked)."""

    __tablename__ = "revoked_tokens"
    jti: Mapped[str] = mapped_column(String(64), primary_key=True)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime)
