# -*- coding: utf-8 -*-
import torch
import torch.nn.functional as F
import torch.optim as optim
from torch.optim.lr_scheduler import StepLR
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix
from sklearn.model_selection import train_test_split
from torch_geometric.data import Data
from typing import Tuple, Dict, List, Optional
import json
from tqdm import tqdm
import warnings
warnings.filterwarnings('ignore')

from data_loader import TechBookDataLoader
from gcn_model import TechBookGCN, TechBookGAT, LinkPredictor, create_pytorch_geometric_data

class GCNTrainer:
    """
    Graph Convolutional Network の学習・評価を行うクラス
    """
    
    def __init__(
        self,
        model_type: str = "GCN",  # "GCN" or "GAT"
        device: Optional[str] = None,
        similarity_threshold: float = 0.6
    ):
        self.model_type = model_type
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.similarity_threshold = similarity_threshold
        
        # データローダー
        self.data_loader = TechBookDataLoader()
        
        # モデルとオプティマイザー
        self.model = None
        self.optimizer = None
        self.scheduler = None
        
        # 学習履歴
        self.train_losses = []
        self.train_accuracies = []
        self.val_accuracies = []
        
        print(f"🚀 GCNTrainer初期化完了:")
        print(f"  - モデルタイプ: {model_type}")
        print(f"  - デバイス: {self.device}")
        print(f"  - 類似度しきい値: {similarity_threshold}")
    
    def prepare_data(self) -> Tuple[Data, torch.Tensor, List[Dict]]:
        """
        データを準備し、訓練/テスト分割を行う
        """
        print("📚 データ準備中...")
        
        # DBからデータ取得
        node_features, edge_index, labels, books = self.data_loader.load_graph_data(
            similarity_threshold=self.similarity_threshold
        )
        
        # PyTorch Geometricデータ作成
        data = create_pytorch_geometric_data(node_features, edge_index, labels)
        
        # 訓練/検証/テストマスクの作成
        num_nodes = data.num_nodes
        indices = torch.randperm(num_nodes)
        
        train_size = int(0.7 * num_nodes)
        val_size = int(0.15 * num_nodes)
        
        train_mask = torch.zeros(num_nodes, dtype=torch.bool)
        val_mask = torch.zeros(num_nodes, dtype=torch.bool)
        test_mask = torch.zeros(num_nodes, dtype=torch.bool)
        
        train_mask[indices[:train_size]] = True
        val_mask[indices[train_size:train_size + val_size]] = True
        test_mask[indices[train_size + val_size:]] = True
        
        data.train_mask = train_mask
        data.val_mask = val_mask
        data.test_mask = test_mask
        
        print(f"📊 データ分割完了:")
        print(f"  - 訓練: {train_mask.sum().item()} ノード")
        print(f"  - 検証: {val_mask.sum().item()} ノード") 
        print(f"  - テスト: {test_mask.sum().item()} ノード")
        
        # デバイスに移動
        data = data.to(self.device)
        
        return data, labels, books
    
    def create_model(self, input_dim: int, output_dim: int) -> torch.nn.Module:
        """
        指定されたモデルタイプでGCNモデルを作成
        """
        if self.model_type == "GCN":
            model = TechBookGCN(
                input_dim=input_dim,
                hidden_dim=512,
                intermediate_dim=128,
                output_dim=output_dim,
                dropout=0.2
            )
        elif self.model_type == "GAT":
            model = TechBookGAT(
                input_dim=input_dim,
                hidden_dim=512,
                intermediate_dim=128,
                output_dim=output_dim,
                heads=8,
                dropout=0.2
            )
        else:
            raise ValueError(f"未対応のモデルタイプ: {self.model_type}")
        
        return model.to(self.device)
    
    def train_epoch(self, data: Data) -> Tuple[float, float]:
        """
        1エポックの学習を実行
        """
        self.model.train()
        self.optimizer.zero_grad()
        
        # Forward pass
        out = self.model(data.x, data.edge_index)
        
        # 訓練データでの損失計算
        loss = F.nll_loss(out[data.train_mask], data.y[data.train_mask])
        
        # Backward pass
        loss.backward()
        self.optimizer.step()
        
        # 訓練精度計算
        pred = out[data.train_mask].max(1)[1]
        train_acc = accuracy_score(
            data.y[data.train_mask].cpu().numpy(),
            pred.cpu().numpy()
        )
        
        return loss.item(), train_acc
    
    def evaluate(self, data: Data, mask: torch.Tensor) -> Tuple[float, np.ndarray, np.ndarray]:
        """
        指定されたマスクでモデルを評価
        """
        self.model.eval()
        
        with torch.no_grad():
            out = self.model(data.x, data.edge_index)
            pred = out[mask].max(1)[1]
            
            true_labels = data.y[mask].cpu().numpy()
            pred_labels = pred.cpu().numpy()
            
            accuracy = accuracy_score(true_labels, pred_labels)
            
        return accuracy, true_labels, pred_labels
    
    def train(
        self,
        epochs: int = 200,
        lr: float = 0.01,
        weight_decay: float = 5e-4,
        patience: int = 50
    ) -> Dict[str, List[float]]:
        """
        モデルを学習する
        """
        print(f"🏋️ モデル学習開始 ({epochs} epochs)")
        
        # データ準備
        data, labels, books = self.prepare_data()
        
        # モデル作成
        input_dim = data.num_node_features
        output_dim = len(torch.unique(data.y))
        
        self.model = self.create_model(input_dim, output_dim)
        
        # オプティマイザー設定
        self.optimizer = optim.Adam(self.model.parameters(), lr=lr, weight_decay=weight_decay)
        self.scheduler = StepLR(self.optimizer, step_size=50, gamma=0.7)
        
        # 早期停止用変数
        best_val_acc = 0.0
        patience_counter = 0
        
        # 学習ループ
        pbar = tqdm(range(epochs), desc="Training")
        
        for epoch in pbar:
            # 学習
            train_loss, train_acc = self.train_epoch(data)
            
            # 検証
            val_acc, _, _ = self.evaluate(data, data.val_mask)
            
            # 記録
            self.train_losses.append(train_loss)
            self.train_accuracies.append(train_acc)
            self.val_accuracies.append(val_acc)
            
            # スケジューラー更新
            self.scheduler.step()
            
            # 早期停止判定
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                patience_counter = 0
                # ベストモデルを保存
                torch.save(self.model.state_dict(), f"{self.model_type}_best_model.pt")
            else:
                patience_counter += 1
            
            # プログレスバー更新
            pbar.set_postfix({
                'Loss': f'{train_loss:.4f}',
                'Train Acc': f'{train_acc:.4f}',
                'Val Acc': f'{val_acc:.4f}',
                'Best': f'{best_val_acc:.4f}'
            })
            
            # 早期停止
            if patience_counter >= patience:
                print(f"\\n⏰ 早期停止: {patience} epochs改善なし")
                break
        
        print(f"🎯 学習完了! Best Validation Accuracy: {best_val_acc:.4f}")
        
        # ベストモデルをロード
        self.model.load_state_dict(torch.load(f"{self.model_type}_best_model.pt"))
        
        return {
            'train_losses': self.train_losses,
            'train_accuracies': self.train_accuracies,
            'val_accuracies': self.val_accuracies,
            'best_val_accuracy': best_val_acc
        }
    
    def evaluate_final(self) -> Dict[str, float]:
        """
        最終テストセットでの評価
        """
        print("🧪 最終評価実行中...")
        
        # データ準備
        data, labels, books = self.prepare_data()
        
        # テストセットで評価
        test_acc, true_labels, pred_labels = self.evaluate(data, data.test_mask)
        
        # 詳細メトリクス計算
        precision, recall, f1, _ = precision_recall_fscore_support(
            true_labels, pred_labels, average='weighted'
        )
        
        # カテゴリ別精度
        category_names = ['AI/ML', 'Python/Backend', 'Infrastructure', 'Frontend', 'Other']
        cm = confusion_matrix(true_labels, pred_labels)
        
        results = {
            'test_accuracy': test_acc,
            'precision': precision,
            'recall': recall,
            'f1_score': f1,
            'confusion_matrix': cm.tolist()
        }
        
        print(f"📊 最終結果:")
        print(f"  - テスト精度: {test_acc:.4f}")
        print(f"  - 精密度: {precision:.4f}")
        print(f"  - 再現率: {recall:.4f}")
        print(f"  - F1スコア: {f1:.4f}")
        
        # 混同行列の可視化
        self.plot_confusion_matrix(cm, category_names)
        
        return results
    
    def plot_confusion_matrix(self, cm: np.ndarray, category_names: List[str]):
        """
        混同行列を可視化
        """
        plt.figure(figsize=(10, 8))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
                    xticklabels=category_names, yticklabels=category_names)
        plt.title(f'{self.model_type} Model - Confusion Matrix')
        plt.ylabel('True Label')
        plt.xlabel('Predicted Label')
        plt.tight_layout()
        plt.savefig(f'{self.model_type}_confusion_matrix.png', dpi=300, bbox_inches='tight')
        plt.show()
        
        print(f"📊 混同行列を '{self.model_type}_confusion_matrix.png' に保存しました")
    
    def plot_training_curves(self):
        """
        学習曲線を可視化
        """
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 5))
        
        # 損失曲線
        ax1.plot(self.train_losses, label='Training Loss', color='blue')
        ax1.set_title('Training Loss')
        ax1.set_xlabel('Epoch')
        ax1.set_ylabel('Loss')
        ax1.legend()
        ax1.grid(True)
        
        # 精度曲線
        ax2.plot(self.train_accuracies, label='Training Accuracy', color='green')
        ax2.plot(self.val_accuracies, label='Validation Accuracy', color='orange')
        ax2.set_title('Training/Validation Accuracy')
        ax2.set_xlabel('Epoch')
        ax2.set_ylabel('Accuracy')
        ax2.legend()
        ax2.grid(True)
        
        plt.tight_layout()
        plt.savefig(f'{self.model_type}_training_curves.png', dpi=300, bbox_inches='tight')
        plt.show()
        
        print(f"📈 学習曲線を '{self.model_type}_training_curves.png' に保存しました")
    
    def get_book_embeddings(self) -> Tuple[np.ndarray, List[Dict]]:
        """
        学習済みモデルから書籍の埋め込みベクトルを取得（推薦システム用）
        """
        print("📝 書籍埋め込みベクトルを取得中...")
        
        # データ準備
        data, labels, books = self.prepare_data()
        
        # 埋め込みベクトル取得
        self.model.eval()
        with torch.no_grad():
            embeddings = self.model.get_embeddings(data.x, data.edge_index)
            embeddings = embeddings.cpu().numpy()
        
        print(f"✅ 埋め込みベクトル取得完了: {embeddings.shape}")
        
        return embeddings, books

if __name__ == "__main__":
    print("🚀 GCN学習システム開始")
    
    # GCNモデルで学習
    trainer_gcn = GCNTrainer(model_type="GCN", similarity_threshold=0.5)
    history_gcn = trainer_gcn.train(epochs=300, lr=0.01)
    
    # 最終評価
    results_gcn = trainer_gcn.evaluate_final()
    
    # 学習曲線の可視化
    trainer_gcn.plot_training_curves()
    
    # 結果保存
    results_gcn['training_history'] = history_gcn
    with open('gcn_results.json', 'w', encoding='utf-8') as f:
        json.dump(results_gcn, f, ensure_ascii=False, indent=2)
    
    print("✅ GCN学習・評価完了!")
    
    # 書籍埋め込み取得（推薦システム用）
    embeddings, books = trainer_gcn.get_book_embeddings()
    
    # 埋め込みベクトル保存
    np.save('book_embeddings_gcn.npy', embeddings)
    
    print("🎉 すべての処理が完了しました！")
