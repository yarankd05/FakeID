#standard library
import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

#local
from backend.routes import verify, age, document

app = FastAPI(title="FakeID — Identity Verification API")

#allow frontend to talk to backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#register all three feature routes
app.include_router(verify.router, prefix="/api", tags=["Feature 1 — Face Verification"])
app.include_router(age.router, prefix="/api", tags=["Feature 2 — Age Estimation"])
app.include_router(document.router, prefix="/api", tags=["Feature 3 — Document Authenticity"])

#serve frontend static files
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(_file_)))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "frontend")), name="static")


@app.get("/")
def serve_frontend():
    """serve the frontend single page app."""
    return FileResponse(os.path.join(BASE_DIR, "frontend", "index.html"))


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """catch any unhandled exceptions and return our standard error envelope."""
    print(f"UNHANDLED ERROR on {request.url}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"success": False, "data": None, "error": "Unexpected server error"}
    )