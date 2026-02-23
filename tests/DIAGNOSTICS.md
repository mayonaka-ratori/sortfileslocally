# Secondary Test Failure Diagnostics Report

## Summary
After fixing the `PIL` dependency and removing obsolete tests, 7 tests continue to fail. These failures are categorized below with tracebacks and recommended actions.

## 1. Logic Bug (Encoding)
*The environment terminal (cp932/Shift-JIS on Windows) crashes when the test script attempts to print emojis (✅, ❌) to stdout.*

| Test Name | Error Message (Traceback Excerpt) | Recommended Action |
| :--- | :--- | :--- |
| `test_engine.py` | `File "tests/test_engine.py", line 47, in test_engine`<br>`print("\u2705 AIEngine initialized.")`<br>`UnicodeEncodeError: 'cp932' codec can't encode character '\u2705'` | **Fix Code**: Set `PYTHONIOENCODING=utf-8` in the test runner script (`test-runner.ps1`), or remove emojis from `print()` statements in tests. |
| `test_optimization.py` | `File "tests/test_optimization.py", line 74, in benchmark`<br>`print(f"\n\u2705 Optimization SUCCESS...`<br>`UnicodeEncodeError: 'cp932' codec can't encode character '\u2705'` | **Fix Code**: Same as above. |
| `test_pipeline.py` | `File "tests/test_pipeline.py", line 53, in test_pipeline`<br>`print("\u2705 Processor Initialized.")`<br>`UnicodeEncodeError: 'cp932' codec can't encode character '\u2705'` | **Fix Code**: Same as above. |

## 2. Logic Bug (Missing Test Data)
*The test looks for specific hardcoded file paths that do not exist.*

| Test Name | Error Message (Traceback Excerpt) | Recommended Action |
| :--- | :--- | :--- |
| `test_deduplication.py` | `Error hashing path/to/img_a_big.jpg: [Errno 2] No such file`<br>`File "tests/test_deduplication.py", line 75, in test_deduplication_logic`<br>`assert len(img_pair) == 1 AssertionError` | **Fix Code**: Update the test to use dynamically generated temporary images or `unittest.mock` instead of hardcoded `path/to/...`. |
| `test_sorter.py` | `File "tests/test_sorter.py", line 49, in test_sorter_safety`<br>`assert os.path.exists(dst_file)`<br>`AssertionError` | **Fix Code**: The `test_sorter_safety` function relies on paths/files that aren't properly prepared or asserts on an incorrect mock state. Rewrite the test to use `tempfile` properly. |

## 3. Outdated Test
*The test references functions or methods that have been refactored or removed.*

| Test Name | Error Message (Traceback Excerpt) | Recommended Action |
| :--- | :--- | :--- |
| `test_vlm_debug.py` | `File "tests/test_vlm_debug.py", line 6, in <module>`<br>`vlm._load_model()`<br>`AttributeError: 'VLMEngine' object has no attribute '_load_model'` | **Update Test**: The `VLMEngine` class method was renamed to `_load_model_unlocked()`. Update the test script to call the correct method or use a public interface. |

## 4. Environment Issue (DLL Load Failure)
*A core dependency required by the AI Pipeline fails to initialize natively in Windows.*

| Test Name | Error Message (Traceback Excerpt) | Recommended Action |
| :--- | :--- | :--- |
| `test_video_understanding.py` | `File "venv\lib\site-packages\onnxruntime\__init__.py", line 74`<br>`raise import_capi_exception`<br>`ImportError: DLL load failed while importing onnxruntime_pybind11_state` | **Install Missing C++ Redistributable**: Error usually points to missing MSVC++ Redistributables required by `onnxruntime`. Install them, or downgrade `onnxruntime` if it's a known bug in this specific release. |
