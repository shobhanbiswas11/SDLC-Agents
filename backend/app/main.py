from fastapi import FastAPI
from app.routes import chat, generate, download
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Code Generator Agent")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/chat", tags=["Chat"])
app.include_router(generate.router, prefix="/generate", tags=["Generate"])
app.include_router(download.router, prefix="/download", tags=["Download"])


@app.get("/")
async def health():
    return {"status": "ok"}