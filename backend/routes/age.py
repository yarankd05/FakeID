#third-party
from fastapi import APIRouter
from fastapi.responses import JSONResponse

#local
from backend.dependencies import age_estimator
from backend.schemas import AgeRequest
from backend.utils.exceptions import FaceNotDetectedError, ModelInferenceError, InvalidImageError
from backend.utils.preprocessing import decode_base64_image

router = APIRouter()


@router.post("/estimate-age")
def estimate_age(request: AgeRequest):
    """
    Estimate age from a live photo and check consistency with ID age.

    Args:
        request: AgeRequest with live_image as base64 string and age_on_id as int

    Returns:
        JSONResponse with success envelope and Feature 2 response shape
    """
    if age_estimator is None:
        return JSONResponse(
            status_code=503,
            content={"success": False, "data": None, "error": "Model not loaded — weights file missing"}
        )

    if request.age_on_id is None:
        return JSONResponse(
            status_code=400,
            content={"success": False, "data": None, "error": "Missing required field: age_on_id"}
        )

    live_image = None

    try:
        live_image = decode_base64_image(request.live_image)

        result = age_estimator.run(live_image, request.age_on_id)

        return JSONResponse(
            status_code=200,
            content={"success": True, "data": result, "error": None}
        )

    except FaceNotDetectedError as e:
        print(f"ERROR [age_estimation]: {str(e)} | image: {getattr(live_image, 'shape', 'not decoded')}")
        return JSONResponse(
            status_code=400,
            content={"success": False, "data": None, "error": str(e)}
        )

    except (ModelInferenceError, InvalidImageError) as e:
        print(f"ERROR [age_estimation]: {str(e)} | image: {getattr(live_image, 'shape', 'not decoded')}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "data": None, "error": str(e)}
        )