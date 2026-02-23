# LocalCuratorPrime - User Manual

Welcome to **LocalCuratorPrime**! This manual will guide you through setting up and using the application, even if you are not a technical user.

---

## 🏁 1. First-Time Setup

1. **Wait for Model Downloads**: When you first run the application, it needs to download several AI "brains" (models). This is about 6GB of data. Ensure you have a stable internet connection.
   ![Setup Screen](C:/tools/organizefiles0112/LocalCuratorPrime/docs/mockup_hero.png)
2. **Setup Folder**: Go to the **Settings** or **Setup** tab in the sidebar.
   *Note: After changing the model storage directory, restart the application for the change to take effect.*
3. **Add a Directory**: Click "Add Folder" and select the directory on your computer where your images and videos are stored.
4. **Start Scan**: Click the **Start Scan** button. The AI will start "looking" at every file, describing them, and transcribing audio.

---

## 🔄 2. Basic Workflow

1. **Index**: The app scans your folders.
2. **Search**: Use the search bar to find anything.
   ![Search Interface](C:/tools/organizefiles0112/LocalCuratorPrime/docs/mockup_search.png)
3. **Explore**: Browse the gallery, filter by tags, or chat with specific images.
4. **Clean**: Use the Deduplication tool to find and delete clones of files.

---

## 🛠 3. Feature Guide

### 🔍 Semantic Search
- **What**: Search for images based on their *meaning* or *content*, not just filenames.
- **Why**: Instead of remembering "IMG_4829.jpg", you can search for "red car in the rain".
- **How**: Type your description into the top search bar and press Enter.

### 🤖 Auto-Tagging
- **What**: AI automatically labels your images with characters, themes, and series names.
- **Why**: Keeps your collection organized without any manual work.
- **How**: This happens automatically during a scan. You can see tags below each image in the gallery.

### 🎬 Video Search
- **What**: Search for specific moments *inside* a video.
- **Why**: Find that exact scene where someone says a specific word or where a specific action happens.
- **How**: Just use the search bar. Results will show the exact timestamp (e.g., "Video @12.5s").

### 💬 Vision Chat
- **What**: A chat window where you can ask an AI questions about an image.
- **Why**: To translate text in an image, identify objects, or get a detailed description.
- **How**: Click on any image to open it, then type a question in the **Chat Panel** on the right.

### 🚀 Deduplication
- **What**: Finds files that look the same or nearly identical.
- **Why**: To save disk space by deleting unnecessary copies.
- **How**: Go to the **Deduplication** tab and click "Find Candidates".

### 💾 Metadata Export (EXIF/IPTC)
- **What**: Writes the AI-generated tags and descriptions back into your original files.
- **Why**: Makes your AI-organized collection compatible with other apps like Adobe Lightroom or Windows Explorer.
- **How**: In the file detail view, click **Export Metadata**. Choose "In-place" for JPEG files or "XMP Sidecar" for other formats.

---

## ❓ 4. FAQ / Troubleshooting

### "The app is very slow during the first scan."
- **Cause**: The AI is working hard to analyze your files using your GPU or CPU.
- **Solution**: This is normal. Subsequent searches will be instant once the scan is finished.

### "I get a 'CUDA Out of Memory' error."
- **Cause**: Your graphics card doesn't have enough memory to run the AI model.
- **Solution**: Close other heavy apps (like games or browsers) and restart the scan.

### "No results found for my search."
- **Cause**: The scan might not be finished yet, or the description is too vague.
- **Solution**: Check the scan progress in the sidebar. Try using different keywords.

---

## 🛑 5. Common Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| `Path does not exist` | The folder you selected was moved or deleted. | Re-select the folder in Settings. |
| `Model not downloaded` | A required AI model is missing. | Go to Setup and click "Download" for the missing model. |
| `Scan already in progress` | You tried to start a new scan while one is already running. | Wait for the current scan to finish or pause it. |
| `No resumable scan job found` | You tried to resume a scan but there are no incomplete jobs. | Start a new scan instead. |
| `Original path no longer exists` | The folder being scanned was moved while the app was closed. | Move the folder back or start a new scan with the new path. |
| `File not found` | The media file was moved or deleted after it was indexed. | Run a new scan to refresh the library. |
| `Invalid image file` | The file is corrupted or not a supported image format. | Check if you can open the file in other applications. |
| `Network Error` | The backend server is not running. | Make sure the black terminal window (Python) is open. |
| `Access denied: file not in library` | You tried to delete a file that the app doesn't recognize. | Only use the app to manage files it has already scanned. |
