import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import chat, company_profile, conversations, diagnosis, documents, experts, memory, rag, homework
from database import Base, engine
import models  # noqa: F401
from seed import seed_demo_data

default_origins = ["http://localhost:3000"]
cors_origins = os.getenv("CORS_ORIGINS")
origins = [origin.strip() for origin in cors_origins.split(",")] if cors_origins else default_origins

app = FastAPI(title="Yorizo API", version="0.1.0")


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    seed_demo_data()


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(conversations.router, prefix="/api", tags=["conversations"])
app.include_router(company_profile.router, prefix="/api", tags=["company-profile"])
app.include_router(diagnosis.router, prefix="/api", tags=["diagnosis"])
app.include_router(memory.router, prefix="/api", tags=["memory"])
app.include_router(rag.router, prefix="/api", tags=["rag"])
app.include_router(documents.router, prefix="/api", tags=["documents"])
app.include_router(experts.router, prefix="/api", tags=["experts"])
app.include_router(homework.router, prefix="/api", tags=["homework"])


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
