# standard library

# third-party
from fastapi import APIRouter
from fastapi.responses import JSONResponse

# local
from backend.dependencies import doc_authenticator
from backend.schemas import DocumentRequest
from backend.utils.exceptions import (
    PerspectiveCorrectionError,
    ModelInferenceError,
    InvalidImageError
)
from backend.utils.preprocessing import decode_base64_image

router = APIRouter()


@router.post("/check-document")
def check_document(request: DocumentRequest):
    """
    Check if an ID document is real or fake.

    Args:
        request: DocumentRequest with id_image as base64 string

    Returns:
        JSONResponse with success envelope and Feature 3 response shape
    """
    if doc_authenticator is None:
        return JSONResponse(
            status_code=503,
            content={"success": False, "data": None, "error": "Model not loaded — weights file missing"}
        )
    try:
        image = None
        image = decode_base64_image(request.id_image)
        result = doc_authenticator.run(image)
        return JSONResponse(
            status_code=200,
            content={"success": True, "data": result, "error": None}
        )
    except (InvalidImageError, PerspectiveCorrectionError) as e:
        print(f"ERROR [doc_auth]: {str(e)} | image: {getattr(image, 'shape', 'not decoded')}")
        return JSONResponse(
            status_code=400,
            content={"success": False, "data": None, "error": str(e)}
        )
    except ModelInferenceError as e:
        print(f"ERROR [doc_auth]: {str(e)} | image: {getattr(image, 'shape', 'not decoded')}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "data": None, "error": str(e)}
        )