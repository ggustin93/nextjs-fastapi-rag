# Docker Container Python Import Fix

## Problem Summary

**Error**: FastAPI backend fails to start in Docker with:
```
ModuleNotFoundError: No module named 'app'
File "/app/services/api/app/main.py", line 30, in <module>
    from app.api import chat, documents, health, system
```

## Root Cause

The issue was with how uvicorn was being invoked in the Docker container:

**Previous configuration**:
- `WORKDIR /app/services/api` (line 60)
- `PYTHONPATH=/app/services/api:/app` (line 65)
- `CMD ["uvicorn", "app.main:app", ...]` (line 79)

**The problem**:
When changing `WORKDIR` to `/app/services/api` and running `uvicorn app.main:app`, Python needs to be able to import both:
1. The `app` module from `/app/services/api/app/`
2. The `packages` module from `/app/packages/`

While PYTHONPATH was set correctly, running uvicorn with the relative module path `app.main:app` from a changed WORKDIR can cause import resolution issues in Docker.

## Solution

Keep `WORKDIR /app` and use the full module path for uvicorn:

**New configuration** (deploy/backend.Dockerfile):
```dockerfile
# WORKDIR stays at /app (no change from line 46)
WORKDIR /app

# Set PYTHONPATH with both paths
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app:/app/services/api \
    PORT=8000

# Run uvicorn with full module path from /app
CMD ["uvicorn", "services.api.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Key changes**:
1. **Removed** the `WORKDIR /app/services/api` directive
2. **Updated** `PYTHONPATH` order to `/app:/app/services/api` (prioritize project root)
3. **Changed** uvicorn command from `app.main:app` to `services.api.app.main:app`

## Why This Works

1. **WORKDIR /app**: Keeps working directory at project root
2. **PYTHONPATH=/app:/app/services/api**:
   - `/app` allows imports like `from packages.config import ...`
   - `/app/services/api` is included but not needed with full module path
3. **Full module path**: `services.api.app.main:app` is unambiguous from `/app`

## Verification

### Local Development (Unchanged)
Local development continues to work as before:
- Runs from `services/api/` directory
- Sets `PYTHONPATH="${PROJECT_ROOT}:${PYTHONPATH:-}"`
- Executes `uvicorn app.main:app`

### Docker Build Test
```bash
# Build the Docker image
docker build -f deploy/backend.Dockerfile -t rag-backend:test .

# Run the container
docker run -p 8000:8000 \
  -e SUPABASE_URL=your_url \
  -e SUPABASE_SERVICE_KEY=your_key \
  -e OPENAI_API_KEY=your_key \
  rag-backend:test

# Check health endpoint
curl http://localhost:8000/health
```

Expected output:
```json
{"status": "healthy"}
```

## Import Structure Reference

The import structure in `main.py` requires:

```python
# Line 30 - Requires /app/services/api in Python path
from app.api import chat, documents, health, system

# Line 32 - Requires /app in Python path
from packages.config import settings
```

With the full module path `services.api.app.main:app`:
- Python resolves the module from `/app/services/api/app/main.py`
- Internal imports work because both `/app` and `/app/services/api` are in PYTHONPATH

## Files Changed

- `deploy/backend.Dockerfile`: Lines 56-77 modified

## Testing Checklist

- [ ] Docker build succeeds
- [ ] Container starts without import errors
- [ ] Health endpoint returns 200
- [ ] Chat endpoint accepts requests
- [ ] Local development still works
- [ ] CI/CD pipeline passes
