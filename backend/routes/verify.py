#third-party
from fastapi import APIRouter
from fastapi.responses import JSONResponse

#local
from backend.dependencies import face_verifier
from backend.schemas import VerifyRequest
from backend.utils.exceptions import FaceNotDetectedError, ModelInferenceError, InvalidImageError
from backend.utils.preprocessing import decode_base64_image

router = APIRouter()


@router.post("/verify-face")
def verify_face(request: VerifyRequest):
    """
    Verify if the face in an ID photo matches a live photo.

    Args:
        request: VerifyRequest with id_image and live_image as base64 strings

    Returns:
        JSONResponse with success envelope and Feature 1 response shape
    """
    if face_verifier is None:
        return JSONResponse(
            status_code=503,
            content={"success": False, "data": None, "error": "Model not loaded — weights file missing"}
        )

    try:
        id_image = decode_base64_image(request.id_image)
        live_image = decode_base64_image(request.live_image)

        result = face_verifier.run(id_image, live_image)

        return JSONResponse(
            status_code=200,
            content={"success": True, "data": result, "error": None}
        )

    except FaceNotDetectedError as e:
        print(f"ERROR [face_verify]: {str(e)} | image: {getattr(id_image, 'shape', 'not decoded')}")
        return JSONResponse(
            status_code=400,
            content={"success": False, "data": None, "error": str(e)}
        )

    except (ModelInferenceError, InvalidImageError) as e:
        print(f"ERROR [face_verify]: {str(e)} | image: {getattr(id_image, 'shape', 'not decoded')}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "data": None, "error": str(e)}
        )