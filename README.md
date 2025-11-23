# Yorizo Backend (FastAPI)

## Setup
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

## Migrations
We use Alembic.
```bash
cd backend
alembic upgrade head  # uses DATABASE_URL (falls back to sqlite:///./yorizo.db)
```

## Run
```bash
uvicorn main:app --reload --port 8000
# http://localhost:8000/docs でAPI確認
```

## Environment variables
- `DATABASE_URL`: full SQLAlchemy URL (optional; overrides DB_*), e.g. `sqlite:///./yorizo.db` or `mysql+pymysql://user:pass@host:3306/yorizo`  
  - If you supply an async driver (e.g., `mysql+asyncmy` or `sqlite+aiosqlite`), it will be normalized to a sync driver for the current engine.
- `DB_HOST`: default `localhost`
- `DB_PORT`: default `3306`
- `DB_USERNAME`: use this instead of a reserved `username` key in Azure App Service
- `DB_PASSWORD`
- `DB_NAME`
- `OPENAI_API_KEY`: OpenAI key
- `OPENAI_MODEL_CHAT`: default `gpt-4.1-mini`
- `OPENAI_MODEL_EMBEDDING`: default `text-embedding-3-small`
- `CORS_ORIGINS`: CSV of allowed origins (default `http://localhost:3000`)
