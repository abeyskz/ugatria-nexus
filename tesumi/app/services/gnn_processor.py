"""
GNN Processor for Memory Retention and Activation
Implements Memory-Augmented GNNs with GraphSAGE and GRU-based memory units
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import SAGEConv, GATConv, global_mean_pool
from torch_geometric.data import Data, Batch
import numpy as np
from typing import List, Dict, Tuple, Optional
import logging
from datetime import datetime, timedelta

from app.core.config import settings

logger = logging.getLogger(__name__)


class MemoryGRU(nn.Module):
    """GRU unit for internal memory in each node"""
    
    def __init__(self, input_dim: int, hidden_dim: int):
        super().__init__()
        self.hidden_dim = hidden_dim
        self.gru = nn.GRUCell(input_dim, hidden_dim)
        
    def forward(self, input_features, hidden_state):
        """Update hidden state with new input"""
        if hidden_state is None:
            hidden_state = torch.zeros(input_features.size(0), self.hidden_dim)
        
        new_hidden = self.gru(input_features, hidden_state)
        return new_hidden


class GraphSAGEMemory(nn.Module):
    """
    GraphSAGE with Memory-Augmented capabilities
    Based on Memory-Augmented GNNs paper
    """
    
    def __init__(
        self,
        input_dim: int = 384,  # Embedding dimension
        hidden_dim: int = 128,
        num_layers: int = 3,
        dropout: float = 0.1
    ):
        super().__init__()
        
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        
        # GraphSAGE layers
        self.convs = nn.ModuleList()
        self.convs.append(SAGEConv(input_dim + 2, hidden_dim))  # +2 for valence/arousal
        
        for _ in range(num_layers - 1):
            self.convs.append(SAGEConv(hidden_dim, hidden_dim))
        
        # Memory components
        self.memory_gru = MemoryGRU(hidden_dim, hidden_dim)
        
        # Attention mechanism for memory
        self.memory_attention = nn.MultiheadAttention(hidden_dim, num_heads=4, dropout=dropout)
        
        # Output layers
        self.dropout = nn.Dropout(dropout)
        self.activation_head = nn.Linear(hidden_dim, 1)  # For activation strength
        self.emotion_head = nn.Linear(hidden_dim, 2)     # For valence/arousal prediction
        
    def forward(self, data: Data, memory_states: Optional[torch.Tensor] = None):
        """
        Forward pass through the memory-augmented GNN
        
        Args:
            data: PyTorch Geometric data object with node features and edges
            memory_states: Previous memory states for each node
            
        Returns:
            node_embeddings: Updated node embeddings
            activation_scores: Activation strength for each node
            emotion_predictions: Predicted valence/arousal
            new_memory_states: Updated memory states
        """
        x, edge_index = data.x, data.edge_index
        batch_size = x.size(0)
        
        # Graph convolutions with residual connections
        for i, conv in enumerate(self.convs):
            x_new = conv(x, edge_index)
            x_new = F.relu(x_new)
            x_new = self.dropout(x_new)
            
            # Residual connection (if dimensions match)
            if i > 0 and x.size(-1) == x_new.size(-1):
                x = x + x_new
            else:
                x = x_new
        
        node_embeddings = x
        
        # Update internal memory using GRU
        if memory_states is not None:
            new_memory_states = self.memory_gru(node_embeddings, memory_states)
        else:
            new_memory_states = self.memory_gru(node_embeddings, None)
        
        # Apply memory attention
        # Reshape for attention: (seq_len, batch, hidden_dim)
        memory_input = new_memory_states.unsqueeze(0)  # (1, batch, hidden_dim)
        attended_memory, _ = self.memory_attention(
            memory_input, memory_input, memory_input
        )
        attended_memory = attended_memory.squeeze(0)  # (batch, hidden_dim)
        
        # Combine node embeddings with attended memory
        combined_features = node_embeddings + attended_memory
        
        # Generate outputs
        activation_scores = torch.sigmoid(self.activation_head(combined_features))
        emotion_predictions = torch.tanh(self.emotion_head(combined_features))
        
        return {
            'node_embeddings': combined_features,
            'activation_scores': activation_scores,
            'emotion_predictions': emotion_predictions,
            'memory_states': new_memory_states
        }


class ExternalMemory:
    """
    Key-Value external memory structure
    Stores and retrieves past memories based on queries
    """
    
    def __init__(self, memory_size: int = 1000, key_dim: int = 128):
        self.memory_size = memory_size
        self.key_dim = key_dim
        
        # Initialize memory matrices
        self.keys = np.zeros((memory_size, key_dim))
        self.values = np.zeros((memory_size, key_dim))
        self.usage = np.zeros(memory_size)
        self.current_size = 0
        
    def write(self, key: np.ndarray, value: np.ndarray):
        """Write a key-value pair to memory"""
        if self.current_size < self.memory_size:
            # Add to next available slot
            idx = self.current_size
            self.current_size += 1
        else:
            # Replace least used memory
            idx = np.argmin(self.usage)
        
        self.keys[idx] = key
        self.values[idx] = value
        self.usage[idx] = 1.0
        
        return idx
    
    def read(self, query: np.ndarray, k: int = 5) -> Tuple[np.ndarray, np.ndarray]:
        """
        Read from memory based on query
        
        Args:
            query: Query vector
            k: Number of nearest neighbors to retrieve
            
        Returns:
            retrieved_values: Values from memory
            similarities: Similarity scores
        """
        if self.current_size == 0:
            return np.zeros((k, self.key_dim)), np.zeros(k)
        
        # Calculate similarities
        similarities = np.dot(self.keys[:self.current_size], query)
        similarities = similarities / (np.linalg.norm(self.keys[:self.current_size], axis=1) + 1e-8)
        similarities = similarities / (np.linalg.norm(query) + 1e-8)
        
        # Get top-k most similar
        top_k_indices = np.argsort(similarities)[::-1][:k]
        
        # Update usage
        self.usage[top_k_indices] += 0.1
        
        retrieved_values = self.values[top_k_indices]
        retrieved_similarities = similarities[top_k_indices]
        
        return retrieved_values, retrieved_similarities


class GNNProcessor:
    """
    Main GNN processor for memory management
    Handles memory activation, updating, and retrieval
    """
    
    def __init__(self):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        # Initialize GNN model
        self.model = GraphSAGEMemory(
            input_dim=settings.VECTOR_DIMENSION,
            hidden_dim=settings.GNN_HIDDEN_DIM,
            num_layers=settings.GNN_NUM_LAYERS,
            dropout=settings.GNN_DROPOUT
        ).to(self.device)
        
        # Initialize external memory
        self.external_memory = ExternalMemory(
            memory_size=settings.MAX_MEMORY_NODES,
            key_dim=settings.GNN_HIDDEN_DIM
        )
        
        # Memory states for each node (will be loaded from DB)
        self.node_memory_states = {}
        
        logger.info(f"GNN Processor initialized on device: {self.device}")
    
    def create_graph_data(self, memory_nodes: List[Dict], memory_edges: List[Dict]) -> Data:
        """
        Create PyTorch Geometric Data object from memory nodes and edges
        
        Args:
            memory_nodes: List of memory node dictionaries
            memory_edges: List of memory edge dictionaries
            
        Returns:
            PyTorch Geometric Data object
        """
        if not memory_nodes:
            # Return empty graph
            return Data(x=torch.empty(0, settings.VECTOR_DIMENSION + 2), 
                       edge_index=torch.empty(2, 0, dtype=torch.long))
        
        # Create node feature matrix
        node_features = []
        node_id_to_idx = {}
        
        for i, node in enumerate(memory_nodes):
            # Combine embedding with valence/arousal
            embedding = np.array(node['embedding'])
            valence = node.get('valence', 0.0)
            arousal = node.get('arousal', 0.0)
            
            features = np.concatenate([embedding, [valence, arousal]])
            node_features.append(features)
            node_id_to_idx[str(node['id'])] = i
        
        x = torch.tensor(node_features, dtype=torch.float32)
        
        # Create edge index
        edge_indices = [[], []]
        edge_weights = []
        
        for edge in memory_edges:
            source_id = str(edge['source_id'])
            target_id = str(edge['target_id'])
            
            if source_id in node_id_to_idx and target_id in node_id_to_idx:
                source_idx = node_id_to_idx[source_id]
                target_idx = node_id_to_idx[target_id]
                
                edge_indices[0].append(source_idx)
                edge_indices[1].append(target_idx)
                edge_weights.append(edge['weight'])
                
                # Add reverse edge for undirected graph
                edge_indices[0].append(target_idx)
                edge_indices[1].append(source_idx)
                edge_weights.append(edge['weight'])
        
        edge_index = torch.tensor(edge_indices, dtype=torch.long)
        edge_attr = torch.tensor(edge_weights, dtype=torch.float32)
        
        return Data(x=x, edge_index=edge_index, edge_attr=edge_attr)
    
    def activate_memories(
        self,
        memory_nodes: List[Dict],
        memory_edges: List[Dict],
        query_embedding: np.ndarray,
        top_k: int = 10
    ) -> List[Dict]:
        """
        Activate memories based on query embedding using GNN
        
        Args:
            memory_nodes: All memory nodes
            memory_edges: All memory edges
            query_embedding: Query embedding vector
            top_k: Number of top memories to return
            
        Returns:
            List of activated memory nodes with scores
        """
        try:
            if not memory_nodes:
                return []
            
            # Create graph data
            graph_data = self.create_graph_data(memory_nodes, memory_edges)
            graph_data = graph_data.to(self.device)
            
            # Get current memory states
            memory_states = self._get_memory_states([str(node['id']) for node in memory_nodes])
            
            # Forward pass through GNN
            with torch.no_grad():
                self.model.eval()
                output = self.model(graph_data, memory_states)
            
            # Update memory states
            self._update_memory_states(
                [str(node['id']) for node in memory_nodes],
                output['memory_states']
            )
            
            # Calculate activation scores based on similarity to query
            node_embeddings = output['node_embeddings'].cpu().numpy()
            activation_scores = output['activation_scores'].cpu().numpy().flatten()
            
            # Compute similarity to query
            similarities = np.dot(node_embeddings, query_embedding)
            similarities = similarities / (np.linalg.norm(node_embeddings, axis=1) + 1e-8)
            similarities = similarities / (np.linalg.norm(query_embedding) + 1e-8)
            
            # Combine GNN activation with similarity
            final_scores = 0.7 * similarities + 0.3 * activation_scores
            
            # Get top-k activated memories
            top_indices = np.argsort(final_scores)[::-1][:top_k]
            
            activated_memories = []
            for idx in top_indices:
                if idx < len(memory_nodes):
                    memory = memory_nodes[idx].copy()
                    memory['activation_score'] = float(final_scores[idx])
                    memory['similarity_score'] = float(similarities[idx])
                    activated_memories.append(memory)
            
            # Query external memory for additional context
            external_memories, _ = self.external_memory.read(
                query_embedding, k=min(3, len(activated_memories))
            )
            
            logger.info(f"Activated {len(activated_memories)} memories")
            return activated_memories
            
        except Exception as e:
            logger.error(f"Error in memory activation: {e}")
            return []
    
    def update_memory_with_interaction(
        self,
        user_input: str,
        system_response: str,
        embedding: np.ndarray,
        emotion_scores: Dict[str, float]
    ):
        """
        Update memory system with new interaction
        
        Args:
            user_input: User's input message
            system_response: System's response
            embedding: Embedding vector for the interaction
            emotion_scores: Emotion scores (valence, arousal)
        """
        try:
            # Store in external memory
            interaction_key = embedding
            interaction_value = embedding  # Could be enhanced with more context
            
            self.external_memory.write(interaction_key, interaction_value)
            
            # Apply memory decay to existing memories
            self._apply_memory_decay()
            
            logger.info("Memory updated with new interaction")
            
        except Exception as e:
            logger.error(f"Error updating memory: {e}")
    
    def _get_memory_states(self, node_ids: List[str]) -> Optional[torch.Tensor]:
        """Get memory states for given node IDs"""
        try:
            states = []
            for node_id in node_ids:
                if node_id in self.node_memory_states:
                    states.append(self.node_memory_states[node_id])
                else:
                    # Initialize random state
                    state = torch.randn(settings.GNN_HIDDEN_DIM)
                    self.node_memory_states[node_id] = state
                    states.append(state)
            
            if states:
                return torch.stack(states).to(self.device)
            return None
            
        except Exception as e:
            logger.error(f"Error getting memory states: {e}")
            return None
    
    def _update_memory_states(self, node_ids: List[str], new_states: torch.Tensor):
        """Update memory states for given node IDs"""
        try:
            new_states_cpu = new_states.cpu()
            for i, node_id in enumerate(node_ids):
                if i < new_states_cpu.size(0):
                    self.node_memory_states[node_id] = new_states_cpu[i]
                    
        except Exception as e:
            logger.error(f"Error updating memory states: {e}")
    
    def _apply_memory_decay(self):
        """Apply decay factor to memory usage"""
        self.external_memory.usage *= settings.MEMORY_DECAY_FACTOR
        
        # Clean up very low usage memories
        threshold = 0.01
        low_usage_indices = np.where(self.external_memory.usage < threshold)[0]
        if len(low_usage_indices) > 0:
            # Reset low usage memories
            for idx in low_usage_indices[:len(low_usage_indices)//2]:  # Reset half
                self.external_memory.usage[idx] = 0.0
    
    def get_memory_statistics(self) -> Dict:
        """Get statistics about memory usage"""
        return {
            'total_nodes': len(self.node_memory_states),
            'external_memory_usage': self.external_memory.current_size,
            'external_memory_capacity': self.external_memory.memory_size,
            'average_memory_usage': np.mean(self.external_memory.usage),
            'device': str(self.device)
        }
