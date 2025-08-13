# -*- coding: utf-8 -*-
import json
import numpy as np
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any, Tuple
import torch
from sklearn.preprocessing import LabelEncoder

# DB設定（techwise_2stage_fixed_db.pyから取得）
DB_CONFIG = {
    "host": "localhost",
    "database": "techwise_db",
    "user": "abeys",
    "password": ""
}

class TechBookDataLoader:
    """
    技術書データをPostgreSQLから取得し、GCN用のデータ形式に変換するクラス
    """
    
    def __init__(self):
        self.books = []
        self.category_encoder = LabelEncoder()
        self.category_mapping = {
            'AI': 0, '機械学習': 0, 'データサイエンス': 0,
            'Python': 1, 'バックエンド': 1, 'プログラミング': 1,
            'クラウド': 2, 'インフラ': 2, 'セキュリティ': 2,
            'フロントエンド': 3, 'Web開発': 3,
            'その他': 4
        }
    
    def parse_embedding_vector(self, embedding_data) -> List[float]:
        """
        PostgreSQL VECTOR型のデータをfloatのリストに変換する。
        """
        try:
            if embedding_data is None:
                return []
            
            # VECTOR型は文字列として返される場合がある
            if isinstance(embedding_data, str):
                # '[0.1, 0.2, 0.3]' 形式の文字列をパース
                embedding_data = embedding_data.strip('[]')
                return [float(x.strip()) for x in embedding_data.split(',')]
            
            # 既にリストの場合
            elif isinstance(embedding_data, list):
                # 文字列のリストの場合、結合してパース
                if len(embedding_data) > 0 and isinstance(embedding_data[0], str):
                    vector_str = ''.join(embedding_data)
                    vector_str = vector_str.strip('[]')
                    return [float(x.strip()) for x in vector_str.split(',')]
                else:
                    return [float(x) for x in embedding_data]
            
            # numpy arrayの場合
            elif hasattr(embedding_data, 'tolist'):
                return embedding_data.tolist()
            
            else:
                print(f"⚠️ 不明なembeddingデータ形式: {type(embedding_data)}")
                return []
        
        except Exception as e:
            print(f"❌ Embeddingパースエラー: {e}")
            return []
    
    def load_books_from_db(self) -> List[Dict[str, Any]]:
        """
        PostgreSQLのtechwise_dbから書籍データを読み込む。
        """
        try:
            with psycopg2.connect(**DB_CONFIG) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    query = """
                        SELECT isbn, title, subtitle, authors, publisher, published_date,
                               page_count, description, difficulty_level, tech_categories,
                               target_audience, analysis_summary, embedding
                        FROM books
                        WHERE embedding IS NOT NULL
                        ORDER BY title
                    """
                    cursor.execute(query)
                    rows = cursor.fetchall()
                    
                    books = []
                    for row in rows:
                        book_data = {
                            "id": row["isbn"],
                            "title": row["title"],
                            "subtitle": row["subtitle"] or "",
                            "authors": row["authors"] or [],
                            "publisher": row["publisher"] or "",
                            "published_date": str(row["published_date"]) if row["published_date"] else "",
                            "page_count": row["page_count"] or 0,
                            "description": row["description"] or "",
                            "difficulty_level": row["difficulty_level"] or 1,
                            "tech_categories": row["tech_categories"] or [],
                            "target_audience": row["target_audience"] or "",
                            "analysis_summary": row["analysis_summary"] or "",
                            "embedding": self.parse_embedding_vector(row["embedding"]),
                            "primary_category": self._get_primary_category(row["tech_categories"] or [])
                        }
                        books.append(book_data)
                    
                    print(f"✅ データベースから {len(books)} 冊の書籍データを取得しました")
                    return books
                    
        except psycopg2.Error as e:
            print(f"❌ データベース接続エラー: {e}")
            return []
        except Exception as e:
            print(f"❌ 予期しないエラー: {e}")
            return []
    
    def _get_primary_category(self, tech_categories: List[str]) -> str:
        """
        技術カテゴリのリストから主要カテゴリを決定する
        """
        if not tech_categories:
            return "その他"
        
        # 優先順位でカテゴリを決定
        for category in tech_categories:
            if any(keyword in category for keyword in ['AI', '機械学習', 'データサイエンス']):
                return 'AI'
            elif any(keyword in category for keyword in ['Python', 'バックエンド', 'プログラミング']):
                return 'Python'
            elif any(keyword in category for keyword in ['クラウド', 'インフラ', 'セキュリティ']):
                return 'インフラ'
            elif any(keyword in category for keyword in ['フロントエンド', 'Web']):
                return 'フロントエンド'
        
        return 'その他'
    
    def create_category_labels(self, books: List[Dict]) -> torch.Tensor:
        """
        書籍のカテゴリからラベルテンソルを作成
        """
        categories = [book["primary_category"] for book in books]
        labels = [self.category_mapping.get(cat, 4) for cat in categories]  # デフォルトは4（その他）
        return torch.tensor(labels, dtype=torch.long)
    
    def create_edge_index(self, books: List[Dict], similarity_threshold: float = 0.6) -> torch.Tensor:
        """
        書籍間の類似度に基づいてエッジインデックスを作成
        """
        from sklearn.metrics.pairwise import cosine_similarity
        
        embeddings = [book["embedding"] for book in books if book["embedding"]]
        if len(embeddings) == 0:
            return torch.empty((2, 0), dtype=torch.long)
        
        # コサイン類似度計算
        similarity_matrix = cosine_similarity(embeddings)
        
        # しきい値以上の類似度を持つペアを抽出
        edge_list = []
        n_books = len(books)
        
        for i in range(n_books):
            for j in range(i + 1, n_books):
                if similarity_matrix[i][j] >= similarity_threshold:
                    edge_list.append([i, j])
                    edge_list.append([j, i])  # 無向グラフなので双方向
        
        if len(edge_list) == 0:
            return torch.empty((2, 0), dtype=torch.long)
        
        edge_index = torch.tensor(edge_list, dtype=torch.long).t().contiguous()
        return edge_index
    
    def create_node_features(self, books: List[Dict]) -> torch.Tensor:
        """
        書籍のembeddingからノード特徴量テンソルを作成
        """
        embeddings = []
        for book in books:
            if book["embedding"] and len(book["embedding"]) == 1536:
                embeddings.append(book["embedding"])
            else:
                # embeddingが無い場合はゼロベクトル
                embeddings.append([0.0] * 1536)
        
        return torch.tensor(embeddings, dtype=torch.float)
    
    def load_graph_data(self, similarity_threshold: float = 0.6) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, List[Dict]]:
        """
        GCN用のグラフデータを読み込む
        
        Returns:
            node_features: ノード特徴量 [num_nodes, 1536]
            edge_index: エッジインデックス [2, num_edges]
            labels: ノードラベル [num_nodes]
            books: 書籍データのリスト
        """
        print("📚 技術書データを読み込み中...")
        books = self.load_books_from_db()
        
        if not books:
            raise ValueError("書籍データが取得できませんでした")
        
        print("🔗 グラフデータを構築中...")
        node_features = self.create_node_features(books)
        edge_index = self.create_edge_index(books, similarity_threshold)
        labels = self.create_category_labels(books)
        
        print(f"📊 グラフ統計:")
        print(f"  - ノード数: {len(books)}")
        print(f"  - エッジ数: {edge_index.size(1)}")
        print(f"  - 特徴量次元: {node_features.size(1)}")
        print(f"  - カテゴリ数: {len(set(labels.tolist()))}")
        
        return node_features, edge_index, labels, books

if __name__ == "__main__":
    # テスト実行
    loader = TechBookDataLoader()
    node_features, edge_index, labels, books = loader.load_graph_data()
    
    print("\n📈 データサンプル:")
    print(f"最初の書籍: {books[0]['title']}")
    print(f"カテゴリ: {books[0]['primary_category']}")
    print(f"ラベル: {labels[0].item()}")
