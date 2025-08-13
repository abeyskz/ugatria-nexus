"""
API routes for memory management
Handles memory node creation, search, and statistics
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import logging

from app.core.database import get_db
from app.models.memory import (
    MemoryNodeCreate, MemoryNodeResponse, MemoryEdgeCreate
)
from app.services.memory_manager import MemoryManager

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/nodes", response_model=MemoryNodeResponse)
async def create_memory_node(
    memory_data: MemoryNodeCreate,
    db: AsyncSession = Depends(get_db),
    app_request: Request = None
):
    """Create a new memory node"""
    try:
        memory_manager: MemoryManager = app_request.app.state.memory_manager
        
        memory_node = await memory_manager.create_memory_node(
            db=db,
            content=memory_data.content,
            memory_type=memory_data.memory_type,
            category=memory_data.category,
            valence=memory_data.valence,
            arousal=memory_data.arousal
        )
        
        return MemoryNodeResponse(
            id=str(memory_node.id),
            content=memory_node.content,
            memory_type=memory_node.memory_type,
            category=memory_node.category,
            valence=memory_node.valence,
            arousal=memory_node.arousal,
            activation_strength=memory_node.activation_strength,
            access_count=memory_node.access_count,
            created_at=memory_node.created_at,
            last_accessed=memory_node.last_accessed
        )
        
    except Exception as e:
        logger.error(f"Error creating memory node: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/search")
async def search_memories(
    query: str = Query(..., description="Search query"),
    limit: int = Query(10, ge=1, le=50, description="Number of results"),
    memory_type: Optional[str] = Query(None, description="Memory type filter"),
    min_activation: float = Query(0.1, ge=0.0, le=1.0, description="Minimum activation strength"),
    db: AsyncSession = Depends(get_db),
    app_request: Request = None
):
    """Search memories using vector similarity and GNN activation"""
    try:
        memory_manager: MemoryManager = app_request.app.state.memory_manager
        
        memories = await memory_manager.search_memories(
            db=db,
            query=query,
            limit=limit,
            memory_type=memory_type,
            min_activation=min_activation
        )
        
        return {
            "query": query,
            "results": memories,
            "total_results": len(memories)
        }
        
    except Exception as e:
        logger.error(f"Error searching memories: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/statistics")
async def get_memory_statistics(
    db: AsyncSession = Depends(get_db),
    app_request: Request = None
):
    """Get memory system statistics"""
    try:
        memory_manager: MemoryManager = app_request.app.state.memory_manager
        gnn_processor = app_request.app.state.gnn_processor
        
        # Get database statistics
        db_stats = await memory_manager.get_memory_statistics(db)
        
        # Get GNN processor statistics
        gnn_stats = gnn_processor.get_memory_statistics()
        
        return {
            "database_statistics": db_stats,
            "gnn_statistics": gnn_stats,
            "status": "healthy"
        }
        
    except Exception as e:
        logger.error(f"Error getting memory statistics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/edges")
async def create_memory_edge(
    edge_data: MemoryEdgeCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a connection between memory nodes"""
    try:
        # TODO: Implement edge creation logic
        # For now, return a placeholder
        return {
            "message": "Memory edge creation not yet implemented",
            "edge_data": edge_data
        }
        
    except Exception as e:
        logger.error(f"Error creating memory edge: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/cleanup")
async def cleanup_old_memories(
    days_threshold: int = Query(365, ge=30, description="Age threshold in days"),
    min_activation: float = Query(0.01, ge=0.0, le=1.0, description="Minimum activation threshold"),
    db: AsyncSession = Depends(get_db),
    app_request: Request = None
):
    """Clean up old and unused memories"""
    try:
        memory_manager: MemoryManager = app_request.app.state.memory_manager
        
        await memory_manager.cleanup_old_memories(
            db=db,
            days_threshold=days_threshold,
            min_activation=min_activation
        )
        
        return {
            "message": "Memory cleanup completed",
            "parameters": {
                "days_threshold": days_threshold,
                "min_activation": min_activation
            }
        }
        
    except Exception as e:
        logger.error(f"Error cleaning up memories: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/nodes/{node_id}")
async def get_memory_node(
    node_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific memory node by ID"""
    try:
        # TODO: Implement node retrieval logic
        return {
            "message": "Memory node retrieval not yet implemented",
            "node_id": node_id
        }
        
    except Exception as e:
        logger.error(f"Error getting memory node: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/nodes/{node_id}")
async def delete_memory_node(
    node_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete a memory node"""
    try:
        # TODO: Implement node deletion logic
        return {
            "message": "Memory node deletion not yet implemented",
            "node_id": node_id
        }
        
    except Exception as e:
        logger.error(f"Error deleting memory node: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
