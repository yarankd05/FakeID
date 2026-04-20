from fastapi import APIRouter, UploadFile, File
import shutil
import os
import uuid
from backend.models.face_verify import verify_faces

router = APIRouter()

TEMP_DIR = "temp_images"
os.makedirs(TEMP_DIR, exist_ok=True)


@router.post("/verify-face")
async def verify_face(
    id_image: UploadFile = File(...),
    live_image: UploadFile = File(...)
):
    # generate unique filenames to avoid conflicts between requests
    id_path = f"{TEMP_DIR}/{uuid.uuid4()}_id.jpg"
    live_path = f"{TEMP_DIR}/{uuid.uuid4()}_live.jpg"

    try:
        # save uploaded files temporarily
        with open(id_path, "wb") as f:
            shutil.copyfileobj(id_image.file, f)
        with open(live_path, "wb") as f:
            shutil.copyfileobj(live_image.file, f)

        # run verification
        result = verify_faces(id_path, live_path)

        return {
            "success": True,
            "data": result,
            "error": None
        }

    except Exception as e:
        return {
            "success": False,
            "data": None,
            "error": str(e)
        }

    finally:
        # always clean up temp files even if something fails
        if os.path.exists(id_path):
            os.remove(id_path)
        if os.path.exists(live_path):
            os.remove(live_path)