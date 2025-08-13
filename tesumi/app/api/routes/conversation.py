"""
API routes for conversation handling
Integrates memory activation with Claude API for contextual responses
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import uuid
import logging

from app.core.database import get_db
from app.models.memory import ConversationRequest, ConversationResponse
from app.services.memory_manager import MemoryManager
from app.services.claude_client import ClaudeClient

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/chat", response_model=ConversationResponse)
async def chat(
    request: ConversationRequest,
    db: AsyncSession = Depends(get_db),
    app_request: Request = None
):
    """
    Main conversation endpoint
    Activates memories and generates contextual response using Claude API
    """
    try:
        # Get services from app state
        memory_manager: MemoryManager = app_request.app.state.memory_manager
        claude_client: ClaudeClient = app_request.app.state.claude_client
        
        # Generate session ID if not provided
        if not request.session_id:
            request.session_id = str(uuid.uuid4())
        
        # Search for relevant memories
        activated_memories = await memory_manager.search_memories(
            db=db,
            query=request.message,
            limit=10,
            min_activation=0.1
        )
        
        # Get conversation history for context
        conversation_context = await memory_manager.get_conversation_context(
            db=db,
            session_id=request.session_id,
            limit=5
        )
        
        # Generate response using Claude API
        response_text = await claude_client.generate_response(
            user_message=request.message,
            context_memories=activated_memories,
            conversation_history=conversation_context
        )
        
        # Store conversation in database
        await memory_manager.store_conversation(
            db=db,
            session_id=request.session_id,
            user_input=request.message,
            system_response=response_text,
            activated_memories=[m['id'] for m in activated_memories]
        )
        
        return ConversationResponse(
            response=response_text,
            session_id=request.session_id,
            activated_memories=[m['id'] for m in activated_memories]
        )
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/sessions/{session_id}/history")
async def get_conversation_history(
    session_id: str,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    app_request: Request = None
):
    """Get conversation history for a session"""
    try:
        memory_manager: MemoryManager = app_request.app.state.memory_manager
        
        history = await memory_manager.get_conversation_context(
            db=db,
            session_id=session_id,
            limit=limit
        )
        
        return {"session_id": session_id, "history": history}
        
    except Exception as e:
        logger.error(f"Error getting conversation history: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/sessions/{session_id}/reset")
async def reset_session(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Reset/clear a conversation session"""
    # In a more complete implementation, you might want to archive or delete
    # the conversation history for this session
    return {"message": f"Session {session_id} reset successfully"}


@router.get("/sessions/{session_id}/memories")
async def get_session_memories(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    app_request: Request = None
):
    """Get all memories activated during a conversation session"""
    try:
        memory_manager: MemoryManager = app_request.app.state.memory_manager
        
        # Get conversation history
        conversations = await memory_manager.get_conversation_context(
            db=db,
            session_id=session_id,
            limit=100  # Get all conversations
        )
        
        # Collect all activated memory IDs
        all_memory_ids = set()
        for conv in conversations:
            all_memory_ids.update(conv.get('activated_memories', []))
        
        # TODO: Fetch actual memory details from database
        # For now, return just the IDs
        return {
            "session_id": session_id,
            "activated_memory_ids": list(all_memory_ids),
            "total_memories": len(all_memory_ids)
        }
        
    except Exception as e:
        logger.error(f"Error getting session memories: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
