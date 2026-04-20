from pydantic import BaseModel


class VerifyRequest(BaseModel):
    """Request body for face verification endpoint."""
    id_image: str       # base64 encoded JPEG of ID document
    live_image: str     # base64 encoded JPEG of live person


class AgeRequest(BaseModel):
    """Request body for age estimation endpoint."""
    live_image: str             # base64 encoded JPEG of live person
    age_on_id: int | None = None  # manually entered by bouncer — None triggers 400


class DocumentRequest(BaseModel):
    """Request body for document authenticity endpoint."""
    id_image: str       # base64 encoded JPEG of ID document