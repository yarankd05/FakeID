# standard library
import tempfile
from pathlib import Path

# third-party
from fastapi import APIRouter
from fastapi.responses import JSONResponse
import cv2

# local
from backend.dependencies import doc_authenticator
from backend.schemas import DocumentRequest
from backend.utils.exceptions import (
    PerspectiveCorrectionError,
    ModelInferenceError,
    InvalidImageError,
)
from backend.utils.preprocessing import decode_base64_image

router = APIRouter()


@router.post("/check-document")
def check_document(request: DocumentRequest) -> JSONResponse:
    """Check if an ID document is real or fake using MRZ verification.

    Args:
        request: DocumentRequest with id_image as base64 string and min_age.

    Returns:
        JSONResponse with success envelope and Feature 3 response shape.
    """
    if doc_authenticator is None:
        return JSONResponse(
            status_code=503,
            content={"success": False, "data": None, "error": "Model not loaded — weights file missing"},
        )

    image = None
    tmp_path = None

    try:
        image = decode_base64_image(request.id_image)

        # MRZ detector requires a file path — save to a temp file
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp_path = Path(tmp.name)
            cv2.imwrite(str(tmp_path), image)

        result = doc_authenticator.run(image, tmp_path, request.min_age)

        return JSONResponse(
            status_code=200,
            content={"success": True, "data": result, "error": None},
        )

    except (InvalidImageError, PerspectiveCorrectionError) as e:
        print(f"ERROR [doc_auth]: {str(e)} | image: {getattr(image, 'shape', 'not decoded')}")
        return JSONResponse(
            status_code=400,
            content={"success": False, "data": None, "error": str(e)},
        )
    except ModelInferenceError as e:
        print(f"ERROR [doc_auth]: {str(e)} | image: {getattr(image, 'shape', 'not decoded')}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "data": None, "error": str(e)},
        )
    finally:
        # always clean up temp file
        if tmp_path is not None and tmp_path.exists():
            tmp_path.unlink()