import logging
import os
import pysqlite3
import sys

sys.modules["sqlite3"] = pysqlite3

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

from app.api.routes import router
from app.config import settings
from app.database import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description="Serverless patent-domain RAG translation platform",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix=settings.API_PREFIX)


@app.on_event("startup")
async def startup_event():
    """Initialize local database tables when the app starts."""
    if not os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
        init_db()
    logging.info("Application started")


@app.on_event("shutdown")
async def shutdown_event():
    logging.info("Application shutting down")


# AWS Lambda container entry point.
handler = Mangum(app, lifespan="off")


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
