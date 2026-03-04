# Dependency Audit Report - 2026-03-04

## Python Dependencies

- **Audit Tool used**: `pip-audit`
- **Vulnerabilities Found**:
  - `cryptography` (CVE-2026-26007): Elliptic curve missing validation issue.
  - `diskcache` (CVE-2025-69872): Arbitrary code execution via pickle serialization.
- **Actions Taken**:
  - Upgraded `cryptography` to `46.0.5` to resolve CVE-2026-26007.
  - Upgraded safe dependencies `fastapi`, `uvicorn`, `pydantic`.
  - Intentionally skipped `diskcache` update as there was no immediately available non-breaking patched version in the audit report; risk is mitigated if the local cache directory is strictly controlled by the system.
  - Pinned `torch`, `torchvision`, `torchaudio`, `transformers`, `onnxruntime`, `insightface`, `open-clip-torch` at their current versions. These are intentionally NOT upgraded to avoid breaking CUDA/cuDNN compatibility, as they have tight coupling and no critical CVEs were reported.
- **Constraints Maintained**: Python version remains at 3.11 for ONNX compatibility.

## Frontend Dependencies (`web/`)

- **Audit Tool used**: `npm audit`
- **Vulnerabilities Found**: 2 moderate/high vulnerabilities (related to `ajv` and `minimatch` ReDoS).
- **Actions Taken**:
  - Ran `npm audit fix` which resolved all 2 vulnerabilities automatically.
  - Upgraded outdated safe packages (`tailwindcss`, `@tailwindcss/postcss`, `framer-motion`, `lucide-react`, `eslint`, `react`, `react-dom` to the latest minor/patch versions).
  - Fixed a Playwright type issue (`e2e/onboarding-tour.spec.ts`) caused by newer typings.
- **Constraints Maintained**: Next.js major version remains on `16.x`.

## Rust Dependencies (`src-tauri/`)

- **Audit Tool used**: Attempted to use `cargo audit`
- **Vulnerabilities Found**: N/A
- **Actions Taken**:
  - Skipped `cargo audit` installation because the latest versions (and previous versions `0.21.2`) require rustc 1.85+ and our current compiler is `1.84.1`.
  - Skipped `cargo update` because it pulls in crates (e.g. `time-core 0.1.8`, `deranged 0.5.8`) that require `edition2024` and `rustc 1.85+`, which fails with our local compiler. The `Cargo.lock` has been left at its previous state to ensure `cargo check` passes cleanly.

## Next Recommended Audit Date

- **2026-04-04** (Monthly)

### diskcache — mitigation status (updated 2026-03-04)
- **Issue**: Deserialization vulnerability allowing arbitrary code execution via crafted cache files.
- **Upstream fix**: Not yet released as of 2026-03-04.
- **Risk level**: LOW for this project — LocalCurator Prime is offline-first, cache files are local-only and not user-facing.
- **Mitigation**: (1) Cache directory permissions restricted to current user. (2) No external cache file import feature. (3) Monitoring PyPI for patched version.
- **Action**: Will upgrade immediately when patch is released. Re-check monthly.
