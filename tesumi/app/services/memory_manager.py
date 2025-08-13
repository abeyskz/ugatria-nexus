"""
Memory Manager Service
Coordinates between database, GNN processor, and embedding generation
Handles Memolette functionality for memory DB management
"""

import asyncio
import logging
from typing import List, Dict, Optional, Tuple
import numpy as np
from datetime import datetime, timedelta
from sentence_transformers import SentenceTransformer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, func, text
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.memory import (
    MemoryNode, MemoryEdge, ConversationHistory,
    MemoryNodeCreate, MemoryNodeResponse
)
from app.services.gnn_processor import GNNProcessor
from app.services.claude_client import ClaudeClient
from app.core.config import settings

logger = logging.getLogger(__name__)


class MemoryManager:
    """
    Core memory management service
    Handles memory storage, retrieval, and activation using Memolette functionality
    """
    
    def __init__(self):
        self.embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL)
        self.gnn_processor = GNNProcessor()
        self.claude_client = ClaudeClient()
        
        # Cache for frequent operations
        self._embedding_cache = {}
        self._memory_cache = {}
        
        logger.info("Memory Manager initialized")
    
    async def create_memory_node(
        self,
        db: AsyncSession,
        content: str,
        memory_type: str = "episodic",
        category: Optional[str] = None,
        valence: float = 0.0,
        arousal: float = 0.0
    ) -> MemoryNode:
        """
        Create a new memory node with embedding and emotion coordinates
        
        Args:
            db: Database session
            content: Text content of the memory
            memory_type: Type of memory (episodic, semantic, procedural)
            category: Optional category
            valence: Emotion valence (-1 to 1)
            arousal: Emotion arousal (-1 to 1)
            
        Returns:
            Created memory node
        """
        try:
            # Generate embedding
            embedding = self.embedding_model.encode(content)
            
            # If emotion scores not provided, analyze them
            if valence == 0.0 and arousal == 0.0:
                emotion_scores = await self.claude_client.analyze_emotion(content)
                valence = emotion_scores.get('valence', 0.0)
                arousal = emotion_scores.get('arousal', 0.0)
            
            # Create memory node
            memory_node = MemoryNode(
                content=content,
                embedding=embedding.tolist(),
                memory_type=memory_type,
                category=category,
                valence=valence,
                arousal=arousal,
                activation_strength=1.0,
                access_count=0,
                created_at=datetime.utcnow(),
                last_accessed=datetime.utcnow()
            )
            
            db.add(memory_node)
            await db.commit()
            await db.refresh(memory_node)
            
            # Create connections to similar memories
            await self._create_similarity_edges(db, memory_node, embedding)
            
            logger.info(f"Created memory node: {memory_node.id}")
            return memory_node
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating memory node: {e}")
            raise
    
    async def search_memories(
        self,
        db: AsyncSession,
        query: str,
        limit: int = 10,
        memory_type: Optional[str] = None,
        min_activation: float = 0.1
    ) -> List[Dict]:
        """
        Search for memories using vector similarity and GNN activation
        
        Args:
            db: Database session
            query: Search query text
            limit: Maximum number of results
            memory_type: Optional memory type filter
            min_activation: Minimum activation strength
            
        Returns:
            List of activated memory dictionaries
        """
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode(query)
            
            # Get candidate memories from vector search
            vector_search_sql = text("""
                SELECT id, content, memory_type, category, valence, arousal, 
                       activation_strength, access_count, created_at, last_accessed,
                       embedding <=> :query_embedding AS distance
                FROM memory_nodes
                WHERE activation_strength >= :min_activation
                AND (:memory_type IS NULL OR memory_type = :memory_type)
                ORDER BY embedding <=> :query_embedding
                LIMIT :limit
            \"\"\")\n            \n            result = await db.execute(\n                vector_search_sql,\n                {\n                    \"query_embedding\": query_embedding.tolist(),\n                    \"min_activation\": min_activation,\n                    \"memory_type\": memory_type,\n                    \"limit\": limit * 3  # Get more candidates for GNN processing\n                }\n            )\n            \n            candidate_memories = []\n            for row in result.fetchall():\n                candidate_memories.append({\n                    'id': str(row[0]),\n                    'content': row[1],\n                    'memory_type': row[2],\n                    'category': row[3],\n                    'valence': row[4],\n                    'arousal': row[5],\n                    'activation_strength': row[6],\n                    'access_count': row[7],\n                    'created_at': row[8],\n                    'last_accessed': row[9],\n                    'embedding': query_embedding.tolist(),  # Placeholder\n                    'vector_distance': row[10]\n                })\n            \n            if not candidate_memories:\n                return []\n            \n            # Get memory edges for GNN processing\n            memory_ids = [m['id'] for m in candidate_memories]\n            edges_result = await db.execute(\n                select(MemoryEdge).where(\n                    or_(\n                        MemoryEdge.source_id.in_(memory_ids),\n                        MemoryEdge.target_id.in_(memory_ids)\n                    )\n                )\n            )\n            \n            memory_edges = []\n            for edge in edges_result.scalars().all():\n                memory_edges.append({\n                    'id': str(edge.id),\n                    'source_id': str(edge.source_id),\n                    'target_id': str(edge.target_id),\n                    'edge_type': edge.edge_type,\n                    'weight': edge.weight\n                })\n            \n            # Use GNN processor to activate memories\n            activated_memories = self.gnn_processor.activate_memories(\n                memory_nodes=candidate_memories,\n                memory_edges=memory_edges,\n                query_embedding=query_embedding,\n                top_k=limit\n            )\n            \n            # Update access counts and last accessed time\n            await self._update_memory_access(db, [m['id'] for m in activated_memories])\n            \n            return activated_memories\n            \n        except Exception as e:\n            logger.error(f\"Error searching memories: {e}\")\n            return []\n    \n    async def get_conversation_context(\n        self,\n        db: AsyncSession,\n        session_id: str,\n        limit: int = 5\n    ) -> List[Dict]:\n        \"\"\"Get recent conversation history for context\"\"\"\n        try:\n            result = await db.execute(\n                select(ConversationHistory)\n                .where(ConversationHistory.session_id == session_id)\n                .order_by(desc(ConversationHistory.created_at))\n                .limit(limit)\n            )\n            \n            conversations = result.scalars().all()\n            return [\n                {\n                    'user_input': conv.user_input,\n                    'system_response': conv.system_response,\n                    'created_at': conv.created_at,\n                    'activated_memories': conv.activated_memories or []\n                }\n                for conv in reversed(conversations)  # Reverse to get chronological order\n            ]\n            \n        except Exception as e:\n            logger.error(f\"Error getting conversation context: {e}\")\n            return []\n    \n    async def store_conversation(\n        self,\n        db: AsyncSession,\n        session_id: str,\n        user_input: str,\n        system_response: str,\n        activated_memories: List[str] = None\n    ) -> ConversationHistory:\n        \"\"\"Store conversation history\"\"\"\n        try:\n            conversation = ConversationHistory(\n                session_id=session_id,\n                user_input=user_input,\n                system_response=system_response,\n                activated_memories=activated_memories or [],\n                created_at=datetime.utcnow()\n            )\n            \n            db.add(conversation)\n            await db.commit()\n            await db.refresh(conversation)\n            \n            # Create memory node from conversation if significant\n            await self._create_conversation_memory(\n                db, user_input, system_response, activated_memories\n            )\n            \n            return conversation\n            \n        except Exception as e:\n            await db.rollback()\n            logger.error(f\"Error storing conversation: {e}\")\n            raise\n    \n    async def get_memory_statistics(self, db: AsyncSession) -> Dict:\n        \"\"\"Get memory system statistics\"\"\"\n        try:\n            # Basic statistics\n            total_memories = await db.scalar(select(func.count(MemoryNode.id)))\n            total_edges = await db.scalar(select(func.count(MemoryEdge.id)))\n            \n            # Memory type distribution\n            memory_types = await db.execute(\n                select(MemoryNode.memory_type, func.count(MemoryNode.id))\n                .group_by(MemoryNode.memory_type)\n            )\n            \n            type_distribution = {row[0]: row[1] for row in memory_types.fetchall()}\n            \n            # Recent activity\n            recent_threshold = datetime.utcnow() - timedelta(hours=24)\n            recent_memories = await db.scalar(\n                select(func.count(MemoryNode.id))\n                .where(MemoryNode.created_at >= recent_threshold)\n            )\n            \n            # Average activation strength\n            avg_activation = await db.scalar(\n                select(func.avg(MemoryNode.activation_strength))\n            )\n            \n            # GNN processor statistics\n            gnn_stats = self.gnn_processor.get_memory_statistics()\n            \n            return {\n                'total_memories': total_memories,\n                'total_edges': total_edges,\n                'memory_types': type_distribution,\n                'recent_memories_24h': recent_memories,\n                'average_activation': float(avg_activation or 0),\n                'gnn_statistics': gnn_stats,\n                'embedding_model': settings.EMBEDDING_MODEL,\n                'vector_dimension': settings.VECTOR_DIMENSION\n            }\n            \n        except Exception as e:\n            logger.error(f\"Error getting memory statistics: {e}\")\n            return {}\n    \n    async def _create_similarity_edges(\n        self, \n        db: AsyncSession, \n        new_node: MemoryNode, \n        embedding: np.ndarray,\n        similarity_threshold: float = 0.7,\n        max_connections: int = 5\n    ):\n        \"\"\"Create similarity edges to existing memories\"\"\"\n        try:\n            # Find similar memories using vector search\n            similar_search_sql = text(\"\"\"\n                SELECT id, embedding <=> :embedding AS similarity\n                FROM memory_nodes\n                WHERE id != :node_id\n                AND embedding <=> :embedding < :threshold\n                ORDER BY embedding <=> :embedding\n                LIMIT :max_connections\n            \"\"\")\n            \n            result = await db.execute(\n                similar_search_sql,\n                {\n                    \"embedding\": embedding.tolist(),\n                    \"node_id\": str(new_node.id),\n                    \"threshold\": 1.0 - similarity_threshold,  # pgvector uses distance, not similarity\n                    \"max_connections\": max_connections\n                }\n            )\n            \n            # Create edges to similar memories\n            for row in result.fetchall():\n                similar_id = row[0]\n                distance = row[1]\n                similarity = 1.0 - distance  # Convert distance to similarity\n                \n                if similarity >= similarity_threshold:\n                    edge = MemoryEdge(\n                        source_id=new_node.id,\n                        target_id=similar_id,\n                        edge_type=\"similarity\",\n                        weight=similarity,\n                        created_at=datetime.utcnow()\n                    )\n                    db.add(edge)\n            \n            await db.commit()\n            \n        except Exception as e:\n            logger.error(f\"Error creating similarity edges: {e}\")\n            await db.rollback()\n    \n    async def _create_conversation_memory(\n        self,\n        db: AsyncSession,\n        user_input: str,\n        system_response: str,\n        activated_memories: List[str] = None\n    ):\n        \"\"\"Create memory node from significant conversations\"\"\"\n        try:\n            # Determine if conversation is significant enough to store as memory\n            combined_text = f\"ユーザー: {user_input}\\nシステム: {system_response}\"\n            \n            # Simple heuristic: store if conversation is long enough or contains certain keywords\n            significant_keywords = [\"重要\", \"覚えて\", \"記録\", \"記憶\", \"忘れない\"]\n            is_significant = (\n                len(combined_text) > 100 or  # Long conversation\n                any(keyword in combined_text for keyword in significant_keywords) or  # Contains keywords\n                len(activated_memories or []) > 2  # Many memories were activated\n            )\n            \n            if is_significant:\n                # Analyze emotion of the conversation\n                emotion_scores = await self.claude_client.analyze_emotion(combined_text)\n                \n                await self.create_memory_node(\n                    db=db,\n                    content=combined_text,\n                    memory_type=\"episodic\",\n                    category=\"conversation\",\n                    valence=emotion_scores.get('valence', 0.0),\n                    arousal=emotion_scores.get('arousal', 0.0)\n                )\n                \n                logger.info(\"Created memory node from significant conversation\")\n            \n        except Exception as e:\n            logger.error(f\"Error creating conversation memory: {e}\")\n    \n    async def _update_memory_access(\n        self,\n        db: AsyncSession,\n        memory_ids: List[str]\n    ):\n        \"\"\"Update access count and last accessed time for memories\"\"\"\n        try:\n            if not memory_ids:\n                return\n            \n            update_sql = text(\"\"\"\n                UPDATE memory_nodes \n                SET access_count = access_count + 1,\n                    last_accessed = :now,\n                    activation_strength = LEAST(activation_strength * 1.1, 1.0)\n                WHERE id = ANY(:memory_ids)\n            \"\"\")\n            \n            await db.execute(\n                update_sql,\n                {\n                    \"now\": datetime.utcnow(),\n                    \"memory_ids\": memory_ids\n                }\n            )\n            \n            await db.commit()\n            \n        except Exception as e:\n            logger.error(f\"Error updating memory access: {e}\")\n            await db.rollback()\n    \n    def get_embedding(self, text: str) -> np.ndarray:\n        \"\"\"Get embedding for text with caching\"\"\"\n        if text in self._embedding_cache:\n            return self._embedding_cache[text]\n        \n        embedding = self.embedding_model.encode(text)\n        \n        # Cache recent embeddings (limit cache size)\n        if len(self._embedding_cache) > 1000:\n            # Remove oldest entries (simple FIFO)\n            oldest_key = next(iter(self._embedding_cache))\n            del self._embedding_cache[oldest_key]\n        \n        self._embedding_cache[text] = embedding\n        return embedding\n    \n    async def cleanup_old_memories(\n        self,\n        db: AsyncSession,\n        days_threshold: int = 365,\n        min_activation: float = 0.01\n    ):\n        \"\"\"Clean up old and unused memories\"\"\"\n        try:\n            cutoff_date = datetime.utcnow() - timedelta(days=days_threshold)\n            \n            # Find old memories with low activation\n            old_memories = await db.execute(\n                select(MemoryNode.id)\n                .where(\n                    and_(\n                        MemoryNode.created_at < cutoff_date,\n                        MemoryNode.activation_strength < min_activation,\n                        MemoryNode.access_count < 2\n                    )\n                )\n            )\n            \n            memory_ids_to_delete = [str(row[0]) for row in old_memories.fetchall()]\n            \n            if memory_ids_to_delete:\n                # Delete associated edges first\n                await db.execute(\n                    select(MemoryEdge).where(\n                        or_(\n                            MemoryEdge.source_id.in_(memory_ids_to_delete),\n                            MemoryEdge.target_id.in_(memory_ids_to_delete)\n                        )\n                    ).delete()\n                )\n                \n                # Delete memory nodes\n                await db.execute(\n                    select(MemoryNode).where(\n                        MemoryNode.id.in_(memory_ids_to_delete)\n                    ).delete()\n                )\n                \n                await db.commit()\n                logger.info(f\"Cleaned up {len(memory_ids_to_delete)} old memories\")\n            \n        except Exception as e:\n            logger.error(f\"Error cleaning up old memories: {e}\")\n            await db.rollback()
