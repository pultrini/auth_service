from __future__ import annotations

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from auth_service.config import settings
from auth_service.routers.auth import router as auth_router
from auth_service.routers.users import router as users_router

app = FastAPI(
    title="Auth Service",
    description="Microserviço de autenticação do Quant Dashboard",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(auth_router)
app.include_router(users_router)


@app.get("/health", tags=["infra"])
async def health() -> dict:
    return {"status": "auth service is alive"}


def run_dev() -> None:
    uvicorn.run("auth_service.app:app", host="0.0.0.0", port=8001, reload=True)


def run_prod() -> None:
    uvicorn.run("auth_service.app:app", host="0.0.0.0", port=8001, workers=2)


if __name__ == "__main__":
    run_dev()
