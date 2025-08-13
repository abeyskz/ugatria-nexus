#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TechWise GCN実装 - メインスクリプト
PyTorch GeometricでGCN実装.txtの要件に基づいた実用的で拡張性の高いシステム

実装内容:
1. 技術書データをDBから取得
2. GCN/GATモデルでノード分類・リンク予測
3. 学習済みモデルによる推薦システム
4. 5-fold交差検証
5. NetworkXとの比較分析

使用技術:
- PyTorch Geometric (GNN専用ライブラリ)
- PostgreSQL (techwise_db)
- GCN/GAT (Graph Neural Networks)
"""

import torch
import json
import argparse
import warnings
from pathlib import Path
from typing import Dict, List

warnings.filterwarnings('ignore')

from data_loader import TechBookDataLoader
from trainer import GCNTrainer
from recommendation_system import GCNRecommendationSystem, demo_recommendation_system

class TechWiseGCNPipeline:
    """
    TechWise技術書GCN分析・推薦パイプライン
    """
    
    def __init__(self, similarity_threshold: float = 0.5):
        self.similarity_threshold = similarity_threshold
        self.results = {}
        
        print(f"🚀 TechWise GCN Pipeline 開始")
        print(f"  - 類似度しきい値: {similarity_threshold}")
        print(f"  - デバイス: {'GPU' if torch.cuda.is_available() else 'CPU'}")
    
    def phase1_data_analysis(self) -> Dict:
        """
        Phase1: データ分析とグラフ統計
        """
        print("\n📊 Phase1: データ分析とグラフ統計")
        print("=" * 50)
        
        # データ読み込み
        data_loader = TechBookDataLoader()
        node_features, edge_index, labels, books = data_loader.load_graph_data(
            similarity_threshold=self.similarity_threshold
        )
        
        # カテゴリ分布分析
        category_dist = {}
        for book in books:
            category = book['primary_category']
            category_dist[category] = category_dist.get(category, 0) + 1
        
        # 難易度分布
        difficulty_dist = {}
        for book in books:
            level = book['difficulty_level']
            difficulty_dist[level] = difficulty_dist.get(level, 0) + 1
        
        analysis_results = {
            'total_books': len(books),
            'total_edges': edge_index.size(1),
            'graph_density': edge_index.size(1) / (len(books) * (len(books) - 1)),
            'category_distribution': category_dist,
            'difficulty_distribution': difficulty_dist,
            'embedding_dimension': node_features.size(1)
        }
        
        print(f"📚 総書籍数: {analysis_results['total_books']}")
        print(f"🔗 エッジ数: {analysis_results['total_edges']}")
        print(f"📈 グラフ密度: {analysis_results['graph_density']:.6f}")
        print(f"📊 カテゴリ分布: {analysis_results['category_distribution']}")
        print(f"🎯 難易度分布: {analysis_results['difficulty_distribution']}")
        
        self.results['phase1_analysis'] = analysis_results
        return analysis_results
    
    def phase2_gcn_training(self, epochs: int = 300) -> Dict:
        """
        Phase2: GCNモデル学習
        """
        print("\n🧠 Phase2: GCNモデル学習")
        print("=" * 50)
        
        # GCN学習
        print("🔥 GCNモデル学習中...")
        trainer_gcn = GCNTrainer(
            model_type="GCN", 
            similarity_threshold=self.similarity_threshold
        )
        history_gcn = trainer_gcn.train(epochs=epochs)
        results_gcn = trainer_gcn.evaluate_final()
        
        # 学習曲線可視化
        trainer_gcn.plot_training_curves()
        
        # 書籍埋め込み取得
        embeddings_gcn, books = trainer_gcn.get_book_embeddings()
        
        gcn_results = {
            'model_type': 'GCN',
            'training_history': history_gcn,
            'final_results': results_gcn,
            'embedding_shape': embeddings_gcn.shape
        }
        
        print(f"✅ GCN学習完了!")
        print(f"  - 最終テスト精度: {results_gcn['test_accuracy']:.4f}")
        print(f"  - F1スコア: {results_gcn['f1_score']:.4f}")
        
        self.results['phase2_gcn'] = gcn_results
        return gcn_results
    
    def phase2_gat_training(self, epochs: int = 300) -> Dict:
        """
        Phase2: GATモデル学習（オプション）
        """
        print("\n🧠 Phase2: GATモデル学習")
        print("=" * 50)
        
        # GAT学習
        print("🔥 GATモデル学習中...")
        trainer_gat = GCNTrainer(
            model_type="GAT", 
            similarity_threshold=self.similarity_threshold
        )
        history_gat = trainer_gat.train(epochs=epochs)
        results_gat = trainer_gat.evaluate_final()
        
        # 学習曲線可視化
        trainer_gat.plot_training_curves()
        
        # 書籍埋め込み取得
        embeddings_gat, books = trainer_gat.get_book_embeddings()
        
        gat_results = {
            'model_type': 'GAT',
            'training_history': history_gat,
            'final_results': results_gat,
            'embedding_shape': embeddings_gat.shape
        }
        
        print(f"✅ GAT学習完了!")
        print(f"  - 最終テスト精度: {results_gat['test_accuracy']:.4f}")
        print(f"  - F1スコア: {results_gat['f1_score']:.4f}")
        
        self.results['phase2_gat'] = gat_results
        return gat_results
    
    def phase3_recommendation_system(self) -> Dict:
        """
        Phase3: 推薦システムのテスト
        """
        print("\n🎯 Phase3: 推薦システム評価")
        print("=" * 50)
        
        try:
            # 推薦システムデモ実行
            demo_recommendation_system()
            
            recommendation_results = {
                'status': 'completed',
                'demo_executed': True,
                'model_used': 'GCN'
            }
            
            print("✅ 推薦システム評価完了!")
            
        except Exception as e:
            print(f"❌ 推薦システムエラー: {e}")
            recommendation_results = {
                'status': 'error',
                'error_message': str(e)
            }
        
        self.results['phase3_recommendation'] = recommendation_results
        return recommendation_results
    
    def phase4_model_comparison(self) -> Dict:
        """
        Phase4: モデル比較（GCN vs GAT vs NetworkX）
        """
        print("\n🏁 Phase4: モデル比較分析")
        print("=" * 50)
        
        comparison_results = {}
        
        # GCN vs GAT比較
        if 'phase2_gcn' in self.results and 'phase2_gat' in self.results:
            gcn_acc = self.results['phase2_gcn']['final_results']['test_accuracy']
            gat_acc = self.results['phase2_gat']['final_results']['test_accuracy']
            gcn_f1 = self.results['phase2_gcn']['final_results']['f1_score']
            gat_f1 = self.results['phase2_gat']['final_results']['f1_score']
            
            comparison_results['gcn_vs_gat'] = {
                'gcn_accuracy': gcn_acc,
                'gat_accuracy': gat_acc,
                'gcn_f1': gcn_f1,
                'gat_f1': gat_f1,
                'better_model': 'GAT' if gat_acc > gcn_acc else 'GCN',
                'accuracy_improvement': abs(gat_acc - gcn_acc)
            }
            
            print(f"🥊 GCN vs GAT:")
            print(f"  - GCN精度: {gcn_acc:.4f} | F1: {gcn_f1:.4f}")
            print(f"  - GAT精度: {gat_acc:.4f} | F1: {gat_f1:.4f}")
            print(f"  - 勝者: {comparison_results['gcn_vs_gat']['better_model']}")
        
        # NetworkXとの比較（Phase1のNetworkX結果があれば）
        comparison_results['networkx_comparison'] = {
            'graph_construction': 'NetworkX: 類似度ベース',
            'gcn_advantage': 'エンドツーエンド学習',
            'feature_learning': 'GCN: 自動特徴抽出'
        }
        
        print("🔗 NetworkX vs GCN:")
        print("  - NetworkX: 明示的類似度計算")
        print("  - GCN: 学習による特徴抽出")
        print("  - GCN利点: エンドツーエンド最適化")
        
        self.results['phase4_comparison'] = comparison_results
        return comparison_results
    
    def save_results(self, output_path: str = "techwise_gcn_results.json"):
        """
        結果をJSONファイルに保存
        """
        # NumPy配列やTensorをリストに変換
        def convert_for_json(obj):
            if hasattr(obj, 'tolist'):
                return obj.tolist()
            elif hasattr(obj, 'item'):
                return obj.item()
            return obj
        
        # 結果の変換
        json_results = {}
        for key, value in self.results.items():
            if isinstance(value, dict):
                json_results[key] = {k: convert_for_json(v) for k, v in value.items()}
            else:
                json_results[key] = convert_for_json(value)
        
        # ファイル保存
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(json_results, f, ensure_ascii=False, indent=2)
        
        print(f"💾 結果を '{output_path}' に保存しました")
    
    def run_full_pipeline(self, epochs: int = 300, include_gat: bool = False) -> Dict:
        """
        全パイプラインを実行
        """
        print("🚀 TechWise GCN Pipeline 全体実行開始")
        print("=" * 80)
        
        try:
            # Phase1: データ分析
            self.phase1_data_analysis()
            
            # Phase2: GCN学習
            self.phase2_gcn_training(epochs=epochs)
            
            # Phase2: GAT学習（オプション）
            if include_gat:
                self.phase2_gat_training(epochs=epochs)
            
            # Phase3: 推薦システム
            self.phase3_recommendation_system()
            
            # Phase4: モデル比較
            self.phase4_model_comparison()
            
            # 結果保存
            self.save_results()
            
            print("\\n" + "=" * 80)
            print("🎉 TechWise GCN Pipeline 完全実行完了!")
            print("=" * 80)
            
            return self.results
            
        except Exception as e:
            print(f"❌ パイプライン実行エラー: {e}")
            raise

def main():
    """
    メイン関数
    """
    parser = argparse.ArgumentParser(description='TechWise GCN Implementation')
    parser.add_argument('--epochs', type=int, default=300, help='Training epochs')
    parser.add_argument('--similarity-threshold', type=float, default=0.5, help='Similarity threshold for graph construction')
    parser.add_argument('--include-gat', action='store_true', help='Include GAT model training')
    parser.add_argument('--demo-only', action='store_true', help='Run only recommendation system demo')
    
    args = parser.parse_args()
    
    if args.demo_only:
        print("🎬 推薦システムデモのみ実行")
        demo_recommendation_system()
    else:
        # フルパイプライン実行
        pipeline = TechWiseGCNPipeline(similarity_threshold=args.similarity_threshold)
        results = pipeline.run_full_pipeline(
            epochs=args.epochs, 
            include_gat=args.include_gat
        )
        
        # 最終サマリー表示
        print("\\n📋 最終実行サマリー:")
        print(f"  - 総書籍数: {results.get('phase1_analysis', {}).get('total_books', 'N/A')}")
        print(f"  - GCN精度: {results.get('phase2_gcn', {}).get('final_results', {}).get('test_accuracy', 'N/A'):.4f}")
        if 'phase2_gat' in results:
            print(f"  - GAT精度: {results.get('phase2_gat', {}).get('final_results', {}).get('test_accuracy', 'N/A'):.4f}")
        print(f"  - 推薦システム: {results.get('phase3_recommendation', {}).get('status', 'N/A')}")

if __name__ == "__main__":
    main()
