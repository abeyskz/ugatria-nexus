# -*- coding: utf-8 -*-
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import GCNConv, GATConv, global_mean_pool
from torch_geometric.data import Data, DataLoader
from typing import Optional, Tuple

class TechBookGCN(nn.Module):
    """
    技術書推薦・分類用のGraph Convolutional Network
    
    アーキテクチャ:
    - Layer1: 1536 → 512 (特徴抽出)
    - Layer2: 512 → 128 (中間表現)  
    - Layer3: 128 → 5 (カテゴリ分類)
    - Dropout: 0.2 (過学習防止)
    """
    
    def __init__(
        self, 
        input_dim: int = 1536,
        hidden_dim: int = 512,
        intermediate_dim: int = 128,
        output_dim: int = 5,
        dropout: float = 0.2
    ):
        super(TechBookGCN, self).__init__()
        
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.intermediate_dim = intermediate_dim
        self.output_dim = output_dim
        self.dropout = dropout
        
        # GCN Layers
        self.conv1 = GCNConv(input_dim, hidden_dim)
        self.conv2 = GCNConv(hidden_dim, intermediate_dim)
        self.conv3 = GCNConv(intermediate_dim, output_dim)
        
        # Batch Normalization
        self.bn1 = nn.BatchNorm1d(hidden_dim)
        self.bn2 = nn.BatchNorm1d(intermediate_dim)
        
        # Dropout
        self.dropout_layer = nn.Dropout(dropout)
        
        print(f"🧠 TechBookGCN初期化完了:")
        print(f"  - 入力次元: {input_dim}")
        print(f"  - 隠れ次元: {hidden_dim} → {intermediate_dim}")
        print(f"  - 出力次元: {output_dim}")
        print(f"  - Dropout: {dropout}")
    
    def forward(self, x: torch.Tensor, edge_index: torch.Tensor) -> torch.Tensor:
        """
        Forward pass
        
        Args:
            x: ノード特徴量 [num_nodes, input_dim]
            edge_index: エッジインデックス [2, num_edges]
            
        Returns:
            out: 分類結果 [num_nodes, output_dim]
        """
        # Layer 1: 1536 → 512
        x = self.conv1(x, edge_index)
        x = self.bn1(x)
        x = F.relu(x)
        x = self.dropout_layer(x)
        
        # Layer 2: 512 → 128
        x = self.conv2(x, edge_index)
        x = self.bn2(x)
        x = F.relu(x)
        x = self.dropout_layer(x)
        
        # Layer 3: 128 → 5 (Classification)
        x = self.conv3(x, edge_index)
        
        return F.log_softmax(x, dim=1)
    
    def get_embeddings(self, x: torch.Tensor, edge_index: torch.Tensor) -> torch.Tensor:
        """
        推薦システム用の中間特徴量を取得
        
        Args:
            x: ノード特徴量 [num_nodes, input_dim]
            edge_index: エッジインデックス [2, num_edges]
            
        Returns:
            embeddings: 中間特徴量 [num_nodes, intermediate_dim]
        """
        # Layer 1
        x = self.conv1(x, edge_index)
        x = self.bn1(x)
        x = F.relu(x)
        x = self.dropout_layer(x)
        
        # Layer 2 (推薦用特徴量として返す)
        x = self.conv2(x, edge_index)
        x = self.bn2(x)
        x = F.relu(x)
        
        return x

class TechBookGAT(nn.Module):
    """
    Graph Attention Networkバージョン（オプション）
    Attentionメカニズムで書籍間の関係性をより詳細に学習
    """
    
    def __init__(
        self, 
        input_dim: int = 1536,
        hidden_dim: int = 512,
        intermediate_dim: int = 128,
        output_dim: int = 5,
        heads: int = 8,
        dropout: float = 0.2
    ):
        super(TechBookGAT, self).__init__()
        
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.intermediate_dim = intermediate_dim
        self.output_dim = output_dim
        self.heads = heads
        self.dropout = dropout
        
        # GAT Layers
        self.conv1 = GATConv(input_dim, hidden_dim // heads, heads=heads, dropout=dropout)
        self.conv2 = GATConv(hidden_dim, intermediate_dim // heads, heads=heads, dropout=dropout)
        self.conv3 = GATConv(intermediate_dim, output_dim, heads=1, dropout=dropout)
        
        # Batch Normalization
        self.bn1 = nn.BatchNorm1d(hidden_dim)
        self.bn2 = nn.BatchNorm1d(intermediate_dim)
        
        print(f"🧠 TechBookGAT初期化完了:")
        print(f"  - 入力次元: {input_dim}")
        print(f"  - Attention heads: {heads}")
        print(f"  - 隠れ次元: {hidden_dim} → {intermediate_dim}")
        print(f"  - 出力次元: {output_dim}")
    
    def forward(self, x: torch.Tensor, edge_index: torch.Tensor) -> torch.Tensor:
        """
        Forward pass with attention mechanism
        """
        # Layer 1 with attention
        x = F.relu(self.conv1(x, edge_index))
        x = self.bn1(x)
        x = F.dropout(x, p=self.dropout, training=self.training)
        
        # Layer 2 with attention
        x = F.relu(self.conv2(x, edge_index))
        x = self.bn2(x)
        x = F.dropout(x, p=self.dropout, training=self.training)
        
        # Layer 3 (Classification)
        x = self.conv3(x, edge_index)
        
        return F.log_softmax(x, dim=1)

class LinkPredictor(nn.Module):
    """
    リンク予測用のモデル（書籍間の関係性予測）
    """
    
    def __init__(self, embedding_dim: int = 128):
        super(LinkPredictor, self).__init__()
        
        self.embedding_dim = embedding_dim
        
        # リンク予測用のMLP
        self.predictor = nn.Sequential(
            nn.Linear(embedding_dim * 2, embedding_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(embedding_dim, embedding_dim // 2),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(embedding_dim // 2, 1),
            nn.Sigmoid()
        )
        
        print(f"🔗 LinkPredictor初期化完了 (embedding_dim: {embedding_dim})")
    
    def forward(self, node_embeddings: torch.Tensor, edge_index: torch.Tensor) -> torch.Tensor:
        """
        エッジの存在確率を予測
        
        Args:
            node_embeddings: ノード埋め込み [num_nodes, embedding_dim]
            edge_index: エッジインデックス [2, num_edges]
            
        Returns:
            predictions: エッジ存在確率 [num_edges]
        """
        # エッジの両端ノードの特徴量を取得
        source_embeddings = node_embeddings[edge_index[0]]
        target_embeddings = node_embeddings[edge_index[1]]
        
        # 連結した特徴量でリンク予測
        edge_embeddings = torch.cat([source_embeddings, target_embeddings], dim=1)
        predictions = self.predictor(edge_embeddings).squeeze()
        
        return predictions

def create_pytorch_geometric_data(
    node_features: torch.Tensor, 
    edge_index: torch.Tensor, 
    labels: torch.Tensor
) -> Data:
    """
    PyTorch GeometricのDataオブジェクトを作成
    
    Args:
        node_features: ノード特徴量 [num_nodes, feature_dim]
        edge_index: エッジインデックス [2, num_edges]
        labels: ノードラベル [num_nodes]
        
    Returns:
        data: PyTorch GeometricのDataオブジェクト
    """
    data = Data(
        x=node_features,
        edge_index=edge_index,
        y=labels
    )
    
    print(f"📊 PyTorch Geometric Dataオブジェクト作成完了:")
    print(f"  - ノード数: {data.num_nodes}")
    print(f"  - エッジ数: {data.num_edges}")
    print(f"  - 特徴量次元: {data.num_node_features}")
    print(f"  - クラス数: {len(torch.unique(labels))}")
    
    return data

if __name__ == "__main__":
    # モデルのテスト
    print("🔬 GCNモデルのテスト実行:")
    
    # ダミーデータでテスト
    num_nodes = 50
    input_dim = 1536
    num_edges = 100
    
    x = torch.randn(num_nodes, input_dim)
    edge_index = torch.randint(0, num_nodes, (2, num_edges))
    labels = torch.randint(0, 5, (num_nodes,))
    
    # GCNモデルテスト
    model = TechBookGCN(input_dim=input_dim)
    output = model(x, edge_index)
    embeddings = model.get_embeddings(x, edge_index)
    
    print(f"✅ GCN出力形状: {output.shape}")
    print(f"✅ 埋め込み形状: {embeddings.shape}")
    
    # GATモデルテスト
    gat_model = TechBookGAT(input_dim=input_dim)
    gat_output = gat_model(x, edge_index)
    
    print(f"✅ GAT出力形状: {gat_output.shape}")
    
    # リンク予測モデルテスト
    link_predictor = LinkPredictor(embedding_dim=128)
    link_predictions = link_predictor(embeddings, edge_index)
    
    print(f"✅ リンク予測形状: {link_predictions.shape}")
    
    print("🎉 すべてのモデルが正常に動作しています！")
