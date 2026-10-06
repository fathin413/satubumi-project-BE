import os
import shutil

from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_admin, require_super_admin
from app.core.security import get_password_hash
from app.core.activity import create_activity_log
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, UserUpdate

# Role yang diizinkan di sistem
ALLOWED_ROLES = {"admin", "super_admin", "client", "field_officer"}


router = APIRouter(prefix="/users", tags=["User Management"])


@router.get("/", response_model=list[UserResponse])
def list_users(
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Mendapatkan daftar semua user.
    - Dapat diakses oleh **admin** dan **super_admin**.
    - Field sensitif seperti `hashed_password` tidak disertakan.
    """
    query = db.query(User)
    if role:
        query = query.filter(User.role == role)
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    return query.all()


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    user_in: UserCreate,
    db: Session = Depends(get_db),
    super_admin: User = Depends(require_super_admin),
):
    if user_in.role and user_in.role not in ALLOWED_ROLES:
        raise HTTPException(
            status_code=400,
            detail=f"Role tidak valid. Pilihan: {', '.join(ALLOWED_ROLES)}",
        )

    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email sudah terdaftar.")

    new_user = User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        full_name=user_in.full_name,
        phone_number=user_in.phone_number,
        role=user_in.role or "admin",
    )

    db.add(new_user)
    db.flush()

    create_activity_log(
        db=db,
        user=super_admin,
        action="CREATE",
        module="USER",
        target_id=new_user.id,
        target_name=new_user.full_name,
        description="Membuat akun user baru",
    )

    db.commit()
    db.refresh(new_user)

    return new_user


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Mendapatkan detail user berdasarkan ID.
    - Dapat diakses oleh **admin** dan **super_admin**.
    """
    usr = db.query(User).filter(User.id == user_id).first()
    if not usr:
        raise HTTPException(status_code=404, detail="User tidak ditemukan.")
    return usr


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    super_admin: User = Depends(require_super_admin),
):
    usr = db.query(User).filter(User.id == user_id).first()
    if not usr:
        raise HTTPException(status_code=404, detail="User tidak ditemukan.")

    if user_in.role and user_in.role not in ALLOWED_ROLES:
        raise HTTPException(
            status_code=400,
            detail=f"Role tidak valid. Pilihan: {', '.join(ALLOWED_ROLES)}",
        )

    update_data = user_in.model_dump(exclude_unset=True)

    if "email" in update_data and update_data["email"] != usr.email:
        taken = (
            db.query(User)
            .filter(User.email == update_data["email"], User.id != user_id)
            .first()
        )
        if taken:
            raise HTTPException(status_code=400, detail="Email sudah terdaftar.")

    if "password" in update_data:
        usr.hashed_password = get_password_hash(update_data.pop("password"))

    for field, value in update_data.items():
        setattr(usr, field, value)

    create_activity_log(
        db=db,
        user=super_admin,
        action="UPDATE",
        module="USER",
        target_id=usr.id,
        target_name=usr.full_name,
        description="Mengubah data user",
    )

    db.commit()
    db.refresh(usr)
    return usr


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    super_admin: User = Depends(require_super_admin),
):
    usr = db.query(User).filter(User.id == user_id).first()
    if not usr:
        raise HTTPException(status_code=404, detail="User tidak ditemukan.")

    create_activity_log(
        db=db,
        user=super_admin,
        action="DELETE",
        module="USER",
        target_id=usr.id,
        target_name=usr.full_name,
        description="Menghapus user",
    )

    db.delete(usr)
    db.commit()


@router.put("/{user_id}/profile-image")
async def upload_profile_image(
    user_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    super_admin: User = Depends(require_super_admin),
):
    usr = db.query(User).filter(User.id == user_id).first()

    if not usr:
        raise HTTPException(status_code=404, detail="User tidak ditemukan.")

    upload_dir = "static/profile"
    os.makedirs(upload_dir, exist_ok=True)

    filename = f"user_{usr.id}_{file.filename}"
    file_path = f"{upload_dir}/{filename}"

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    usr.profile_image = "/" + file_path

    create_activity_log(
        db=db,
        user=super_admin,
        action="UPLOAD",
        module="USER",
        target_id=usr.id,
        target_name=usr.full_name,
        description="Mengubah foto profil user",
    )

    db.commit()
    db.refresh(usr)

    return {"message": "Profile image updated", "profile_image": usr.profile_image}


@router.patch("/{user_id}/rapidfs-access", response_model=UserResponse)
def update_rapidfs_access(
    user_id: int,
    has_access: bool,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    """
    Mengubah hak akses eksklusif Rapid-FS untuk user tertentu.
    - Dapat diakses oleh **admin** dan **super_admin**.
    """
    usr = db.query(User).filter(User.id == user_id).first()
    if not usr:
        raise HTTPException(status_code=404, detail="User tidak ditemukan.")

    usr.has_rapidfs_access = has_access

    create_activity_log(
        db=db,
        user=admin_user,
        action="UPDATE",
        module="USER",
        target_id=usr.id,
        target_name=usr.full_name,
        description=f"{'Memberikan' if has_access else 'Mencabut'} akses Rapid-FS eksklusif",
    )

    db.commit()
    db.refresh(usr)
    return usr