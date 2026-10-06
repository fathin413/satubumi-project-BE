import os
import shutil

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.activity import create_activity_log
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    verify_password,
)
from app.models.user import User
from app.schemas.user import ProfileUpdate, Token, UserCreate, UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
oauth2_scheme_optional = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login", auto_error=False
)


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    email: str = payload.get("sub")
    if email is None:
        raise credentials_exception
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    return user


def get_current_user_optional(
    token: str | None = Depends(oauth2_scheme_optional), db: Session = Depends(get_db)
) -> User | None:
    if not token:
        return None
    payload = decode_access_token(token)
    if payload is None:
        return None
    email: str = payload.get("sub")
    if email is None:
        return None
    return db.query(User).filter(User.email == email).first()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_211_CREATED if False else status.HTTP_201_CREATED,
)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == user_in.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email sudah terdaftar.")

    hashed_pwd = get_password_hash(user_in.password)
    new_user = User(
        email=user_in.email,
        hashed_password=hashed_pwd,
        full_name=user_in.full_name,
        phone_number=user_in.phone_number,
        role=user_in.role or "client",
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    email = form_data.username
    password = form_data.password

    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Email atau password salah.")

    access_token = create_access_token(subject=user.email)
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/me", response_model=UserResponse)
@router.patch("/me", response_model=UserResponse)
def update_me(
    profile_in: ProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Mengupdate profil diri sendiri (nama, nomor telepon, email, password).
    Role dan status akses tidak dapat diubah oleh user itu sendiri.
    """
    update_data = profile_in.model_dump(exclude_unset=True)

    if "email" in update_data and update_data["email"] != current_user.email:
        taken = (
            db.query(User)
            .filter(User.email == update_data["email"], User.id != current_user.id)
            .first()
        )
        if taken:
            raise HTTPException(status_code=400, detail="Email sudah terdaftar.")
        current_user.email = update_data["email"]

    if "password" in update_data and update_data["password"]:
        current_user.hashed_password = get_password_hash(update_data["password"])

    if "full_name" in update_data:
        current_user.full_name = update_data["full_name"]

    if "phone_number" in update_data:
        current_user.phone_number = update_data["phone_number"]

    create_activity_log(
        db=db,
        user=current_user,
        action="UPDATE",
        module="USER",
        target_id=current_user.id,
        target_name=current_user.full_name,
        description="User memperbarui profil sendiri",
    )

    db.commit()
    db.refresh(current_user)
    return current_user


@router.put("/me/profile-image")
@router.post("/me/profile-image")
async def upload_my_profile_image(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Mengunggah foto profil untuk akun diri sendiri.
    """
    upload_dir = "static/profile"
    os.makedirs(upload_dir, exist_ok=True)

    filename = f"user_{current_user.id}_{file.filename}"
    file_path = f"{upload_dir}/{filename}"

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    current_user.profile_image = "/" + file_path

    create_activity_log(
        db=db,
        user=current_user,
        action="UPLOAD",
        module="USER",
        target_id=current_user.id,
        target_name=current_user.full_name,
        description="User memperbarui foto profil sendiri",
    )

    db.commit()
    db.refresh(current_user)
    return {"message": "Profile image updated", "profile_image": current_user.profile_image}
