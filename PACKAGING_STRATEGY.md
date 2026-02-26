# LocalCurator Prime: Packaging Strategy Analysis

This document provides a detailed feasibility analysis and implementation plan for packaging LocalCurator Prime as a standalone desktop application for Windows, macOS, and Linux.

---

## 1. Feasibility Check

**Can Next.js 16 with App Router run inside Tauri v2's webview?**
Yes. However, Tauri serves files via a native webview (WebView2 on Windows, WKit on macOS, WebKitGTK on Linux), which means it expects static assets (HTML/CSS/JS). To run natively inside the webview without bundling the entire Node.js runtime, Next.js must be configured for a Static HTML Export (`output: 'export'`).

**What Next.js features break with `output: 'export'`?**
*   **Server-Side Rendering (SSR) & Server Components API:** Features requiring a Node.js server at runtime (e.g., `getServerSideProps`, Server Actions, dynamic Route Handlers).
*   **Dynamic Functions:** Usage of `cookies()`, `headers()`, or `req` objects.
*   **Middleware & Edge Functions:** Not supported as there is no Next.js server to intercept requests.
*   **Image Optimization:** Default `next/image` optimization requires a server. It must be set to `unoptimized: true` or a custom loader must be provided.
*   **Incremental Static Regeneration (ISR):** Background revalidation requires a Next.js server.
*   **Resolution:** Since the app already has a dedicated FastAPI backend, the Next.js frontend should be strictly treated as a Single Page Application (SPA). All dynamic data loading must occur client-side by querying the FastAPI backend.

**Tauri v2 Sidecar Capabilities:**
Tauri v2 fully supports multiple sidecar processes. External binaries can be declared in `tauri.conf.json` within the `bundle.externalBin` array. While Tauri can technically manage a Node.js sidecar and a Python sidecar simultaneously, it is highly discouraged due to massive bundle bloat and increased memory footprint.

---

## 2. Architecture Options

### Option A: Tauri + Static Export + Python Sidecar (Recommended)
*   **Architecture:** Next.js is statically exported (`output: 'export'`) and loaded directly into Tauri's webview. The FastAPI backend is packaged via PyInstaller into a standalone binary and launched by Tauri as a single sidecar process.
*   **Pros:** Native OS window management, extremely small UI bundle size (Tauri is lightweight), minimal RAM usage, standard cross-platform distribution installers (.msi, .dmg, .AppImage). Easy access to native OS APIs if needed.
*   **Cons:** Requires refactoring any Next.js server-side logic to client-side fetching.
*   **Migration Effort:** Moderate. Involves Next.js export configuration and wiring Tauri to manage the Python process lifecycle.

### Option B: Tauri + Embedded Next.js Server + Python Sidecar
*   **Architecture:** Tauri launches two sidecars: a standalone Node.js binary running the Next.js server, and the Python backend.
*   **Pros:** No need to refactor out Next.js server components or middleware.
*   **Cons:** Enormous bundle size and RAM overhead (running Chromium WebView + Node.js + Python simultaneously). Exceptionally complex process lifecycle management.
*   **Migration Effort:** High. Packaging Node.js apps as executables (e.g., via `pkg` or `nexe`) with Next.js is notoriously fragile.

### Option C: Electron + Python Sidecar
*   **Architecture:** Electron bundles Chromium and Node.js. It serves the Next.js app (statically or dynamically) and spawns the Python sidecar.
*   **Pros:** Widespread ecosystem, easy to embed Node.js.
*   **Cons:** Bloated installation size and high baseline memory usage (Electron overhead). Tauri is fundamentally lighter and faster.
*   **Migration Effort:** Moderate. Similar to Tauri but with different IPC mechanisms.

### Option D: PyInstaller-only (No Tauri/Electron)
*   **Architecture:** Next.js is statically exported and served directly by FastAPI as static files. The user launches `LocalCurator.exe`, which opens their default web browser (e.g., Chrome/Edge) to `http://localhost:8000`.
*   **Pros:** Absolute simplest packaging setup. Only one process to manage.
*   **Cons:** Lacks a true "desktop application" feel. No native application window, dock/taskbar icon behavior is tied to the browser, and no access to native OS dialogue boxes or filesystem APIs from the frontend.
*   **Migration Effort:** Low.

### Recommendation: **Option A**
Option A is the only approach that meets the lightweight bundle size constraints (< 500 MB CPU-only), provides a native desktop experience, and maintains a clean separation of concerns. The primary effort will be ensuring the Next.js frontend is fully static-compatible.

---

## 3. Implementation Plan (Phase-by-Phase)

### Phase A: Project Scaffolding
*   **Objective:** Initialize Tauri within the existing project structure.
*   **Steps:**
    1. Run `npx create-tauri-app` inside the project root (or integrate into the `web` workspace).
    2. Configure `tauri.conf.json` with app identifiers, window dimensions, and permissions.
    3. Define the Python backend as `bundle.externalBin` in the Tauri config.
    4. Implement Tauri Rust code (`src-tauri/src/main.rs`) to spawn and monitor the Python sidecar on startup and elegantly terminate it when the Tauri window closes.

### Phase B: Frontend Adaptation
*   **Objective:** Convert Next.js to a static SPA.
*   **Steps:**
    1. Update `next.config.mjs`: add `output: 'export'` and configure `images: { unoptimized: true }`.
    2. Audit frontend for `cookies()`, `headers()`, tracking down any server-side dependencies and converting them to React hooks (`useEffect`, `SWR`, or `React Query`).
    3. Ensure API calls are dynamically routed to the Python sidecar's port (which Tauri should pass to the frontend via IPC or environment variables).

### Phase C: Backend Bundling
*   **Objective:** Compile the Python FastAPI backend into a single executable.
*   **Steps:**
    1. Create a `LocalCurator.spec` file for PyInstaller.
    2. Ensure PyTorch, FAISS, and model processing libraries are correctly collected (handling hidden imports).
    3. **CPU-Only vs GPU Targets:** Create two separate virtual environments for builds. The CPU build script installs the `cpu` wheels of PyTorch, drastically reducing the bundle size.
    4. Ensure SQLite uses absolute paths relative to the executable's runtime directory (`sys._MEIPASS` or standard AppData paths).

### Phase D: Build Scripts & Installers
*   **Objective:** Produce final packaged installers for distribution.
*   **Steps:**
    1. Write CI/CD shell scripts to sequentially build the Next.js static export -> PyInstaller backend -> Tauri bundle.
    2. Configure Tauri bundler for `.msi` (Windows), `.dmg` (macOS), and `.AppImage` (Linux).
    3. Setup application signing (Code Signing certificates for Windows, Apple Developer ID for macOS) in the CI environment to prevent SmartScreen/Gatekeeper warnings.

---

## 4. Risk Analysis

*   **PyInstaller + PyTorch Bundle Size:** Even CPU-only PyTorch can be large. *Mitigation:* Explicitly build within a fresh `venv` installing `torch torchvision --index-url https://download.pytorch.org/whl/cpu`. Use PyInstaller's integration with `UPX` for further binary compression.
*   **FAISS Binary Compatibility:** FAISS relies on C++ extensions that compile differently per OS. *Mitigation:* Native CI runners (Windows, macOS, Linux) must be used to perform the PyInstaller build step. Cross-compilation for Python C-extensions is generally unreliable.
*   **SQLite Path Resolution:** Packaged environments extract files to temporary directories (e.g., `sys._MEIPASS`). *Mitigation:* The backend must dynamically determine whether it's running as a script or a frozen executable (`getattr(sys, 'frozen', False)`) and explicitly place the SQLite `.db` file in persistent user data directories (like `%APPDATA%` / `~/.config`), NOT the extracted executable path.
*   **Model Download Paths:** The 5.2 model downloader must save models to a persistent, user-accessible directory (e.g., `AppData/Local/LocalCurator/models`) rather than relative to the executable, ensuring models persist across app updates.
*   **Dev Mode Workflow:** Adding Tauri should not break `npm run dev` and `uvicorn main:app`. *Mitigation:* Tauri's config allows specifying a `devPath` (pointing to `http://localhost:3000`) for development while using the static `distDir` for production builds, maintaining the two-terminal workflow flawlessly.

---

## 5. Phase Estimates

| Phase | Files to Create/Modify | New Dependencies | Estimated Build Time | Testing Strategy |
| :--- | :--- | :--- | :--- | :--- |
| **A: Tauri Scaffolding** | `src-tauri/*`, `package.json` | `@tauri-apps/api`, `@tauri-apps/cli`, Rust toolchain | 5-10m (first compile) | Run `tauri dev` to ensure native window opens Next.js dev server. |
| **B: Frontend Adaptation** | `next.config.mjs`, UI components using SSR, API hooks | None (removing server dependencies) | < 1m | Run `npm run build` to verify successful static export. Test UI strictly in browser targeting separate backend. |
| **C: Backend Bundling** | `backend.spec` (PyInstaller), `main.py` (Pathing) | `pyinstaller` | 5-15m (depending on upx/compression) | Run the compiled PyInstaller binary manually. Execute existing `pytest` suite against the running binary's API. |
| **D: Build & Installers** | `.github/workflows/build.yml`, build scripts | CI signing tools | 15-30m per platform | Install the generated `.msi`/`.dmg` on a clean VM. Verify the app opens and automatically launches the backend. |

**Constraints Adherence Check:**
*   [x] 100% Report only, no implementation.
*   [x] Dev workflow remains untouched (`devPath` handles this).
*   [x] Offline operation intact (FAISS/SQLite managed locally).
*   [x] Tauri structure allows code signing configuration.
*   [x] Greenfield Tauri initialization documented.
