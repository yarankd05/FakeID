from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routes import verify

app = FastAPI(title="FakeID - Identity Verification API")

# allow frontend to talk to backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# register routes
app.include_router(verify.router, prefix="/api", tags=["Face Verification"])


@app.get("/")
def root():
    return {"status": "FakeID API is running"}