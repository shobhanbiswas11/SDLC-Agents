"""
FastAPI Application Entry Point
---------------------------------
Registers all routers and middleware.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as api_router
from app.api.ws import router as ws_router
from app.api.hitl_routes import router as hitl_router

app = FastAPI(
    title="Build Orchestration Agent",
    description="AI-powered build failure diagnosis and fix system with human-in-the-loop approval.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
app.include_router(ws_router)
app.include_router(hitl_router)