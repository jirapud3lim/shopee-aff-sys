from fastapi import Depends, FastAPI, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import current_user, hash_password, issue_session, token_digest, verify_password
from app.db import get_db
from app.models import Organization, OrganizationMember, SessionToken, User
from app.products import router as products_router
from app.publishing import router as publishing_router
from app.renders import router as renders_router

app = FastAPI(
    title="Shopee Affiliate Automation API",
    version="0.1.0",
    openapi_url="/api/v1/openapi.json",
    docs_url="/api/v1/docs",
)


for feature_router in (products_router, renders_router, publishing_router):
    app.include_router(feature_router)


class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=1024)


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Workspace name cannot be blank")
        return value.strip()


def _email(value: str) -> str:
    return value.strip().casefold()


@app.get("/api/v1/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok"}


@app.post("/api/v1/auth/register", status_code=status.HTTP_201_CREATED)
def register(body: Credentials, db: Session = Depends(get_db)):
    email = _email(str(body.email))
    try:
        user = User(email=email, password_hash=hash_password(body.password))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    db.add(user)
    try:
        db.flush()
        org = Organization(name="My workspace")
        db.add(org)
        db.flush()
        db.add(OrganizationMember(organization_id=org.id, user_id=user.id, role="owner"))
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="An account with this email already exists"
        ) from exc
    return {"token": issue_session(db, user.id)}


@app.post("/api/v1/auth/login")
def login(body: Credentials, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == _email(str(body.email))))
    if user is None or not user.is_active or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return {"token": issue_session(db, user.id)}


@app.post("/api/v1/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)):
    bearer = request.headers.get("authorization", "").partition(" ")[2]
    row = db.get(SessionToken, token_digest(bearer))
    if row is not None and row.user_id == user.id:
        db.delete(row)
        db.commit()
    return None


@app.get("/api/v1/workspaces")
def list_workspaces(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.execute(
        select(Organization, OrganizationMember.role)
        .join(OrganizationMember, OrganizationMember.organization_id == Organization.id)
        .where(OrganizationMember.user_id == user.id)
        .order_by(Organization.created_at)
    ).all()
    return [{"id": org.id, "name": org.name, "role": role} for org, role in rows]


@app.post("/api/v1/workspaces", status_code=status.HTTP_201_CREATED)
def create_workspace(
    body: WorkspaceCreate, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    org = Organization(name=body.name.strip())
    db.add(org)
    db.flush()
    db.add(OrganizationMember(organization_id=org.id, user_id=user.id, role="owner"))
    db.commit()
    return {"id": org.id, "name": org.name, "role": "owner"}
