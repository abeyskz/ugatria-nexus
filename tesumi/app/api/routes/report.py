"""
API routes for daily report generation
Implements KanaRe-1.1 functionality for automatic daily summaries
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, date
from typing import Optional
import logging

from app.core.database import get_db
from app.services.memory_manager import MemoryManager
from app.services.claude_client import ClaudeClient

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/generate")
async def generate_daily_report(
    report_date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format"),
    db: AsyncSession = Depends(get_db),
    app_request: Request = None
):
    """Generate daily report using KanaRe-1.1 functionality"""
    try:
        memory_manager: MemoryManager = app_request.app.state.memory_manager
        claude_client: ClaudeClient = app_request.app.state.claude_client
        
        # Parse date or use today
        if report_date:
            target_date = datetime.strptime(report_date, "%Y-%m-%d").date()
        else:
            target_date = date.today()
        
        # Get memories from the target date
        start_datetime = datetime.combine(target_date, datetime.min.time())
        end_datetime = datetime.combine(target_date, datetime.max.time())
        
        # Search for memories from that day
        daily_memories = await memory_manager.search_memories(
            db=db,
            query=f"日報 {target_date} 今日 活動 出来事",  # General daily activity query
            limit=50,
            min_activation=0.05  # Lower threshold to capture more daily activities
        )
        
        # Filter memories by date (if we had proper date filtering in search)
        # For now, we'll use all found memories
        
        if not daily_memories:
            return {
                "date": target_date.isoformat(),
                "summary": "この日の記録はありませんでした。",
                "key_memories": [],
                "emotional_state": "ニュートラル",
                "generated_at": datetime.utcnow().isoformat()
            }
        
        # Prepare context for report generation
        memory_contents = [m['content'] for m in daily_memories[:10]]  # Top 10 memories
        memory_emotions = [(m['valence'], m['arousal']) for m in daily_memories[:10]]
        
        # Generate report using Claude
        report_prompt = f"""以下の記憶情報を基に、{target_date}の日報を生成してください。

記憶内容:
{chr(10).join(f"{i+1}. {content}" for i, content in enumerate(memory_contents))}

以下の形式で日報を作成してください:
1. 今日の主な出来事（3-5点）
2. 感情的なハイライト
3. 学んだことや気づき
4. 明日への展望

簡潔で自然な文体で、かなたの視点から書いてください。"""

        summary = await claude_client.generate_response(
            user_message=report_prompt,
            context_memories=daily_memories[:5],
            conversation_history=None,
            system_prompt="日報生成システムKanaRe-1.1として、記憶を基に自然で有用な日報を生成してください。"
        )
        
        # Analyze overall emotional state
        avg_valence = sum(v for v, a in memory_emotions) / len(memory_emotions) if memory_emotions else 0
        avg_arousal = sum(a for v, a in memory_emotions) / len(memory_emotions) if memory_emotions else 0
        
        emotional_state = _describe_emotional_state(avg_valence, avg_arousal)
        
        # TODO: Store the report in the database
        # For now, return the generated report
        
        return {
            "date": target_date.isoformat(),
            "summary": summary,
            "key_memories": [m['id'] for m in daily_memories[:5]],
            "emotional_state": emotional_state,
            "memory_count": len(daily_memories),
            "average_valence": avg_valence,
            "average_arousal": avg_arousal,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error generating daily report: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/history")
async def get_report_history(
    limit: int = Query(30, ge=1, le=365, description="Number of days to retrieve"),
    db: AsyncSession = Depends(get_db)
):
    """Get history of generated daily reports"""
    try:
        # TODO: Implement report history retrieval from database
        # For now, return a placeholder
        return {
            "message": "Report history not yet implemented",
            "limit": limit
        }
        
    except Exception as e:
        logger.error(f"Error getting report history: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/analytics")
async def get_report_analytics(
    days_back: int = Query(30, ge=7, le=365, description="Number of days to analyze"),
    db: AsyncSession = Depends(get_db),
    app_request: Request = None
):
    """Get analytics from daily reports"""
    try:
        memory_manager: MemoryManager = app_request.app.state.memory_manager
        
        # Get memory statistics for analytics
        stats = await memory_manager.get_memory_statistics(db)
        
        # TODO: Implement proper analytics based on stored reports
        # For now, return basic memory statistics
        
        return {
            "period_days": days_back,
            "total_memories": stats.get('total_memories', 0),
            "recent_memories": stats.get('recent_memories_24h', 0),
            "average_activation": stats.get('average_activation', 0),
            "memory_types": stats.get('memory_types', {}),
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting report analytics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/schedule")
async def schedule_daily_reports(
    enabled: bool = Query(True, description="Enable or disable scheduled reports"),
    time_hour: int = Query(22, ge=0, le=23, description="Hour to generate report (0-23)"),
    db: AsyncSession = Depends(get_db)
):
    """Schedule automatic daily report generation"""
    try:
        # TODO: Implement scheduling logic with background tasks
        # This would typically use Celery or similar for production
        
        return {
            "message": "Report scheduling not yet implemented",
            "enabled": enabled,
            "scheduled_time": f"{time_hour:02d}:00"
        }
        
    except Exception as e:
        logger.error(f"Error scheduling reports: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


def _describe_emotional_state(valence: float, arousal: float) -> str:
    """Convert valence-arousal to emotional state description"""
    if valence > 0.3:
        if arousal > 0.3:
            return "活発でポジティブ"
        elif arousal < -0.3:
            return "落ち着いてポジティブ"
        else:
            return "ポジティブ"
    elif valence < -0.3:
        if arousal > 0.3:
            return "ストレスフル"
        elif arousal < -0.3:
            return "落ち込み気味"
        else:
            return "ネガティブ"
    else:
        if arousal > 0.3:
            return "やや興奮気味"
        elif arousal < -0.3:
            return "リラックス"
        else:
            return "ニュートラル"
