import os

from dotenv import load_dotenv
from supabase import Client, create_client


load_dotenv()


def get_supabase_client() -> Client:
    url = os.getenv("SUPABASE_URL")
    secret_key = os.getenv("SUPABASE_SECRET_KEY")

    if not url:
        raise RuntimeError(
            "SUPABASE_URL belum dikonfigurasi."
        )

    if not secret_key:
        raise RuntimeError(
            "SUPABASE_SECRET_KEY belum dikonfigurasi."
        )

    return create_client(
        url,
        secret_key,
    )


def get_public_bucket() -> str:
    return os.getenv(
        "SUPABASE_PUBLIC_BUCKET",
        "satubumi-public",
    )


import io
import os

from dotenv import load_dotenv
from PIL import Image, ImageOps
from supabase import Client, create_client


load_dotenv()


def get_supabase_client() -> Client:
    url = os.getenv("SUPABASE_URL")
    secret_key = os.getenv("SUPABASE_SECRET_KEY")

    if not url:
        raise RuntimeError(
            "SUPABASE_URL belum dikonfigurasi."
        )

    if not secret_key:
        raise RuntimeError(
            "SUPABASE_SECRET_KEY belum dikonfigurasi."
        )

    return create_client(
        url,
        secret_key,
    )


def get_public_bucket() -> str:
    return os.getenv(
        "SUPABASE_PUBLIC_BUCKET",
        "satubumi-public",
    )


def optimize_image(
    file_bytes: bytes,
    content_type: str,
    max_dimension: int = 1920,
    quality: int = 82,
) -> tuple[bytes, str]:
    """
    Optimizes JPEG, PNG, WEBP images before storage upload to avoid Supabase Egress bloat.
    - Preserves aspect ratio with max dimension (default 1920px).
    - Auto-orients based on EXIF tag.
    - Compresses raw camera photos (often 3-6 MB) down to 150-300 KB without perceptible loss.
    """
    if content_type not in {"image/jpeg", "image/png", "image/webp"}:
        return file_bytes, content_type

    try:
        with Image.open(io.BytesIO(file_bytes)) as img:
            img = ImageOps.exif_transpose(img)
            w, h = img.size
            if w > max_dimension or h > max_dimension:
                img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)

            out_io = io.BytesIO()
            if content_type == "image/png":
                if img.mode in ("RGBA", "LA", "P"):
                    img.save(out_io, format="PNG", optimize=True)
                    optimized = out_io.getvalue()
                    return (optimized, content_type) if len(optimized) < len(file_bytes) else (file_bytes, content_type)
                else:
                    img = img.convert("RGB")
                    img.save(out_io, format="JPEG", quality=quality, optimize=True)
                    optimized = out_io.getvalue()
                    return (optimized, "image/jpeg") if len(optimized) < len(file_bytes) else (file_bytes, content_type)
            elif content_type == "image/jpeg":
                if img.mode != "RGB":
                    img = img.convert("RGB")
                img.save(out_io, format="JPEG", quality=quality, optimize=True)
                optimized = out_io.getvalue()
                return (optimized, "image/jpeg") if len(optimized) < len(file_bytes) else (file_bytes, content_type)
            elif content_type == "image/webp":
                img.save(out_io, format="WEBP", quality=quality, method=4)
                optimized = out_io.getvalue()
                return (optimized, "image/webp") if len(optimized) < len(file_bytes) else (file_bytes, content_type)
    except Exception:
        # Fall back gracefully to original if Pillow encounters any unhandled stream/format
        return file_bytes, content_type

    return file_bytes, content_type


def upload_public_file(
    path: str,
    file_bytes: bytes,
    content_type: str,
) -> str:
    supabase = get_supabase_client()
    bucket = get_public_bucket()

    # Automatic image optimization to prevent egress and bandwidth spikes
    file_bytes, content_type = optimize_image(file_bytes, content_type)

    supabase.storage.from_(bucket).upload(
        path=path,
        file=file_bytes,
        file_options={
            "content-type": content_type,
            "cache-control": "public, max-age=31536000, immutable",
            "upsert": "false",
        },
    )

    public_url = (
        supabase.storage
        .from_(bucket)
        .get_public_url(path)
    )

    return public_url


def delete_public_file(
    path: str,
) -> None:
    supabase = get_supabase_client()
    bucket = get_public_bucket()

    supabase.storage.from_(bucket).remove(
        [path]
    )


def extract_public_storage_path(
    file_url: str | None,
) -> str | None:
    if not file_url:
        return None

    bucket = get_public_bucket()

    marker = (
        f"/storage/v1/object/public/"
        f"{bucket}/"
    )

    if marker not in file_url:
        return None

    return file_url.split(
        marker,
        1,
    )[1]