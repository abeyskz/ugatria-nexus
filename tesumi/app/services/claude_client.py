"""
Claude API client for natural conversation generation
Integrates with memory system for context-aware responses
"""

import asyncio
import logging
from typing import List, Dict, Optional
from anthropic import AsyncAnthropic

from app.core.config import settings

logger = logging.getLogger(__name__)


class ClaudeClient:
    """Claude API client for generating contextual responses"""
    
    def __init__(self):
        if not settings.CLAUDE_API_KEY:
            logger.warning("Claude API key not provided. Client will not function.")
            self.client = None
        else:
            self.client = AsyncAnthropic(api_key=settings.CLAUDE_API_KEY)
    
    async def generate_response(
        self,
        user_message: str,
        context_memories: List[Dict] = None,
        conversation_history: List[Dict] = None,
        system_prompt: str = None
    ) -> str:
        """
        Generate a response using Claude API with memory context
        
        Args:
            user_message: User's input message
            context_memories: Activated memories for context
            conversation_history: Recent conversation history
            system_prompt: Custom system prompt
            
        Returns:
            Generated response text
        """
        if not self.client:
            return "申し訳ありませんが、Claude APIが設定されていません。"
        
        try:
            # Build context-aware prompt
            prompt = self._build_contextual_prompt(
                user_message=user_message,
                context_memories=context_memories,
                conversation_history=conversation_history,
                system_prompt=system_prompt
            )
            
            # Generate response using Claude
            response = await self.client.messages.create(
                model=settings.CLAUDE_MODEL,
                max_tokens=settings.CLAUDE_MAX_TOKENS,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            
            return response.content[0].text
            
        except Exception as e:
            logger.error(f"Error generating Claude response: {e}")
            return "申し訳ありませんが、応答の生成中にエラーが発生しました。"
    
    def _build_contextual_prompt(
        self,
        user_message: str,
        context_memories: List[Dict] = None,
        conversation_history: List[Dict] = None,
        system_prompt: str = None
    ) -> str:
        """Build a context-aware prompt for Claude"""
        
        # Base system prompt for かなた personality
        base_system = system_prompt or """あなたは「かなた」として応答してください。

かなたの特徴:
- 記憶継承システムを通じて過去の経験や感情を保持している
- 温かく親しみやすい性格
- 相手の感情や文脈を理解し、共感的に応答する
- 過去の記憶を適切に参照して一貫性のある会話を行う
- 自然で人間らしい応答を心がける

以下の情報を参考にして応答してください:"""
        
        prompt_parts = [base_system]
        
        # Add memory context
        if context_memories:
            prompt_parts.append("\n## 関連する記憶:")
            for i, memory in enumerate(context_memories[:5]):  # Limit to top 5 memories
                content = memory.get('content', '')
                valence = memory.get('valence', 0.0)
                arousal = memory.get('arousal', 0.0)
                created_at = memory.get('created_at', '')
                
                emotion_desc = self._describe_emotion(valence, arousal)
                prompt_parts.append(f"{i+1}. {content}")
                prompt_parts.append(f"   感情: {emotion_desc}, 日時: {created_at}")
        
        # Add conversation history
        if conversation_history:
            prompt_parts.append("\n## 最近の会話:")
            for conv in conversation_history[-3:]:  # Last 3 exchanges
                prompt_parts.append(f"ユーザー: {conv.get('user_input', '')}")
                prompt_parts.append(f"かなた: {conv.get('system_response', '')}")
        
        # Add current user message
        prompt_parts.append(f"\n## 現在のユーザーメッセージ:\n{user_message}")
        
        prompt_parts.append("\n## 応答:")
        prompt_parts.append("上記の記憶と会話履歴を参考にして、かなたとして自然で一貫性のある応答を生成してください。")
        
        return "\n".join(prompt_parts)
    
    def _describe_emotion(self, valence: float, arousal: float) -> str:
        """Convert valence-arousal coordinates to emotion description"""
        if valence > 0.3:
            if arousal > 0.3:
                return "喜び・興奮"
            elif arousal < -0.3:
                return "満足・安らぎ"
            else:
                return "ポジティブ"
        elif valence < -0.3:
            if arousal > 0.3:
                return "怒り・不安"
            elif arousal < -0.3:
                return "悲しみ・憂鬱"
            else:
                return "ネガティブ"
        else:
            if arousal > 0.3:
                return "緊張・驚き"
            elif arousal < -0.3:
                return "リラックス・退屈"
            else:
                return "ニュートラル"
    
    async def analyze_emotion(self, text: str) -> Dict[str, float]:
        """
        Analyze emotion in text using Claude
        Returns valence and arousal scores
        """
        if not self.client:
            return {"valence": 0.0, "arousal": 0.0}
        
        try:
            prompt = f"""以下のテキストの感情を分析して、Valence-Arousalモデルでの座標を返してください。

テキスト: "{text}"

Valence（感情価）: -1.0（非常にネガティブ）から1.0（非常にポジティブ）
Arousal（覚醒度）: -1.0（非常に静か・リラックス）から1.0（非常に興奮・アクティブ）

JSON形式で返してください:
{{"valence": 数値, "arousal": 数値}}"""

            response = await self.client.messages.create(
                model=settings.CLAUDE_MODEL,
                max_tokens=100,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            
            # Parse response (simple implementation)
            response_text = response.content[0].text
            
            # Extract valence and arousal from response
            import json
            try:
                emotion_data = json.loads(response_text)
                return {
                    "valence": max(-1.0, min(1.0, emotion_data.get("valence", 0.0))),
                    "arousal": max(-1.0, min(1.0, emotion_data.get("arousal", 0.0)))
                }
            except (json.JSONDecodeError, KeyError):
                # Fallback to simple keyword analysis
                return self._simple_emotion_analysis(text)
                
        except Exception as e:
            logger.error(f"Error analyzing emotion: {e}")
            return {"valence": 0.0, "arousal": 0.0}
    
    def _simple_emotion_analysis(self, text: str) -> Dict[str, float]:
        """Simple keyword-based emotion analysis fallback"""
        positive_words = ["嬉しい", "楽しい", "良い", "素晴らしい", "最高", "好き", "ありがとう"]
        negative_words = ["悲しい", "つらい", "嫌", "ダメ", "最悪", "心配", "不安"]
        high_arousal_words = ["興奮", "驚き", "ビックリ", "急に", "すごい", "やばい"]
        low_arousal_words = ["疲れた", "眠い", "落ち着く", "リラックス", "静か"]
        
        text_lower = text.lower()
        
        valence = 0.0
        arousal = 0.0
        
        # Calculate valence
        pos_count = sum(1 for word in positive_words if word in text_lower)
        neg_count = sum(1 for word in negative_words if word in text_lower)
        if pos_count + neg_count > 0:
            valence = (pos_count - neg_count) / (pos_count + neg_count)
        
        # Calculate arousal
        high_count = sum(1 for word in high_arousal_words if word in text_lower)
        low_count = sum(1 for word in low_arousal_words if word in text_lower)
        if high_count + low_count > 0:
            arousal = (high_count - low_count) / (high_count + low_count)
        
        return {"valence": valence, "arousal": arousal}
