# LocalCurator Prime 取扱説明書 / User Manual

## 🇯🇵 日本語 (Japanese)

LocalCurator Primeは、AI（VLMおよび音声認識）を活用して、PC内の大量の画像や動画を自動で整理、文脈検索、そしてチャットで内容を分析するための次世代ローカル・メディア管理ツールです。

2026年のアップデートにより、**「ハイパー・フルイド（Hyper-Fluid）」** デザインシステムと **「Synchronized Playback Engine」** を搭載し、より直感的でシームレスな体験を提供します。

---

## 1. 起動方法

WebブラウザベースのモダンなUIを採用しています。バックエンド（AIエンジン）とフロントエンド（UI）の両方を起動する必要があります。

### バックエンド (FastAPI / AI Engine)

ターミナルを開き、プロジェクトフォルダで以下を実行します。

```powershell
# Pythonの仮想環境を有効化 (任意)
# .\venv\Scripts\activate

cd server
python main.py
```

### フロントエンド (Next.js / Web UI)

別のターミナルを開き、`web` フォルダに移動して以下を実行します。

```powershell
cd web
npm run dev
```

起動後、ブラウザで `http://localhost:3000` にアクセスしてください。

---

## 2. 推奨システム要件

| スペック | 詳細 |
| :--- | :--- |
| **OS** | Windows 10/11 |
| **GPU** | NVIDIA GPU (VRAM 8GB以上推奨, 快適な動作には12GB以上) |
| **ストレージ** | SSD推奨 (初回モデルダウンロードに約6GBの空き容量が必要) |

---

## 3. 基本操作フロー

### ステップ1：スキャン

1. 左側のサイドバーにある **「Scanner」** タブに、整理したいメディアが入っているフォルダのパスを入力します。
2. **「Start Scan」** ボタンをクリックします。プログレスバーでリアルタイムの進捗や残り時間（ETA）が確認できます。
3. AIが各ファイル（動画含む）を解析し、内容、タグ、音声などをデータベースに登録します。

### ステップ2：検索と閲覧

1. 画面上部の検索バーに **「海辺に沈む夕日」** や **「雨の中で笑う女の子」** など、自然言語を入力してEnterを押します。
2. 文脈を理解したAIが、類似度の高い順にメディアを表示します。動画の音声やシーン解説にヒットした場合は、対象の「スニペット（抜粋）」が表示されます。

---

## 4. 主要機能の紹介

* 🔍 **Semantic Search（セマンティック検索）**: ファイル名や手付けのタグではなく、「意味」や「文脈」で検索します。動画内のセリフやアクションも検索対象です。
* 🎬 **Synchronized Playback（同期再生エンジン）**: メインギャラリーとチャットパネル間での再生状態（再生/一時停止/シーク）が完全に同期されます。どこでもシームレスな確認が可能です。
* ✨ **Hyper-Fluid Design（ハイパー・フルイド設計）**: 最新のグラスモフィズム（Glassmorphism）を採用した、美しくレスポンスの良いUI。Geist Variableフォントにより、視認性も極限まで高められています。
* 🎬 **Video Understanding（動画・音声理解）**: 動画からキーフレームを抽出してAIが状況を説明（Moondream2）し、音声は文字起こし（Whisper）してデータベース化します。
* 🏷️ **Auto Tagging & Filtering（自動タグ付けとフィルタ）**: キャラクター名、シリーズ名、一般タグなどを自動推論。サイドバーでクイックな絞り込みが可能です。
* 💬 **Chat with Media（メディアとの対話）**: メディアをクリックして右側のチャットパネルを開くと、AIに内容について直接質問が可能です。

---

## 5. プロフェッショナルな使い方のコツ

* **Force Reprocess (強制再スキャン):** 以前スキャンしたフォルダに新機能（動画の音声解析など）を適用したい場合は、`Force Reprocess` にチェックを入れてスキャンしてください。
* **高性能GPU:** NVIDIA RTX 40シリーズ等の高性能GPU環境では、数千枚のメディア解析も極めて高速に完了します。

---

## 6. よくある質問とトラブルシューティング (FAQ)

* **Q. 初回起動がまったく終わらない**
  * **A.** 初回はAIモデル（約6GB）のダウンロードが行われるため、時間がかかります。ターミナルのログを確認してください。
* **Q. 「CUDA Out of Memory」エラーが出る**
  * **A.** GPUのVRAMが不足しています。他の高負荷アプリ（ゲーム等）を閉じてから再試行してください。
* **Q. 動作が非常に重い**
  * **A.** NVIDIA GPUをお持ちの場合は、CUDA対応のPyTorchが正しくインストールされているか確認してください。CPUでのみ動作している可能性があります。
* **Q. データは外部に送信されますか？**
  * **A.** いいえ。すべての処理はローカルで完結します。プライバシーは完全に保護されます。

---

## 🇺🇸 English (User Manual)

LocalCurator Prime is a next-generation local media management tool that utilizes AI to automatically organize, semantically search, and analyze your massive local image and video collections.

The 2026 update features the **"Hyper-Fluid"** design system and the **"Synchronized Playback Engine"** for a more intuitive and seamless experience.

---

## 1. How to Start

This application uses a modern web-browser based UI. You need to start both the backend (AI Engine) and frontend (UI).

### Backend (FastAPI / AI Engine)

Open a terminal, navigate to the project folder, and run:

```powershell
# Activate venv (optional)
# .\venv\Scripts\activate

cd server
python main.py
```

### Frontend (Next.js / Web UI)

Open a new terminal, navigate to the `web` folder, and run:

```powershell
cd web
npm run dev
```

After starting, open your browser and navigate to `http://localhost:3000`.

---

## 2. Recommended System Requirements

| Specification | Details |
| :--- | :--- |
| **OS** | Windows 10/11 |
| **GPU** | NVIDIA GPU (8GB VRAM recommended, 12GB+ for optimal performance) |
| **Storage** | SSD recommended (Requires approx. 6GB free space for initial AI models) |

---

## 3. Basic Workflow

### Step 1: Scan

1. In the **Scanner** section of the left sidebar, enter the path to the folder containing your media.
2. Click the **Start Scan** button. You can monitor the real-time progress and ETA via the progress bar.
3. The AI will analyze each file and register its contents, tags, and audio transcriptions to the database.

### Step 2: Search and Browse

1. In the top search bar, enter natural language queries like **"sunset at the beach"** and press Enter.
2. The AI understand the context and displays media in order of semantic similarity.

---

## 4. Key Features

* 🔍 **Semantic Search**: Search by "meaning" rather than filenames. Dialogue and actions inside videos are also searchable.
* 🎬 **Synchronized Playback**: Playback state (play/pause/seek) is fully synced between the main gallery and the detail chat panel.
* ✨ **Hyper-Fluid Design**: Beautiful responsive UI using modern Glassmorphism. Optimized for clarity with Geist Variable fonts.
* 🎬 **Video Understanding**: AI scene description (Moondream2) and audio transcription (Whisper).
* 🏷️ **Auto Tagging & Filtering**: Automatically infers tags. Use the sidebar for quick filtering.
* 💬 **Chat with Media**: Open the chat panel to ask the AI questions about the selected media.

---

## 5. Pro Tips

* **Force Reprocess:** To apply new AI features to previously scanned folders, check the `Force Reprocess` box before scanning.
* **High-Performance GPU:** With an NVIDIA RTX 40-series GPU, analysis of thousands of items completes extremely fast.

---

## 6. Troubleshooting & FAQ

* **Q. First startup is taking forever.**
  * **A.** On the first run, AI models (approx. 6GB) will be downloaded. Please check the terminal for logs.
* **Q. I get a "CUDA Out of Memory" error.**
  * **A.** Your GPU ran out of VRAM. Close resource-heavy apps (like games) before scanning.
* **Q. The processing is extremely slow.**
  * **A.** Ensure you have PyTorch with CUDA installed. The AI might be falling back to CPU.
* **Q. Is my data sent to external servers?**
  * **A.** No. All processing is strictly local. Privacy-first by design.
