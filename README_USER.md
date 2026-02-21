# LocalCurator Prime 取扱説明書 / User Manual

LocalCurator Primeは、AI（VLMおよび音声認識）を活用して、PC内の大量の画像や動画を自動で整理、文脈検索、そしてチャットで内容を分析するための次世代ローカル・メディア管理ツールです。
LocalCurator Prime is a next-generation local media management tool that utilizes AI (Vision-Language Models and Speech Recognition) to automatically organize, semantically search, and analyze your massive local image and video collections.

---

## 1. 起動方法 / How to Start

WebブラウザベースのモダンなUIを採用しています。バックエンド（AIエンジン）とフロントエンド（UI）の両方を起動する必要があります。
This application uses a modern web-browser based UI. You need to start both the backend (AI Engine) and frontend (UI).

### バックエンド (FastAPI / AI Engine)
ターミナルを開き、プロジェクトフォルダで以下を実行します。
Open a terminal, navigate to the project folder, and run:
```powershell
# Pythonの仮想環境を有効化 (任意) / Activate venv (optional)
# .\venv\Scripts\activate

cd server
python main.py
```

### フロントエンド (Next.js / Web UI)
別のターミナルを開き、`web` フォルダに移動して以下を実行します。
Open a new terminal, navigate to the `web` folder, and run:
```powershell
cd web
npm run dev
```

起動後、ブラウザで `http://localhost:3000` にアクセスしてください。
After starting, open your browser and navigate to `http://localhost:3000`.

---

## 2. 基本操作フロー / Basic Workflow

### ステップ1：スキャン / Step 1: Scan
1. 左側のサイドバー上部にある **「Folder Scanner」** に、整理したい画像・動画が入っているフォルダのパスを入力します。
   In the **Folder Scanner** section near the top of the left sidebar, enter the path to the folder containing your media.
2. **「Start Scan」** ボタンをクリックします。プログレスバーでリアルタイムの進捗や残り時間（ETA）が確認できます。
   Click the **Start Scan** button. You can monitor the real-time progress and ETA via the progress bar.
3. AIが各ファイル（動画含む）を解析し、内容、タグ、音声などをデータベースに登録します。
   The AI will analyze each file (including videos) and register its contents, tags, and audio transcriptions to the database.

### ステップ2：検索と閲覧 / Step 2: Search and Browse
1. 画面上部の検索バーに **「海辺を沈む夕日」** や **「雨の中で笑う女の子」** など、自然言語を入力してEnterを押します。
   In the top search bar, enter natural language queries like **"sunset at the beach"** or **"girl laughing in the rain"** and press Enter.
2. 文脈を理解したAIが、類似度の高い順にメディアを表示します。動画の音声やシーン解説にヒットした場合は、対象の「スニペット（抜粋）」が表示されます。
   The AI understands the context and displays media in order of semantic similarity. If a video's audio or scene description matches, a text snippet of the exact moment will be displayed.

---

## 3. 主要機能の紹介 / Key Features

### 🔍 Semantic Search（セマンティック検索）
* **概要 / Overview:** ファイル名や手付けのタグではなく、「意味」や「文脈」で検索します。動画内のセリフやアクションも検索対象です。
  Search by "meaning" or "context" rather than exact filenames or manual tags. Dialogue and actions inside videos are also searchable.

### 🎬 Video Understanding（動画・音声理解）
* **概要 / Overview:** 動画からキーフレームを抽出してAIが状況を説明（Moondream2）し、音声は文字起こし（Whisper）してデータベース化します。動画にカーソルを合わせると自動でプレビュー再生されます。
  Extracts keyframes from videos for AI scene description (Moondream2), and transcribes audio (Whisper). Hover over a video thumbnail to instantly preview it.

### 🏷️ Auto Tagging & Filtering（自動タグ付けとフィルタ）
* **概要 / Overview:** キャラクター名、シリーズ名、一般タグなどを自動推論。左側のサイドバーで「画像のみ / 動画のみ」やキャラクターごとの絞り込みがワンクリックで行えます。
  Automatically infers character names, series, and general tags. Use the left sidebar to filter down by "Images only / Videos only" or by specific characters with a single click.

### 💬 Chat with Media（メディアとの対話）
* **概要 / Overview:** ギャラリー内の画像をクリックして右側のチャットパネルを開くと、AIに「この画像には何が描かれていますか？」「このテキストを翻訳して」など直接質問が可能です。
  Click an image to open the right chat panel and directly ask the AI questions like "What is drawn in this image?" or "Translate this text for me."

---

## 4. プロフェッショナルな使い方のコツ / Pro Tips

* **Force Reprocess (強制再スキャン):** 以前スキャンしたフォルダでも、アプリの新機能（動画の音声解析など）を適用したい場合は、スキャン画面の `Force Reprocess` にチェックを入れてスキャンしてください。
  If you want to apply new AI features (like video audio analysis) to a previously scanned folder, check the `Force Reprocess` box before scanning.
* **高性能GPU / High-Performance GPU:** NVIDIA GPU (RTX 4070 Super等) を搭載した環境であれば、数千枚のメディアや動画のディープラーニング解析も極めて高速に完了します。
  With an NVIDIA GPU (e.g., RTX 4070 Super), deep learning analysis of thousands of images and videos completes extremely fast.

---

## 5. 注意事項 / Important Notes

* すべての処理は**ローカル環境**で完結しており、外部サーバーにデータや画像が送信されることはありません（完全オフライン＆プライバシー保護）。
  All processing is done completely **locally**. No data or images are ever sent to external servers (Fully offline & Privacy-first).
* 初回起動時はAIモデルのダウンロード（約6GB〜）が行われるため、ネットワーク環境によっては起動に時間がかかります。
  On the first run, AI models (approx. 6GB+) will be downloaded, so startup may take some time depending on your network speed.
