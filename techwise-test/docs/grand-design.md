# Phase2：PyTorch GeometricでGCN実装

## 使用技術

- **PyTorch Geometric**: GNN専用ライブラリ
- **GCN (Graph Convolutional Network)**: 基本的なGNNモデル

## 実装ステップ

### 1. データ準備

```python
class BookGraphDataset:
    def __init__(self, books, embeddings):
        self.x = torch.tensor(embeddings)  # ノード特徴量
        self.edge_index = self.build_edges()  # エッジ情報
```

### 2. GCNモデル定義

```python
class BookGCN(torch.nn.Module):
    def __init__(self, input_dim, hidden_dim, output_dim):
        self.conv1 = GCNConv(input_dim, hidden_dim)
        self.conv2 = GCNConv(hidden_dim, output_dim)
```

### 3. 学習タスク

- **ノード分類**: 「この本はReact本？AI本？」
- **リンク予測**: 「この2冊は関連している？」

## 期待する効果

- 書籍間の潜在的関係性発見
- タナカさんの好み予測精度向上
- 新刊書籍の自動カテゴリ分類

---

# Phase2：PyTorch Geometric GCN実装 詳細設計

## 実装目標

TechWiseの150冊技術書データを使って、書籍推薦精度向上とカテゴリ自動分類を実現するGCNシステム

## 技術スタック

- `torch >= 1.9.0`
- `torch-geometric >= 2.0.0`
- `scikit-learn`
- `pandas`
- `numpy`
- `matplotlib`
- `networkx`

## データ準備仕様

```python
class BookGraphData:
    # ノード特徴量：[1536次元OpenAI Embedding]
    # エッジ特徴量：[コサイン類似度, 著者一致, 出版社一致, カテゴリ類似度]
    # ラベル：[カテゴリID（0:フロントエンド, 1:バックエンド, 2:インフラ, 3:データサイエンス, 4:AI/ML）]
```

## GCNモデル設計

```python
class TechBookGCN(torch.nn.Module):
    def __init__(self):
        # Layer1: 1536 → 512 (特徴抽出)
        # Layer2: 512 → 128 (中間表現)  
        # Layer3: 128 → 5 (カテゴリ分類)
        # Dropout: 0.2 (過学習防止)
```

## 学習タスク

- **ノード分類**: 書籍カテゴリ予測（精度目標85%以上）
- **リンク予測**: 未知の書籍関係性発見
- **埋め込み獲得**: 推薦システム用特徴量抽出

## 評価手法

- 交差検証（5-fold）
- Phase1 NetworkX結果との比較
- ソフィーちゃん推薦精度との比較
