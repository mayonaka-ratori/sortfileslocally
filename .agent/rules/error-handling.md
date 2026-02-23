# Error Handling and Logging

Guidelines for maintaining system stability and debuggability.

## Logging Strategy
- Use `loguru` for all application logging.
- Differentiate between `info`, `debug`, `warning`, and `error`.

## Exception Handling
- Always wrap complex pipeline logic in `try...except` blocks.
- Include `traceback.format_exc()` for `error` level logs to aid root cause analysis.

### Example
```python
from loguru import logger
import traceback

try:
    processor.run()
except Exception as e:
    logger.error(f"Execution failed: {e}\n{traceback.format_exc()}")
```

## Backend Responses
- Return descriptive HTTP error codes (400, 404, 500) with helpful JSON detail messages.
