from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.routes.analytics import router as analytics_router
from app.routes.audit import router as audit_router
from app.routes.config import router as config_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": "internal_error", "message": "An unexpected error occurred"},
    )


app.include_router(analytics_router)
app.include_router(config_router)
app.include_router(audit_router)
