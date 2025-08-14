# TechWise GCN実装

PyTorch GeometricでGCN実装.txtに基づいた、実用的で拡張性の高いGraph Convolutional Network (GCN)実装システムです。

## 🎯 プロジェクト概要

技術書データベース（PostgreSQL）から50冊の技術書データを取得し、GCNモデルを用いて書籍のカテゴリ分類・推薦システムを構築します。

### 実装内容

- **Phase1**: データ分析とグラフ統計
- **Phase2**: GCN/GATモデル学習（カテゴリ分類 85%以上目標）
- **Phase3**: 学習済みモデルによる推薦システム
- **Phase4**: NetworkXとの比較分析

### 使用技術

- **PyTorch Geometric**: GNN専用ライブラリ
- **PostgreSQL**: techwise_dbから技術書データ取得
- **GCN/GAT**: Graph Convolutional Networks
- **scikit-learn**: 評価メトリクス

## 🏗️ システム構成

```
techwise-test/
├── src/                       # ソースコード
│   ├── main.py                # メイン実行スクリプト
│   ├── data_loader.py         # PostgreSQLデータ取得
│   ├── gcn_model.py           # GCN/GATモデル定義
│   ├── trainer.py             # 学習・評価システム
│   ├── recommendation_system.py # 推薦システム実装
│   └── simple_demo.py         # デモスクリプト
├── data/                      # データファイル
│   └── book_embeddings_gcn.npy # 書籍埋め込みベクトル
├── models/                    # 学習済みモデル
│   ├── GCN_best_model.pt      # GCN学習済みモデル
│   └── GAT_best_model.pt      # GAT学習済みモデル
├── results/                   # 実行結果・可視化
│   ├── *_training_curves.png  # 学習曲線
│   ├── *_confusion_matrix.png # 混同行列
│   └── *.json                 # 結果JSON
├── docs/                      # ドキュメント
│   └── INSTALLATION_GUIDE.md  # インストールガイド
├── requirements.txt           # 依存関係
├── .gitignore                 # Git除外設定
├── LICENSE                    # ライセンス
└── README.md                  # このファイル
```

### データモデル

- **ノード特徴量**: 1536次元OpenAI Embedding
- **エッジ**: コサイン類似度（しきい値設定可能）
- **ラベル**: 5カテゴリ（AI/ML, Python/Backend, Infrastructure, Frontend, Other）

### モデルアーキテクチャ

#### GCNモデル
```
Layer1: 1536 → 512  (特徴抽出)
Layer2: 512 → 128   (中間表現)
Layer3: 128 → 5     (カテゴリ分類)
Dropout: 0.2        (過学習防止)
```

#### GATモデル (オプション)
```
Attention heads: 8
同様の構造でAttentionメカニズム付き
```

## 🚀 セットアップ

### 1. 依存関係のインストール

```bash
cd techwise-test
pip install -r requirements.txt
```

### データベース接続確認

PostgreSQLのtechwise_dbに接続可能であることを確認：

```bash
python -c "from src.data_loader import TechBookDataLoader; loader = TechBookDataLoader(); books = loader.load_books_from_db(); print(f'取得した書籍数: {len(books)}')"
```

## 🎮 使用方法

### 完全パイプライン実行

```bash
# GCNモデルのみで300エポック学習
python src/main.py --epochs 300

# GCN + GATモデル比較
python src/main.py --epochs 300 --include-gat

# 類似度しきい値を調整
python src/main.py --similarity-threshold 0.4 --epochs 200
```

### 推薦システムのみ実行

```bash
python src/main.py --demo-only
```

### 個別コンポーネント実行

```bash
# データローダーテスト
python src/data_loader.py

# GCNモデルテスト
python src/gcn_model.py

# 学習のみ実行
python src/trainer.py

# 推薦システムテスト
python src/recommendation_system.py

# デモスクリプト実行
python src/simple_demo.py
```

## 📊 出力結果

### 学習結果
- `GCN_best_model.pt` / `GAT_best_model.pt`: 学習済みモデル
- `gcn_results.json` / `gat_results.json`: 学習結果JSON
- `GCN_training_curves.png`: 学習曲線
- `GCN_confusion_matrix.png`: 混同行列

### 推薦システム
- 類似書籍推薦
- キーワードベース検索
- パーソナライズ推薦
- カテゴリ予測

### 総合結果
- `techwise_gcn_results.json`: 全フェーズの結果
- `book_embeddings_gcn.npy`: 書籍埋め込みベクトル

## 🔍 推薦システムAPI

### 1. 類似書籍推薦
```python
recommender = GCNRecommendationSystem()
recommender.load_model_and_data()

# 書籍インデックス0に類似した5冊を推薦
recommendations = recommender.find_similar_books(
    book_index=0, 
    n_recommendations=5
)
recommender.print_recommendations(recommendations)
```

### 2. キーワード検索
```python
# キーワードで検索
results = recommender.recommend_by_query(
    query_keywords=["Python", "機械学習", "AI"],
    n_recommendations=5
)
```

### 3. パーソナライズ推薦
```python
# ユーザーの読書履歴から推薦
user_books = [0, 5, 10]  # 読んだ書籍のインデックス
personalized = recommender.personalized_recommendations(
    user_book_indices=user_books,
    n_recommendations=10
)
```

### 4. カテゴリ予測
```python
# 書籍のカテゴリを予測
category, confidence = recommender.predict_category(book_index=0)
print(f"予測カテゴリ: {category} (信頼度: {confidence:.3f})")
```

## 📈 評価指標

### 学習タスク
- **ノード分類精度**: 85%以上目標
- **交差検証**: 5-fold対応
- **メトリクス**: Accuracy, Precision, Recall, F1-score

### 推薦システム
- **類似度計算**: コサイン類似度
- **多様性**: カテゴリ分散考慮
- **パーソナライズ**: ユーザー嗜好学習

## 🛠️ カスタマイズ

### データローダー修正
```python
# data_loader.py
class TechBookDataLoader:
    def __init__(self):
        # カテゴリマッピングの変更
        self.category_mapping = {
            'Custom1': 0,
            'Custom2': 1,
            # ...
        }
```

### モデル構造変更
```python
# gcn_model.py
model = TechBookGCN(
    input_dim=1536,
    hidden_dim=1024,  # 隠れ層サイズ変更
    intermediate_dim=256,
    output_dim=5,
    dropout=0.1  # Dropout率変更
)
```

### 類似度しきい値調整
```python
# より多くのエッジを作成（密なグラフ）
similarity_threshold = 0.3

# より疎なグラフ
similarity_threshold = 0.7
```

## 🐛 トラブルシューティング

### CUDA関連エラー
```bash
# CPU only mode
export CUDA_VISIBLE_DEVICES=""
python main.py --epochs 100
```

### PostgreSQL接続エラー
```python
# data_loader.pyのDB_CONFIGを確認
DB_CONFIG = {
    "host": "localhost",
    "database": "techwise_db", 
    "user": "your_user",
    "password": "your_password"
}
```

### メモリ不足
```python
# バッチサイズやモデルサイズを削減
model = TechBookGCN(hidden_dim=256, intermediate_dim=64)
```

## 📚 参考資料

- [PyTorch Geometric Documentation](https://pytorch-geometric.readthedocs.io/)
- [Graph Convolutional Networks (Kipf & Welling, 2017)](https://arxiv.org/abs/1609.02907)
- [Graph Attention Networks (Veličković et al., 2018)](https://arxiv.org/abs/1710.10903)

## 🤝 貢献

プルリクエストや課題報告を歓迎します。以下の点にご注意ください：

1. コードスタイル: PEP8準拠
2. テスト: 新機能には適切なテストを追加
3. ドキュメント: README更新

## 📄 ライセンス

MIT License

## 🎉 完了チェックリスト

- [x] データベースからの技術書データ取得
- [x] GCN/GATモデル実装
- [x] 学習・評価システム
- [x] 推薦システム実装
- [x] 5段階カテゴリ分類
- [x] 可視化（学習曲線、混同行列）
- [x] コマンドライン引数対応
- [x] エラーハンドリング
- [x] 詳細ドキュメント

---

**作成者**: Warp AI Assistant  
**最終更新**: 2025年8月11日
