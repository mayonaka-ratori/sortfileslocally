# Test Organization Guide

## Current State

All tests are in `tests/` directory (flat structure).

## Target State (Gradual Migration)

New tests should be placed next to the module they test:

src/core/
├── ai_models.py
├── ai_models_test.py    ← unit tests for ai_models
├── whisper_worker.py
└── whisper_worker_test.py

src/data/
├── db_manager.py
└── db_manager_test.py

server/routers/
├── scan.py
└── scan_test.py

tests/                   ← integration & cross-module tests remain here
├── test_inference_accuracy.py ← GPU integration test
├── test_sqlite_stress.py      ← stress test
└── conftest.py                ← shared fixtures

## Naming Convention

- Module-adjacent tests: `{module_name}_test.py`
- Integration tests (tests/ dir): `test_{feature}.py`

## Running Tests

```bash
# All tests
python -m pytest -v

# Skip GPU tests
python -m pytest -v -m "not gpu and not ai_models"

# Only a specific module's tests
python -m pytest src/core/ai_models_test.py -v

# Only integration tests
python -m pytest tests/ -v
```

## Migration Rules

- **Do NOT move existing tests in bulk**
- When significantly modifying a module, move its test file at that time
- New modules MUST have adjacent test files
- Shared fixtures stay in `tests/conftest.py`
