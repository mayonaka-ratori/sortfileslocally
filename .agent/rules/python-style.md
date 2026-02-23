# Python Style Guidelines

Follow these patterns for Python development in this project.

## Imports
- Use **relative imports** when importing from the same sub-package (e.g., within `src.core`).
- Use **absolute imports** when importing from other top-level packages or the project root.

### Examples
✅ `from .scanner import Scanner` (inside `src/core/processor.py`)
✅ `from src.data.db_manager import DBManager`
❌ `from ..data.db_manager import DBManager` (if absolute path is clearer)

## FastAPI Routers
- Always use `APIRouter` with explicit prefixes and tags.
- Define request/response schemas using Pydantic.

### Example
```python
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/example", tags=["example"])

class ExampleRequest(BaseModel):
    name: str

@router.post("/run")
async def run_example(req: ExampleRequest):
    return {"message": f"Hello {req.name}"}
```

## Naming Conventions
- Variables/Functions: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
