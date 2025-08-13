#!/usr/bin/env python3
"""
Tesumi System v2.0 - API版かなた（テスミちゃん）
Memory Inheritance System with GNN-based memory management and Claude API integration
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
import logging
from typing import List, Optional

from app.core.config import settings
from app.core.database import init_db, close_db
from app.api.routes import memory, conversation, report
from app.services.memory_manager import MemoryManager
from app.services.claude_client import ClaudeClient
from app.services.gnn_processor import GNNProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Starting Tesumi System v2.0...")
    
    # Initialize database
    await init_db()
    
    # Initialize core services
    app.state.memory_manager = MemoryManager()
    app.state.claude_client = ClaudeClient()
    app.state.gnn_processor = GNNProcessor()
    
    logger.info("Tesumi System v2.0 started successfully")
    
    yield
    
    # Cleanup
    logger.info("Shutting down Tesumi System v2.0...")
    await close_db()


app = FastAPI(
    title="Tesumi System v2.0 - API版かなた",
    description="Memory Inheritance System with GNN-based memory management",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(memory.router, prefix="/api/memory", tags=["memory"])
app.include_router(conversation.router, prefix="/api/conversation", tags=["conversation"])
app.include_router(report.router, prefix="/api/report", tags=["report"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Tesumi System v2.0 - API版かなた",
        "version": "2.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
