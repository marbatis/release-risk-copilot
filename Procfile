release: python -c "from app.db import init_db; init_db()"
web: uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
