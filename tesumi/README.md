# Tesumi System v2.0 - API版かなた（テスミちゃん）

記憶継承システムの完全自動化と生成AIとの文脈連携による自然な対話システム

## 概要

本プロジェクトは、Memory-Augmented GNN（グラフニューラルネットワーク）を用いた記憶継承システムです。Claude APIを中心とした軽量かつ高効率なLLM基盤により、記憶の保持・活性化・文脈連携を実現します。

### 主な特徴

- **記憶継承システム**: GNNによる記憶保持と活性化
- **Claude API統合**: 自然な対話生成
- **Memolette機能**: PostgreSQL + pgvectorによる記憶データベース管理
- **感情モデル**: Valence-Arousalモデルによる感情座標
- **日報生成**: KanaRe-1.1による自動要約・記録
- **月額コスト削減**: 85%削減（3,000円 → 410円）を実現

## 技術構成

| コンポーネント | 技術 |
|---------------|------|
| **LLM** | Claude API (Haiku 3.5) |
| **データベース** | PostgreSQL + pgvector |
| **記憶管理** | Memory-Augmented GNNs |
| **GNN** | GraphSAGE + GAT + GRU |
| **埋め込み** | Sentence-BERT (384次元) |
| **バックエンド** | FastAPI + SQLAlchemy |
| **コンテナ** | Docker + Docker Compose |

## アーキテクチャ

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   User Input    │───▶│  Claude API     │───▶│   Response      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       ▲                       │
         ▼                       │                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Memory Search   │───▶│ GNN Processor   │───▶│Memory Database  │
│ (Vector + GNN)  │    │(GraphSAGE+GRU) │    │(PostgreSQL+    │
└─────────────────┘    └─────────────────┘    │ pgvector)       │
                                              └─────────────────┘
```

## 記憶ノード構造

各記憶ノードは以下の情報を持ちます：

- **埋め込みベクトル**: 384次元（Sentence-BERT）
- **感情座標**: Valence（感情価）、Arousal（覚醒度）
- **時間情報**: 作成日時、最終アクセス日時
- **活性化強度**: 記憶の重要度・使用頻度
- **GRU状態**: 内部記憶のための隠れ状態

## セットアップ

### 必要な環境

- Python 3.11+
- PostgreSQL 15+ (pgvector拡張)
- Docker & Docker Compose
- Claude API キー

### インストール

1. **リポジトリのクローン**
```bash
git clone <repository-url>
cd tesumi-system2
```

2. **環境変数の設定**
```bash
cp .env.example .env
# .envファイルを編集してClaude APIキーを設定
```

3. **Docker Composeでの起動**
```bash
docker-compose up -d
```

4. **ローカル開発環境での起動**
```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

### 環境変数

重要な設定項目：

```env
CLAUDE_API_KEY=your_claude_api_key_here
DATABASE_URL=postgresql+asyncpg://tesumi:tesumi_password@localhost:5432/tesumi_db
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

## API エンドポイント

### 会話API

- `POST /api/conversation/chat` - メイン会話エンドポイント
- `GET /api/conversation/sessions/{session_id}/history` - 会話履歴取得
- `POST /api/conversation/sessions/{session_id}/reset` - セッションリセット

### 記憶管理API

- `POST /api/memory/nodes` - 記憶ノード作成
- `GET /api/memory/search` - 記憶検索
- `GET /api/memory/statistics` - 記憶統計情報
- `POST /api/memory/cleanup` - 古い記憶のクリーンアップ

### 日報生成API

- `POST /api/report/generate` - 日報生成（KanaRe-1.1）
- `GET /api/report/history` - 日報履歴
- `GET /api/report/analytics` - 分析データ

## 使用例

### 基本的な会話

```python
import requests

response = requests.post("http://localhost:8000/api/conversation/chat", json={
    "message": "今日はいい天気ですね",
    "session_id": "user-session-123"
})

print(response.json()["response"])
```

### 記憶の作成

```python
response = requests.post("http://localhost:8000/api/memory/nodes", json={
    "content": "今日は友人と映画を見に行った。とても楽しかった。",
    "memory_type": "episodic",
    "category": "leisure",
    "valence": 0.8,
    "arousal": 0.6
})
```

### 記憶の検索

```python
response = requests.get("http://localhost:8000/api/memory/search", params={
    "query": "映画",
    "limit": 10
})

memories = response.json()["results"]
```

## GNN（グラフニューラルネットワーク）

### Memory-Augmented GNNs

本システムでは以下の論文をベースにしたMemory-Augmented GNNsを実装：

- **GraphSAGE**: ノード特徴の集約
- **GRU Units**: 各ノードの内部記憶
- **Attention機構**: 記憶の重み付け統合
- **外部記憶**: Key-Valueメモリ構造

### 記憶活性化プロセス

1. 入力クエリの埋め込み生成
2. ベクトル類似度による候補記憶抽出
3. GNNによる記憶グラフの処理
4. 活性化スコアの計算
5. Top-K記憶の選択と文脈生成

## 日報生成（KanaRe-1.1）

自動日報生成機能：

- **記憶抽出**: その日の記憶を自動収集
- **感情分析**: Valence-Arousalによる感情状態分析
- **要約生成**: Claudeによる自然な日報生成
- **キー記憶**: 重要な記憶のハイライト

## モニタリング

### ヘルスチェック

- `GET /health` - システム健康状態
- `GET /api/memory/statistics` - 記憶システム統計

### ログ

アプリケーションログは構造化されており、以下を含みます：
- 記憶作成・アクセス
- GNN処理統計
- Claude API使用状況
- エラー・例外情報

## 開発

### テスト

```bash
pytest tests/
```

### コード品質

```bash
black app/  # フォーマット
flake8 app/  # リント
```

### 貢献

1. Forkしてfeatureブランチを作成
2. 変更を実装
3. テストを追加・実行
4. Pull Requestを提出

## パフォーマンス最適化

### データベース

- pgvectorインデックスによる高速ベクトル検索
- 適切な接続プーリング
- 記憶のLRU管理

### GNN処理

- バッチ処理によるGPU活用
- メモリ効率的な実装
- キャッシュシステム

## トラブルシューティング

### よくある問題

1. **Claude API エラー**: APIキーの確認
2. **データベース接続エラー**: PostgreSQLの起動確認
3. **メモリ不足**: バッチサイズの調整
4. **pgvector エラー**: 拡張の有効化確認

### ログの確認

```bash
docker-compose logs tesumi-api
docker-compose logs postgres
```

## ライセンス

このプロジェクトは[ライセンス名]の下で公開されています。

## 参考文献

- Memory-Augmented GNNs: A Brain-Inspired Review
- COGMEN: Contextualized GNN for Multimodal Emotion Recognition
- GraphSAGE: Inductive Representation Learning on Large Graphs

---

**Tesumi System v2.0** - 記憶を通じて成長し続けるAIシステム
