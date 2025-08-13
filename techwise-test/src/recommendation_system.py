# -*- coding: utf-8 -*-
import torch
import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Dict, Tuple, Optional
import json

from data_loader import TechBookDataLoader
from gcn_model import TechBookGCN
from trainer import GCNTrainer

class GCNRecommendationSystem:
    """
    GCNモデルを使用した技術書推薦システム
    """
    
    def __init__(self, model_path: str = "GCN_best_model.pt", similarity_threshold: float = 0.5):
        self.model_path = model_path
        self.similarity_threshold = similarity_threshold
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # データローダー
        self.data_loader = TechBookDataLoader()
        
        # モデルと書籍データ
        self.model = None
        self.books = []
        self.book_embeddings = None
        self.category_mapping = {
            0: 'AI/機械学習',
            1: 'Python/バックエンド', 
            2: 'インフラ/クラウド',
            3: 'フロントエンド/Web',
            4: 'その他'
        }
        
        print(f"🤖 GCN推薦システム初期化完了")
        print(f"  - モデルパス: {model_path}")
        print(f"  - 類似度しきい値: {similarity_threshold}")
        print(f"  - デバイス: {self.device}")

def demo_recommendation_system():
    """
    推薦システムのデモンストレーション (学習済みモデル不要版)
    """
    print("🎬 GCN推薦システム デモンストレーション")
    print("⚠️  学習済みモデルが存在しないため、簡易版を実行します")
    
    # データローダーで基本機能テスト
    from simple_demo import SimpleTechBookAnalyzer
    analyzer = SimpleTechBookAnalyzer()
    analyzer.demo_system()
    
    print("\n💡 フルGCN推薦システム利用手順:")
    print("1. python trainer.py でGCNモデルを学習")
    print("2. 学習完了後、フル機能が利用可能になります")

if __name__ == "__main__":
    demo_recommendation_system()
