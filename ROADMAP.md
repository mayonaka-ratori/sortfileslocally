# 🚀 Local Curator Prime - Future Update Plan (Roadmap)

Local Curator Primeをさらに洗練されたプロフェッショナルなツール・アプリケーションへと引き上げるための、今後のアップデートと改善計画をまとめました。
完全ローカル・プライバシー保護の原則を維持したまま、「自分のための最高のツール」から「同じニーズを持つ人に届けられるプロダクト」への成長を段階的に計画しています。

---

## 🌐 5. 公開・配布の成熟 (Distribution & Public Release)

同じニーズ（プライバシーを守りながらAIでメディア管理）を持つユーザーに届けるための準備です。

### 5.1 デスクトップアプリ化 (Native Desktop Packaging)
- **Tauri + PyInstaller** でバックエンド同梱 of 単一実行ファイル化。
- Windows `.msi`、Mac `.dmg`、Linux `.AppImage` で配布。
- Python・Node.jsの事前インストール不要に。
- GPUドライバの検出・案内をウィザードに統合。

### 5.2 初回体験の磨き込み (First-Run Experience Polish)
- デモモード: サンプル画像10枚で検索体験を試せる導入。
- スキャン中の具体的な残り時間表示（「150/3000枚 — 残り約12分」）。
- 初回スキャン完了後の誘導（「まずは検索してみましょう」）。

### 5.3 多言語対応 (Internationalization)
- next-intl による日英切り替え対応。
- UI全体のi18nキー化。

### 5.4 プライバシー透明性 (Privacy Transparency)
- 「完全ローカル」「データ送信なし」「アカウント不要」を明示するUI。
- 起動時のネットワーク通信ログを出力し、ユーザーが検証可能に。
- README・ランディングページでプライバシーを前面に。

### 5.5 自動アップデート機能 (Auto-Update)
- Tauri の組み込みアップデーターを利用。
- ユーザーに通知 → ワンクリックでアップデート適用。

### 5.6 テスト基盤強化 (Test Infrastructure)
- E2Eテスト（Playwright）の導入。
- プロファイル別テスト（performance / balanced / lightweight）。
- CI/CDパイプライン構築（GitHub Actions）。

---

## ✅ 完了済みセクション (Completed)

以下のセクションは実装・テスト・レビュー・ドキュメント更新がすべて完了しています。

### 🏷 4. タグ管理・検索体験の深化 (Tag Management & Search Experience)

#### [✅] 4.1 検索履歴機能 (Search History)
- UPSERT方式の履歴保存（100件限度）と検索バー連動ドロップダウン実装。

#### [✅] 4.2 タグダッシュボード (Tag Dashboard)
- 使用統計・未タグ抽出・一括リネーム機能の実装。

#### [✅] 4.3 インラインタグ編集 (Inline Tag Editor)
- 詳細ビューでの即時編集、オートコンプリート、カテゴリ切替対応。

#### [✅] 4.4 一括タグ操作 (Bulk Tag Operations)
- 複数選択からのタグ追加/削除/置換。トランザクションによる整合性確保。

#### [✅] 4.5 AIタグ再生成 (AI Tag Regeneration)
- 単一/複数ファイルへのAI再スキャン（上書き・追記モード選択可能）。

#### [✅] 4.6 AI提案型インテリジェンス (AI-Powered Insights)
- 整理提案（重複・未タグ等）のカード表示とワンクリック遷移。

#### [✅] 4.7 動画シーン分割 (Video Scene Segmentation)
- シーン単位のCLIP検索・タイムライン表示・メモリ最適化済み。

#### [✅] 4.8 キーボードショートカット (Keyboard Shortcuts)
- ギャラリー・詳細ビュー全域の操作。useRef + EventListenerによる最適化実装。

#### [✅] 4.9 オフライン動作保証 (Offline Guarantee)
- ネットワーク監視UIおよびオフライン時のAPIエラーハンドリング強化。

### 🛠 1. エンジニアリング & アーキテクチャ強化 (Engineering & Architecture)

#### [✅] 1.1 デプロイメントと起動プロセスの統合 (Desktop App Launcher)
- `start.bat` (Windows) / `start.sh` (Linux/Mac) でバックエンド＋フロントエンド一括起動。

#### [✅] 1.2 高度なモデル管理システム (Model Manager)
- ModelManagerクラス、ダウンロードAPI・UI、プログレス表示、カスタム保存先設定、再起動通知UX。

#### [✅] 1.3 スキャン非同期ジョブキューとレジューム機能 (Async Job Queue & Resume)
- SQLiteベースジョブ管理、レジューム機能、エラースキップログ。

#### [✅] 1.4 重複排除・類似画像検索 (Deduplication & Reverse Search)
- 重複検出エンジン、逆画像検索、クリーナーUI、メタデータマージ、XMPサイドカー連動削除。

#### [✅] 1.5 メタデータ書き戻し機能 (EXIF/IPTC Write-back)
- XMP/EXIF書き込み、フォーマット選択UI、バルクエクスポート（500件上限）、EXIFフォールバック。

### 🧠 2. AIモデル・推論エンジンの進化 (AI Models & Inference)

#### [✅] 2.1 高精度イラストタグ付け (Advanced Illustration Tagging)
- JoyTag導入。ポーズ・服装・背景要素の正確なタグ抽出。

#### [✅] 2.2 小規模VLMによるキャプション強化 (Enhanced Captioning)
- Florence-2導入。実写・イラスト両対応の詳細キャプション生成。

#### [✅] 2.3 顔認識と検索 (Face Retrieval Search)
- InsightFace (RetinaFace + ArcFace) による顔認識・登録・検索機能。

### 🎨 3. UI/UX・デザイン体験の向上 (Design & User Experience)

#### [✅] 3.1 オンボーディングの洗練 (Premium Setup Experience)
- 5ステップウィザード、next-themesテーマ切替、実行プロファイル（Performance/Balanced/Lightweight）、フォルダピッカー。

#### [✅] 3.2 ハイブリッドクエリビルダー (Advanced Hybrid Search UI)
- FAISS+SQLiteのTiered検索、フィルタチップUI、JSON body API、スコア閾値フィルタリング。

#### [✅] 3.3 スマートアルバム機能 (Smart Dynamic Albums)
- 静的/動的アルバム、検索条件JSON保存、アルバムCRUD、Pydanticバリデーション。

#### [✅] 3.4 没入感のあるギャラリーUX (Immersive Masonry Gallery)
- Pinterest風Masonryレイアウト、動画ホバープレビュー。
