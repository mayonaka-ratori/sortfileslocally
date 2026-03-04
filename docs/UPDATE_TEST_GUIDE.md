# LocalCurator Prime - Updater Test Guide

This guide describes how to verify the Tauri auto-update configuration locally without deploying to production.

## Prerequisites

1. Have your Updater Keypair generated and the public key added to `tauri.conf.json`.
2. Ensure you have the Python environment active.

## Step-by-Step Test

1. **Start the Mock Server:**
   Run the following command to start a small local update server on port 9999.

   ```bash
   python scripts/mock_update_server.py --version "99.0.0" --notes "Test update feature."
   ```

2. **Temporarily Modify Endpoint:**
   In `src-tauri/tauri.conf.json`, temporarily change the `endpoints` array to point to the mock server:

   ```json
   "updater": {
     "endpoints": ["http://localhost:9999/latest.json"],
     "pubkey": "YOUR_PUBLIC_KEY"
   }
   ```

3. **Launch the Application:**
   Start the Tauri application (either in dev mode or a local release build).

   ```bash
   npm run tauri dev
   ```

4. **Verify Dialog:**
   Shortly after the frontend loads, Tauri will check `http://localhost:9999/latest.json`. Because the version `99.0.0` is higher than the current version, the native Tauri Update Dialog should appear, displaying the release notes ("Test update feature.").

5. **Revert Changes:**
   Once verified, **make sure to revert** `tauri.conf.json` endpoints back to the original GitHub Releases URL before committing!

![Update Dialog Preview](./assets/update_dialog_placeholder.png)
