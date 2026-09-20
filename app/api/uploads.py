"""Upload and upload-status API routes."""

from __future__ import annotations

import tempfile
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile, status

from app.db import repository
from app.db.models import Upload
from app.ingestion.pipeline import process_upload


router = APIRouter(tags=["uploads"])
UPLOAD_DIRECTORY = Path(tempfile.gettempdir()) / "finpilot-uploads"
MAX_UPLOAD_BYTES = 25 * 1024 * 1024
SUPPORTED_EXTENSIONS = {".pdf", ".csv", ".xlsx", ".jpg", ".jpeg", ".png"}
_MAGIC_TYPES = ((b"%PDF", "application/pdf"), (b"\xff\xd8\xff", "image/jpeg"), (b"\x89PNG\r\n\x1a\n", "image/png"))
_EXPECTED_TYPES = {".pdf": "application/pdf", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}


def _sniff_content_type(prefix: bytes) -> str | None:
    for magic, content_type in _MAGIC_TYPES:
        if prefix.startswith(magic):
            return content_type
    return None


def _upload_response(upload: Upload) -> dict[str, object]:
    return {
        "upload_id": str(upload.id),
        "filename": upload.filename,
        "status": upload.status,
        "row_count": upload.row_count,
        "error_message": upload.error_message,
        "flagged_rows": upload.flagged_rows or [],
    }


@router.post("/uploads", status_code=status.HTTP_202_ACCEPTED)
async def create_upload(
    background_tasks: BackgroundTasks,
    user_id: str,
    file: UploadFile = File(...),
) -> dict[str, str]:
    filename = Path(file.filename or "").name
    suffix = Path(filename).suffix.lower()
    if not filename or suffix not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="unsupported file extension")

    prefix = await file.read(16)
    sniffed_content_type = _sniff_content_type(prefix)
    expected_type = _EXPECTED_TYPES.get(suffix)
    if expected_type is not None and sniffed_content_type != expected_type:
        raise HTTPException(status_code=400, detail="file content does not match its extension")
    # Text and spreadsheet formats use extension fallback in the dispatcher.
    sniffed_content_type = sniffed_content_type or "application/octet-stream"

    UPLOAD_DIRECTORY.mkdir(parents=True, exist_ok=True)
    destination = UPLOAD_DIRECTORY / f"upload-{uuid4()}{suffix}"
    bytes_written = 0
    try:
        with destination.open("wb") as output:
            for chunk in (prefix,):
                bytes_written += len(chunk)
                if bytes_written > MAX_UPLOAD_BYTES:
                    raise HTTPException(status_code=413, detail="file exceeds 25 MB limit")
                output.write(chunk)
            while chunk := await file.read(1024 * 1024):
                bytes_written += len(chunk)
                if bytes_written > MAX_UPLOAD_BYTES:
                    raise HTTPException(status_code=413, detail="file exceeds 25 MB limit")
                output.write(chunk)
    except HTTPException:
        destination.unlink(missing_ok=True)
        raise
    except OSError as error:
        destination.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"could not store upload: {error}") from error
    finally:
        await file.close()

    upload = await repository.create_upload(filename, sniffed_content_type)
    background_tasks.add_task(
        process_upload,
        upload.id,
        destination,
        sniffed_content_type,
        user_id,
    )
    return {"upload_id": str(upload.id), "filename": upload.filename, "status": upload.status}


@router.get("/uploads/{upload_id}")
async def get_upload(upload_id: UUID) -> dict[str, object]:
    async with repository.async_session_factory() as session:
        upload = await session.get(Upload, upload_id)
    if upload is None:
        raise HTTPException(status_code=404, detail="upload not found")
    return _upload_response(upload)
