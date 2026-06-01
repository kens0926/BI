from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import current_user
from ..models import Role, User
from ..schemas import ApiResponse, TokenResponse, UserCreate, UserRead, UserUpdate
from ..security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.account == form.username).first()
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect account or password")
    return TokenResponse(access_token=create_access_token(user.id), user=user)


@router.get("/me", response_model=UserRead)
def me(user: User = Depends(current_user)):
    return user


@router.post("/users", response_model=ApiResponse)
def create_user(payload: UserCreate, db: Session = Depends(get_db), user: User = Depends(current_user)):
    if user.role != Role.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only Admin can create users")
    if db.query(User).filter(User.account == payload.account).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Account already exists")
    created = User(
        account=payload.account,
        password_hash=hash_password(payload.password),
        name=payload.name,
        role=payload.role,
    )
    db.add(created)
    db.commit()
    db.refresh(created)
    return ApiResponse(message="User created", data=UserRead.model_validate(created))


@router.get("/users", response_model=ApiResponse)
def list_users(db: Session = Depends(get_db), user: User = Depends(current_user)):
    if user.role != Role.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only Admin can maintain users")
    rows = db.query(User).order_by(User.created_at.desc()).all()
    return ApiResponse(message="Data retrieved successfully", data=[UserRead.model_validate(row) for row in rows])


@router.put("/users/{user_id}", response_model=ApiResponse)
def update_user(
    user_id: str,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    if user.role != Role.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only Admin can maintain users")
    row = db.get(User, user_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    update_data = payload.model_dump(exclude_unset=True)
    if update_data.get("password"):
        row.password_hash = hash_password(update_data.pop("password"))
    elif "password" in update_data:
        update_data.pop("password")
    for key, value in update_data.items():
        setattr(row, key, value)

    db.commit()
    db.refresh(row)
    return ApiResponse(message="User updated", data=UserRead.model_validate(row))
