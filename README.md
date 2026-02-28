<div align="center">
  <img src="https://via.placeholder.com/150/09090b/4f46e5?text=LCP" alt="Local Curator Prime Logo" width="100"/>
  <h1>Local Curator Prime</h1>
  <p><strong>AI-Powered Local Media Manager & Semantic Search</strong></p>
</div>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue" alt="Python Version">
  <img src="https://img.shields.io/badge/Next.js-16.1.6-black" alt="Next.js">
  <img src="https://img.shields.io/badge/FastAPI-0.129.0-009688" alt="FastAPI">
  <img src="https://img.shields.io/badge/PyTorch-2.5.1-ee4c2c" alt="PyTorch">
  <img src="https://img.shields.io/badge/Tailwind_CSS-4-38bdf8" alt="Tailwind CSS">
  <img src="https://img.shields.io/badge/License-MIT-green" alt="License">
  <img src="https://github.com/mayonaka-ratori/sortfileslocally/actions/workflows/ci.yml/badge.svg" alt="CI">
</p>

---

## 🌟 Overview (English)

**Local Curator Prime** is a powerful, offline-first media management suite designed to intelligently catalog, tag, and search your local image and video collections. By leveraging state-of-the-art Vision-Language Models (VLM) and Semantic Search, it transforms your folders into a searchable, interactive digital library.

### ✨ Key Features

- **🔍 Semantic Search**: Search using natural language (e.g., *"a cat sleeping on a sunny windowsill"*) instead of just filenames.
- **🤖 Automated AI Tagging**: Automatically detects characters, series, and objects in your images.
- **🎬 Video Understanding**: Transcribes audio with Whisper and describes scenes using VLM for deep video search.
- **💬 Chat with Media**: Interactive VLM panel to ask questions about specific images or videos.
- **🚀 Deduplication**: Find and manage visually similar or duplicate files to save space.
- **💾 Metadata Export**: Write AI-generated tags back to files as EXIF/IPTC or XMP sidecars.
- **🛡️ 100% Privacy**: All AI processing happens locally. No data ever leaves your machine.

### 🏗 Project Structure

```text
LocalCuratorPrime/
├── server/            # FastAPI Backend (Python)
│   ├── routers/       # API Endpoints (Scan, Gallery, Dedup, Setup)
│   └── main.py        # Backend Entry Point
├── web/               # Next.js Frontend (TypeScript)
│   └── src/           # UI Components and Logic
├── src/               # Shared AI/Data Logic
│   ├── core/          # AI Inference Engines (CLIP, VLM, Whisper)
│   └── data/          # Database & Job Management
├── docs/              # Detailed Documentation & User Manuals
└── data/              # Local Storage (SQLite, Vector Index, Thumbnails)
```

### 🛠 Tech Stack

- **Frontend**: Next.js 16.1.6 (React 19.2.3), Tailwind CSS 4, Lucide React, Framer Motion.
- **Backend**: FastAPI 0.129.0, Uvicorn, SQLite3.
- **AI Core**: PyTorch 2.5.1, Transformers, FAISS (Vector DB), InsightFace (Face ID), faster-whisper.

### 🚀 Quick Start

**1. Backend Setup**

```bash
# Enter project directory
cd LocalCuratorPrime

# Create venv and install
python -m venv venv

# Windows:
venv\Scripts\activate
# Mac / Linux:
source venv/bin/activate

# Install dependencies (ensure PyTorch matches your CUDA version if using GPU)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
pip install -r requirements.txt

# Start Server
cd server
python main.py
```

**2. Frontend Setup**

```bash
# Open a new terminal
cd LocalCuratorPrime/web

# Install dependencies and start
npm install
npm run dev
```

Visit `http://localhost:3000`.

---

## 🌟 概要 (日本語)

**Local Curator Prime** は、ローカルに保存された大量の画像や動画を AI でスマートに管理するための、完全オフライン型のメディア管理スイートです。最新の視覚言語モデル (VLM) とセマンティック検索を組み合わせ、単なるファイル管理を超えた「対話可能なライブラリ」を実現します。

### ✨ 主な機能

- **🔍 セマンティック検索**: 「夕暮れの浜辺を歩く犬」のような自然言語での記述でメディアを瞬時に特定します。
- **🤖 自動AIタグ付け**: 画像からキャラクター、作品名、一般属性を自動で抽出・付与します。
- **🎬 動画解析**: Whisper による音声文字起こしと、VLM によるシーン説明により、動画内の特定の場面を検索可能です。
- **💬 メディアと対話**: ギャラリー内の画像に対し、VLM (AI) を通じて質問をしたり説明を求めたりできます。
- **🚀 ダブリの解消 (Deduplication)**: 視覚的に類似したファイルや完全な重複ファイルを検出し、整理を支援します。
- **💾 メタデータの書き出し**: AIが付与したタグを EXIF/IPTC 形式でファイルに直接書き込む、または XMP サイドカーとして出力できます。
- **🛡️ 100% プライバシー**: すべての推論処理はローカルで完結します。データが外部に送信されることはありません。

### 🛠 テックスタック

- **フロントエンド**: Next.js 16.1.6 (React 19.2.3), Tailwind CSS 4, Lucide React.
- **バックエンド**: FastAPI 0.129.0, Uvicorn, SQLite3.
- **AI Core**: PyTorch 2.5.1, Transformers, FAISS, faster-whisper.

### 🚀 クイックスタート

**1. バックエンドのセットアップ**

```bash
# ディレクトリへ移動
cd LocalCuratorPrime

# 仮想環境の作成と有効化
python -m venv venv
# Windows: venv\Scripts\activate
# Mac / Linux: source venv/bin/activate

# 依存関係のインストール
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
pip install -r requirements.txt

# サーバーの起動
cd server
python main.py
```

**2. フロントエンドのセットアップ**

```bash
# 新しいターミナルを開く
cd LocalCuratorPrime/web

# インストールと起動
npm install
npm run dev
```

Webブラウザで `http://localhost:3000` を開いてください。

詳細な使い方は [USER_MANUAL.md](docs/USER_MANUAL_JP.md) をご覧ください。

---

## 📚 Documentation

- **[Changelog](CHANGELOG.md)**: View the full history of changes for each release.
- **[API Reference](docs/api.md)**: Detailed documentation of all backend endpoints.
- **[I18n Localization Guide](docs/i18n.md)**: Learn how to add new languages and update translations.
- **[User Manual (JP)](docs/USER_MANUAL_JP.md)**: 詳細なユーザーマニュアル（日本語）.

---

## 🧪 Testing

### Backend Tests

The backend uses `pytest` with `pytest-cov` for coverage reporting.

```powershell
# Run all tests (requires GPU/models for some)
python -m pytest tests/ -v

# Skip GPU tests (for CI or machines without GPU)
$env:SKIP_GPU_TESTS="1"; python -m pytest tests/ -v

# Run with coverage report
python -m pytest tests/ -v --cov=src --cov=server --cov-report=term-missing

# Run only fast tests (skip slow AI model tests)
python -m pytest tests/ -v -m "not ai_models and not slow"
```

### Frontend Tests

The frontend uses Playwright for E2E testing.

```powershell
# Lint checks
cd web
npm run lint

# Run E2E tests (requires both frontend and backend servers running)
# Ensure backend is at http://localhost:8000 and frontend at http://localhost:3000
npm run test:e2e

# Open Playwright UI for debugging
npm run test:e2e:ui
```

## 🏗️ Building Desktop App

### Prerequisites

- Python 3.11 (due to `onnxruntime` compatibility constraints)
- Rust toolchain (rustc, cargo)
- Node.js 20+
- PyInstaller: `pip install pyinstaller`

### Build Backend (PyInstaller)

```powershell
# CPU-only (smaller footprint, ~300-500 MB)
python scripts/build_backend.py --cpu-only

# GPU / All-inclusive (larger, ~2.5-4 GB)
python scripts/build_backend.py
```

### Build Desktop App (Tauri)

```powershell
# Unified build: statically exports frontend and bundles with backend sidecar
npm run tauri:build
```

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
