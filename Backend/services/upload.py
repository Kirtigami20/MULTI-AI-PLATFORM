import os
import uuid
from fastapi import UploadFile, HTTPException, status
from config import settings

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".docx"}


class UploadService:

    @staticmethod
    def _user_dir(user_id: str) -> str:
        path = os.path.join(settings.UPLOAD_DIR, user_id)
        os.makedirs(path, exist_ok=True)
        return path

    @staticmethod
    async def save_file(file: UploadFile, user_id: str) -> dict:
        ext = os.path.splitext(file.filename)[1].lower()

        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type '{ext}' not allowed. Supported: {', '.join(ALLOWED_EXTENSIONS)}",
            )

        content = await file.read()
        size_mb = len(content) / (1024 * 1024)

        if size_mb > settings.MAX_FILE_SIZE_MB:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File too large. Max size: {settings.MAX_FILE_SIZE_MB}MB",
            )

        user_dir = UploadService._user_dir(user_id)

        file_id = str(uuid.uuid4())
        filename = f"{file_id}{ext}"
        file_path = os.path.join(user_dir, filename)

        with open(file_path, "wb") as f:
            f.write(content)

        return {
            "file_id": file_id,
            "filename": file.filename,
            "saved_as": filename,
            "path": file_path,
            "size_mb": round(size_mb, 2),
            "extension": ext,
        }

    @staticmethod
    def list_files(user_id: str) -> list[dict]:
        user_dir = os.path.join(settings.UPLOAD_DIR, user_id)
        if not os.path.exists(user_dir):
            return []

        files = []
        for fname in os.listdir(user_dir):
            fpath = os.path.join(user_dir, fname)
            if os.path.isfile(fpath):
                ext = os.path.splitext(fname)[1].lower()
                file_id = os.path.splitext(fname)[0]
                size_mb = round(os.path.getsize(fpath) / (1024 * 1024), 2)
                files.append({
                    "file_id": file_id,
                    "filename": f"{file_id}{ext}",
                    "size_mb": size_mb,
                    "extension": ext,
                })
        return files

    @staticmethod
    def get_file_path(filename: str, user_id: str) -> str:
        path = os.path.join(settings.UPLOAD_DIR, user_id, filename)
        if not os.path.exists(path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found",
            )
        return path

    @staticmethod
    def delete_file(filename: str, user_id: str):
        path = os.path.join(settings.UPLOAD_DIR, user_id, filename)
        if os.path.exists(path):
            os.remove(path)
