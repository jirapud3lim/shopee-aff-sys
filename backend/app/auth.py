import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Annotated

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import OrganizationMember, SessionToken, User

password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    if len(password) < get_settings().password_min_length:
        raise ValueError(
            f"Password must be at least {get_settings().password_min_length} characters"
        )
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def issue_session(db: Session, user_id: str) -> str:
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(days=get_settings().session_ttl_days)
    db.add(SessionToken(token_hash=token_digest(token), user_id=user_id, expires_at=expires))
    db.commit()
    return token


def current_user(request: Request, db: Annotated[Session, Depends(get_db)]) -> User:
    authorization = request.headers.get("authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        )
    row = db.scalar(select(SessionToken).where(SessionToken.token_hash == token_digest(token)))
    now = datetime.now(timezone.utc)
    if row is None or _as_utc(row.expires_at) <= now:
        if row is not None:
            db.delete(row)
            db.commit()
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    user = db.get(User, row.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return user


def _as_utc(value: datetime) -> datetime:
    return (
        value.replace(tzinfo=timezone.utc)
        if value.tzinfo is None
        else value.astimezone(timezone.utc)
    )


@dataclass(frozen=True)
class WorkspaceContext:
    workspace_id: str
    user_id: str
    role: str


def require_workspace(
    workspace_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(current_user)],
) -> WorkspaceContext:
    member = db.scalar(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == str(workspace_id),
            OrganizationMember.user_id == user.id,
        )
    )
    if member is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return WorkspaceContext(workspace_id=str(workspace_id), user_id=user.id, role=member.role)
