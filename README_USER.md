# LocalCurator Prime 取扱説明書 / User Manual

<details open>
<summary><strong>🇯🇵 日本語 (Japanese)</strong></summary>

LocalCurator Primeは、AI（VLMおよび音声認識）を活用して、PC内の大量の画像や動画を自動で整理、文脈検索、そしてチャットで内容を分析するための次世代ローカル・メディア管理ツールです。

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
|---|---|
| **OS** | Windows 10/11 |
| **GPU** | NVIDIA GPU (VRAM 8GB以上推奨, 快適な動作には12GB以上) |
| **ストレージ** | SSD推奨 (初回モデルダウンロードに約6GBの空き容量が必要) |

---

## 3. 基本操作フロー

### ステップ1：スキャン
1. 左側のサイドバー上部にある **「Folder Scanner」** に、整理したい画像・動画が入っているフォルダのパスを入力します。
2. **「Start Scan」** ボタンをクリックします。プログレスバーでリアルタイムの進捗や残り時間（ETA）が確認できます。
3. AIが各ファイル（動画含む）を解析し、内容、タグ、音声などをデータベースに登録します。

### ステップ2：検索と閲覧
1. 画面上部の検索バーに **「海辺を沈む夕日」** や **「雨の中で笑う女の子」** など、自然言語を入力してEnterを押します。
2. 文脈を理解したAIが、類似度の高い順にメディアを表示します。動画の音声やシーン解説にヒットした場合は、対象の「スニペット（抜粋）」が表示されます。

---

## 4. 主要機能の紹介

* 🔍 **Semantic Search（セマンティック検索）**: ファイル名や手付けのタグではなく、「意味」や「文脈」で検索します。動画内のセリフやアクションも検索対象です。
* 🎬 **Video Understanding（動画・音声理解）**: 動画からキーフレームを抽出してAIが状況を説明（Moondream2）し、音声は文字起こし（Whisper）してデータベース化します。動画にカーソルを合わせると自動でプレビュー再生されます。
* 🏷️ **Auto Tagging & Filtering（自動タグ付けとフィルタ）**: キャラクター名、シリーズ名、一般タグなどを自動推論。左側のサイドバーで「画像のみ / 動画のみ」やキャラクターごとの絞り込みがワンクリックで行えます。
* 💬 **Chat with Media（メディアとの対話）**: ギャラリー内の画像をクリックして右側のチャットパネルを開くと、AIに「この画像には何が描かれていますか？」「このテキストを翻訳して」など直接質問が可能です。

---

## 5. プロフェッショナルな使い方のコツ

* **Force Reprocess (強制再スキャン):** 以前スキャンしたフォルダでも、アプリの新機能（動画の音声解析など）を適用したい場合は、スキャン画面の `Force Reprocess` にチェックを入れてスキャンしてください。
* **高性能GPU:** NVIDIA GPU (RTX 4070 Super等) を搭載した環境であれば、数千枚のメディアや動画のディープラーニング解析も極めて高速に完了します。

---

## 6. よくある質問とトラブルシューティング (FAQ)

* **Q. 初回起動がまったく終わらない**
  * **A.** 初回起動時はAIモデル（約6GB以上）のダウンロードが行われるため、ネットワーク速度によっては数十分から1時間程度かかる場合があります。ターミナルのログを確認してください。
* **Q. 「CUDA Out of Memory」というエラーが出てスキャンが止まる**
  * **A.** GPUのメモリ（VRAM）が不足しています。PCのブラウザや他のゲームなどを閉じてから再試行するか、バックグラウンドのアプリを終了して再開してください。
* **Q. 動作が非常に重い（AIの処理が遅い）**
  * **A.** CPUで処理が実行されている可能性があります。NVIDIA GPUをお持ちの場合は、CUDAに対応したPyTorchが正しくインストールされているか確認してください。
* **Q. データは外部に送信されますか？**
  * **A.** いいえ。すべての処理はローカル環境で完結しており、画像や解析データが外部のサーバーに送信されることは一切ありません（完全オフライン＆プライバシー保護）。

</details>

<details>
<summary><strong>🇺🇸 English (User Manual)</strong></summary>

LocalCurator Prime is a next-generation local media management tool that utilizes AI (Vision-Language Models and Speech Recognition) to automatically organize, semantically search, and analyze your massive local image and video collections.

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
|---|---|
| **OS** | Windows 10/11 |
| **GPU** | NVIDIA GPU (8GB VRAM recommended, 12GB+ for optimal performance) |
| **Storage** | SSD recommended (Requires approx. 6GB free space for initial AI models) |

---

## 3. Basic Workflow

### Step 1: Scan
1. In the **Folder Scanner** section near the top of the left sidebar, enter the path to the folder containing your media.
2. Click the **Start Scan** button. You can monitor the real-time progress and ETA via the progress bar.
3. The AI will analyze each file (including videos) and register its contents, tags, and audio transcriptions to the database.

### Step 2: Search and Browse
1. In the top search bar, enter natural language queries like **"sunset at the beach"** or **"girl laughing in the rain"** and press Enter.
2. The AI understands the context and displays media in order of semantic similarity. If a video's audio or scene description matches, a text snippet of the exact moment will be displayed.

---

## 4. Key Features

* 🔍 **Semantic Search**: Search by "meaning" or "context" rather than exact filenames or manual tags. Dialogue and actions inside videos are also searchable.
* 🎬 **Video Understanding**: Extracts keyframes from videos for AI scene description (Moondream2), and transcribes audio (Whisper). Hover over a video thumbnail to instantly preview it.
* 🏷️ **Auto Tagging & Filtering**: Automatically infers character names, series, and general tags. Use the left sidebar to filter down by "Images only / Videos only" or by specific characters with a single click.
* 💬 **Chat with Media**: Click an image to open the right chat panel and directly ask the AI questions like "What is drawn in this image?" or "Translate this text for me."

---

## 5. Pro Tips

* **Force Reprocess:** If you want to apply new AI features (like video audio analysis) to a previously scanned folder, check the `Force Reprocess` box before scanning.
* **High-Performance GPU:** With an NVIDIA GPU (e.g., RTX 4070 Super), deep learning analysis of thousands of images and videos completes extremely fast.

---

## 6. Troubleshooting & FAQ

* **Q. First startup is taking forever.**
  * **A.** On the first run, AI models (approx. 6GB+) will be downloaded. Depending on your network speed, this may take a while. Please check the terminal for download progress logs.
* **Q. I get a "CUDA Out of Memory" error and scanning stops.**
  * **A.** Your GPU ran out of VRAM. Try closing resource-heavy applications (like games or excessive browser tabs) before scanning.
* **Q. The processing is extremely slow.**
  * **A.** The AI might be falling back to CPU. Ensure you have PyTorch installed with the correct CUDA version for your NVIDIA GPU.
* **Q. Is my data sent to external servers?**
  * **A.** No. All processing is processed completely locally. No data or images are ever sent to external servers (Fully offline & Privacy-first).

</details>
