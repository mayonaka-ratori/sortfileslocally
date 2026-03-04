<div align="center">
  <img src="https://via.placeholder.com/150/09090b/4f46e5?text=LCP" alt="Local Curator Prime Logo" width="100"/>
  <h1>Local Curator Prime</h1>
  <p><strong>AI-Powered Local Media Manager & Semantic Search</strong></p>
</div>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11-blue" alt="Python Version">
  <img src="https://img.shields.io/badge/Next.js-16.1.6-black" alt="Next.js">
  <img src="https://img.shields.io/badge/FastAPI-0.129.0-009688" alt="FastAPI">
  <img src="https://img.shields.io/badge/PyTorch-2.5.1-ee4c2c" alt="PyTorch">
  <img src="https://img.shields.io/badge/Tauri-v2-38bdf8" alt="Tauri">
  <img src="https://img.shields.io/badge/License-MIT-green" alt="License">
  <img src="https://github.com/mayonaka-ratori/sortfileslocally/actions/workflows/ci.yml/badge.svg" alt="CI">
</p>

---

## 🌟 Overview (English)

**Local Curator Prime** is a powerful, offline-first media management suite designed to intelligently catalog, tag, and search your local image and video collections. By leveraging state-of-the-art Vision-Language Models (VLM) and Semantic Search, it transforms your folders into a searchable, interactive digital library.

### ✨ Key Features

- **🔍 Semantic Search**: Search using natural language instead of just filenames.
- **🤖 Automated AI Tagging**: Detects characters, series, and objects automatically.
- **🎬 Video Understanding**: Speech-to-text and scene-by-scene visual indexing.
- **🛡️ 100% Privacy**: All AI processing happens locally. Zero data leakage.
- **🏥 Self-Healing Architecture**: Automatic recovery for AI sidecars and vector indices.

### 🏗 Architecture

See **[Architecture Overview](docs/ARCHITECTURE.md)** for deep-dive technical details.

```text
LocalCuratorPrime/
├── server/            # FastAPI Backend (Python)
├── web/               # Next.js Frontend (TypeScript)
├── src/               # Shared AI/Data Logic
├── src-tauri/         # Rust Desktop Shell
├── scripts/           # Build & Admin Utility Scripts
└── docs/              # Detailed Documentation
```

### 🚀 Development Quick Start

**1. Backend**

```bash
python -m venv venv
# Windows: venv\Scripts\activate | Unix: source venv/bin/activate
pip install -r requirements.txt
python server/main.py
```

**2. Frontend**

```bash
cd web && npm install && npm run dev
```

---

## 🌟 概要 (日本語)

**Local Curator Prime** は、ローカルに保存された大量の画像や動画を AI でスマートに管理するための、完全オフライン型のメディア管理スイートです。

### ✨ 主な機能

- **🔍 セマンティック検索**: 自然言語でメディアを検索。
- **🤖 自動AIタグ付け**: キャラクター、作品名、一般属性を自動抽出。
- **🎬 動画解析**: 音声文字起こしとシーン別の視覚インデックス。
- **🛡️ 100% プライバシー**: すべての推論処理はローカルで完結。
- **🏥 自己修復設計**: バックエンドのクラッシュ監視と自動再起動機能を搭載。

詳細な使い方は **[ユーザーマニュアル (日本語)](docs/USER_MANUAL_JP.md)** をご覧ください。

---

## 📚 Documentation

- **[Changelog](CHANGELOG.md)**: Full history of Sprint 1-6.
- **[Architecture](docs/ARCHITECTURE.md)**: System design and data flow.
- **[API Reference](docs/api.md)**: Backend endpoint documentation.
- **[I18n Localization](docs/i18n.md)**: Translation guide.

---

## 🏗️ Production Build

To build the standalone desktop application:

**Windows (PowerShell)**:

```powershell
./scripts/build_production.ps1 --cpu-only
```

**macOS / Linux (Bash)**:

```bash
chmod +x scripts/build_production.sh
./scripts/build_production.sh --cpu-only
```

The installer will be generated in `src-tauri/target/release/bundle`.

---

## 📄 License

MIT License - see the [LICENSE](LICENSE) file for details.
