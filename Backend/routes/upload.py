from fastapi import APIRouter, Depends, UploadFile, File
from utils.dependencies import get_current_user
from services.upload import UploadService

router = APIRouter(prefix="/api/v1/upload", tags=["Upload"])


@router.post("")
async def upload_file(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    user_id = str(current_user["_id"])
    result = await UploadService.save_file(file, user_id)
    return result


@router.get("")
async def list_files(
    current_user: dict = Depends(get_current_user),
):
    user_id = str(current_user["_id"])
    files = UploadService.list_files(user_id)
    return {"files": files, "total": len(files)}
