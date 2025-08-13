#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TechWise GCN 簡易デモ (PyTorch不要バージョン)
データ取得と基本的な分析機能のデモンストレーション
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import numpy as np
import json
from typing import List, Dict, Any, Tuple
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import LabelEncoder
import matplotlib.pyplot as plt
import seaborn as sns

# DB設定
DB_CONFIG = {
    "host": "localhost",
    "database": "techwise_db",
    "user": "abeys",
    "password": ""
}

class SimpleTechBookAnalyzer:
    """
    PyTorch不要のシンプルな技術書分析システム
    """
    
    def __init__(self):
        self.books = []
        self.embeddings = []
        self.category_mapping = {
            'AI': 0, '機械学習': 0, 'データサイエンス': 0,
            'Python': 1, 'バックエンド': 1, 'プログラミング': 1,
            'クラウド': 2, 'インフラ': 2, 'セキュリティ': 2,
            'フロントエンド': 3, 'Web開発': 3,
            'その他': 4
        }
        self.category_names = ['AI/ML', 'Python/Backend', 'Infrastructure', 'Frontend', 'Other']
        
        print("🚀 SimpleTechBookAnalyzer初期化完了")
    
    def parse_embedding_vector(self, embedding_data) -> List[float]:
        """PostgreSQL VECTOR型のデータを解析"""
        try:
            if embedding_data is None:
                return []
            
            if isinstance(embedding_data, str):
                embedding_data = embedding_data.strip('[]')
                return [float(x.strip()) for x in embedding_data.split(',')]
            elif isinstance(embedding_data, list):
                if len(embedding_data) > 0 and isinstance(embedding_data[0], str):
                    vector_str = ''.join(embedding_data)
                    vector_str = vector_str.strip('[]')
                    return [float(x.strip()) for x in vector_str.split(',')]
                else:
                    return [float(x) for x in embedding_data]
            elif hasattr(embedding_data, 'tolist'):
                return embedding_data.tolist()
            else:
                return []
        except Exception as e:
            print(f"❌ Embeddingパースエラー: {e}")
            return []
    
    def _get_primary_category(self, tech_categories: List[str]) -> str:
        """技術カテゴリから主要カテゴリを決定"""
        if not tech_categories:
            return "その他"
        
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
    
    def load_books_from_db(self) -> List[Dict[str, Any]]:
        """データベースから書籍データを取得"""
        print("📚 データベースから書籍データを読み込み中...")
        
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
                    embeddings = []
                    
                    for row in rows:
                        embedding = self.parse_embedding_vector(row["embedding"])
                        if len(embedding) == 1536:  # 有効なembeddingのみ
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
                                "primary_category": self._get_primary_category(row["tech_categories"] or [])
                            }
                            books.append(book_data)
                            embeddings.append(embedding)
                    
                    self.books = books
                    self.embeddings = np.array(embeddings)
                    
                    print(f"✅ {len(books)} 冊の書籍データを取得しました")
                    print(f"  - 埋め込みベクトル形状: {self.embeddings.shape}")
                    
                    return books
                    
        except Exception as e:
            print(f"❌ データベース接続エラー: {e}")
            return []
    
    def analyze_data_distribution(self):
        """データ分布を分析"""
        print("\n📊 データ分布分析")
        print("=" * 50)
        
        # カテゴリ分布
        category_counts = {}
        difficulty_counts = {}
        
        for book in self.books:
            cat = book['primary_category']
            category_counts[cat] = category_counts.get(cat, 0) + 1
            
            diff = book['difficulty_level']
            difficulty_counts[diff] = difficulty_counts.get(diff, 0) + 1
        
        print("📚 カテゴリ分布:")
        for category, count in sorted(category_counts.items()):
            percentage = (count / len(self.books)) * 100
            print(f"  - {category}: {count}冊 ({percentage:.1f}%)")
        
        print("\n🎯 難易度分布:")
        for level in sorted(difficulty_counts.keys()):
            count = difficulty_counts[level]
            percentage = (count / len(self.books)) * 100
            print(f"  - レベル{level}: {count}冊 ({percentage:.1f}%)")
        
        return category_counts, difficulty_counts
    
    def build_similarity_graph(self, threshold: float = 0.6) -> Tuple[np.ndarray, int]:
        """類似度グラフを構築"""
        print(f"\n🔗 類似度グラフ構築 (しきい値: {threshold})")
        print("=" * 50)
        
        # コサイン類似度計算
        similarity_matrix = cosine_similarity(self.embeddings)
        
        # エッジ数計算
        edges = 0
        edge_list = []
        
        for i in range(len(self.books)):
            for j in range(i + 1, len(self.books)):
                if similarity_matrix[i][j] >= threshold:
                    edges += 2  # 無向グラフなので双方向
                    edge_list.append((i, j, similarity_matrix[i][j]))
        
        print(f"📈 グラフ統計:")
        print(f"  - ノード数: {len(self.books)}")
        print(f"  - エッジ数: {edges}")
        print(f"  - 密度: {edges / (len(self.books) * (len(self.books) - 1)):.6f}")
        print(f"  - 接続ペア数: {len(edge_list)}")
        
        return similarity_matrix, len(edge_list)
    
    def find_similar_books(self, book_index: int, n_recommendations: int = 5) -> List[Dict]:
        """類似書籍を検索"""
        if len(self.embeddings) == 0:
            return []
        
        target_embedding = self.embeddings[book_index].reshape(1, -1)
        similarities = cosine_similarity(target_embedding, self.embeddings)[0]
        
        # 自分自身を除外
        similarities[book_index] = -1
        
        # 類似度順にソート
        similar_indices = np.argsort(similarities)[::-1]
        
        recommendations = []
        for i, idx in enumerate(similar_indices[:n_recommendations]):
            if similarities[idx] < 0.3:  # 最低類似度
                break
            
            rec = {
                'rank': i + 1,
                'book_index': int(idx),
                'title': self.books[idx]['title'],
                'authors': self.books[idx]['authors'],
                'publisher': self.books[idx]['publisher'],
                'similarity_score': float(similarities[idx]),
                'category': self.books[idx]['primary_category'],
                'difficulty_level': self.books[idx]['difficulty_level']
            }
            recommendations.append(rec)
        
        return recommendations
    
    def recommend_by_keywords(self, keywords: List[str], n_recommendations: int = 5) -> List[Dict]:
        """キーワードベース推薦"""
        book_scores = []
        
        for i, book in enumerate(self.books):
            score = 0.0
            
            # タイトルマッチング
            title_words = book['title'].lower().split()
            for keyword in keywords:
                if any(keyword.lower() in word for word in title_words):
                    score += 2.0
            
            # カテゴリマッチング
            for category in book['tech_categories']:
                for keyword in keywords:
                    if keyword.lower() in category.lower():
                        score += 1.5
            
            # 説明文マッチング
            if book['description']:
                description = book['description'].lower()
                for keyword in keywords:
                    if keyword.lower() in description:
                        score += 1.0
            
            book_scores.append((i, score))
        
        # スコア順にソート
        book_scores.sort(key=lambda x: x[1], reverse=True)
        
        recommendations = []
        for rank, (book_index, score) in enumerate(book_scores[:n_recommendations]):
            if score == 0:
                break
            
            rec = {
                'rank': rank + 1,
                'book_index': book_index,
                'title': self.books[book_index]['title'],
                'authors': self.books[book_index]['authors'],
                'match_score': score,
                'category': self.books[book_index]['primary_category'],
                'difficulty_level': self.books[book_index]['difficulty_level']
            }
            recommendations.append(rec)
        
        return recommendations
    
    def print_recommendations(self, recommendations: List[Dict], title: str = "推薦結果"):
        """推薦結果を表示"""
        print(f"\n📚 {title} ({len(recommendations)}冊):")
        print("=" * 80)
        
        for rec in recommendations:
            print(f"\n{rec['rank']}. {rec['title']}")
            authors = ', '.join(rec['authors']) if rec['authors'] else '不明'
            print(f"   著者: {authors}")
            print(f"   カテゴリ: {rec['category']}")
            print(f"   難易度: {rec['difficulty_level']}")
            
            if 'similarity_score' in rec:
                print(f"   類似度: {rec['similarity_score']:.3f}")
            if 'match_score' in rec:
                print(f"   マッチスコア: {rec['match_score']:.1f}")
        
        print("\n" + "=" * 80)
    
    def demo_system(self):
        """システムデモを実行"""
        print("🎬 TechWise 簡易GCNシステム デモ")
        print("=" * 80)
        
        # データ読み込み
        if len(self.books) == 0:
            self.load_books_from_db()
        
        if len(self.books) == 0:
            print("❌ データが取得できませんでした")
            return
        
        # データ分析
        self.analyze_data_distribution()
        
        # グラフ構築
        similarity_matrix, edge_count = self.build_similarity_graph(threshold=0.6)
        
        # 1. 類似書籍推薦デモ
        print("\n🔍 1. 類似書籍推薦デモ")
        target_index = 0
        target_book = self.books[target_index]
        print(f"基準書籍: {target_book['title']}")
        print(f"カテゴリ: {', '.join(target_book['tech_categories'])}")
        
        similar_books = self.find_similar_books(target_index, n_recommendations=3)
        self.print_recommendations(similar_books, "類似書籍")
        
        # 2. キーワード検索デモ
        print("\n🔍 2. キーワード検索デモ")
        keywords = ["Python", "機械学習", "AI"]
        print(f"検索キーワード: {keywords}")
        
        keyword_results = self.recommend_by_keywords(keywords, n_recommendations=3)
        self.print_recommendations(keyword_results, "キーワード検索結果")
        
        # 3. システム統計
        print("\n📊 システム統計:")
        print(f"  - 総書籍数: {len(self.books)}")
        print(f"  - 埋め込み次元: {self.embeddings.shape[1]}")
        print(f"  - グラフエッジ数: {edge_count}")
        print(f"  - 平均類似度: {np.mean(similarity_matrix):.4f}")
        
        print("\n🎉 デモ完了！")
        print("💡 PyTorchインストール後、フルGCNシステムが利用可能になります")

def main():
    """メイン実行関数"""
    analyzer = SimpleTechBookAnalyzer()
    analyzer.demo_system()

if __name__ == "__main__":
    main()
