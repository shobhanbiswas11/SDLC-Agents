"""
Cross-cutting router — exposes the service-level health endpoints and acts as
the place to mount additional agent routers in the future.
"""
from __future__ import annotations

from fastapi import APIRouter

core_router = APIRouter(tags=["Health"])


@core_router.get("/")
async def root():
    return {
        "service": "Coding Standards Enforcer",
        "version": "0.2.0",
        "status": "running",
        "docs": "/docs",
    }


@core_router.get("/health")
async def health():
    return {"status": "healthy"}
