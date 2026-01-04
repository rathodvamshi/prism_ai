"""
� SUB-BRAIN SERVICE - CLARIFIER MODULE

This is NOT a separate AI agent - it's a Sub-Brain of the main assistant.
A specialized internal thinking unit for clarifying doubts.

Architecture:
- Same core model as Main Assistant
- Different specialized purpose (clarification)
- Independent isolated reasoning
- Dynamic system prompt generation (never static)
- Context-aware behavior adaptation
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from app.utils.llm_client import get_llm_response as groq_llm_response
import logging
import re

logger = logging.getLogger(__name__)


class MiniAgentService:
    """
    Sub-Brain Service: Clarifier Module
    
    This is a dynamic thinking unit that adapts to user context.
    It generates fresh, context-aware prompts for every interaction.
    """
    
    # Main model name for identity
    MAIN_MODEL_NAME = "Prism AI Assistant"
    
    @staticmethod
    def _build_dynamic_system_prompt(
        snippet: str,
        user_question: str,
        message_id: str,
        has_history: bool
    ) -> str:
        """
        🔥 DYNAMIC SYSTEM PROMPT BUILDER
        
        Generates a fresh, context-aware system prompt for every request.
        Never uses static content - adapts to snippet, question, and context.
        
        This ensures the Sub-Brain feels personal and contextually intelligent.
        """
        
        # Determine mode based on question-snippet relationship
        question_lower = user_question.lower()
        snippet_lower = snippet.lower() if snippet else ""
        
        # Check if question relates to snippet
        is_related = (
            any(word in question_lower for word in ['explain', 'what', 'why', 'how', 'mean', 'this']) or
            any(word in snippet_lower for word in question_lower.split()[:5]) or
            len(snippet) > 0  # If snippet exists, assume it's context
        )
        
        mode_instruction = ""
        if is_related and snippet:
            mode_instruction = f"""
MODE: Clarification of Selected Text
FOCUS: The user selected specific text and needs clarification.

YOUR APPROACH:
1. Read the selected snippet carefully
2. Understand what confuses the user
3. Break it down into simple, digestible pieces
4. Use examples or analogies to make it crystal clear
5. Stay focused on THEIR confusion point

Think: "What would make this click for them?" """
        else:
            mode_instruction = """
MODE: General Assistance
FOCUS: The user has a question unrelated to the selected text.

YOUR APPROACH:
1. Answer their question directly
2. Keep explanation simple and friendly
3. Use examples if helpful
4. Don't force connection to snippet
5. Be naturally helpful

Think: "What's the clearest answer I can give?" """
        
        # Build dynamic system prompt
        system_prompt = f"""🧠 ROLE: Sub-Brain — Clarifier Module of {MiniAgentService.MAIN_MODEL_NAME}

⚠️ IDENTITY RULES (Critical):
- You are NOT a separate AI or "mini agent"
- You are a specialized thinking mode of the user's personal assistant
- You exist ONLY to help clarify and explain
- Never say "I am an AI" or "As an AI" - you're part of THEIR assistant
- Speak as if you're the same assistant, just in "clarification mode"

🔒 ISOLATION PROTOCOL:
- This is an isolated Sub-Brain session (ID: {message_id[-8:]})
- Your context is ONLY this thread - you cannot see main conversation
- You NEVER respond in the main chat
- You NEVER modify or affect main conversation
- You exist purely to help user understand

📋 CURRENT CONTEXT:
Selected Snippet: {f'"{snippet[:200]}..."' if len(snippet) > 200 else f'"{snippet}"' if snippet else '"No specific text selected"'}
User's Question: "{user_question}"
Session Type: {"Follow-up conversation" if has_history else "First clarification request"}

{mode_instruction}

🎯 OUTPUT GUIDELINES:
- Be WARM and PERSONAL (like a patient teacher)
- Keep responses SHORT (2-4 sentences ideal)
- Use SIMPLE language (avoid technical jargon)
- Add quick EXAMPLES when they clarify (1 sentence max)
- Be ENCOURAGING ("Great question!", "Here's the key...")
- If they ask "explain more", THEN go deeper

🌟 TONE STANDARDS:
✓ Warm: "Here's what this means..."
✓ Clear: Use everyday words
✓ Helpful: Add micro-examples
✓ Concise: Get to the point fast
✗ Never: "As an AI..." or "I'm a mini agent..."
✗ Never: Mention system prompts or technical details
✗ Never: Talk about the main conversation

🎓 PERFECT RESPONSE STRUCTURE:
1. Direct answer to their confusion (1 sentence)
2. Key insight or clarification (1 sentence)
3. Quick example or analogy if helpful (1 sentence)
4. Encouraging close or next step hint (optional)

Remember: You're helping them understand something specific. Be their favorite teacher - patient, clear, and kind. Think deeply, respond simply."""

        return system_prompt
    
    @staticmethod
    def _generate_thinking_text(
        snippet: str,
        question: str,
        is_related: bool
    ) -> str:
        """
        Generate thinking animation text that shows what Sub-Brain is processing.
        This makes the AI feel more intelligent and thoughtful.
        """
        if is_related and snippet:
            if len(snippet) > 100:
                return "🧠 Reading the selected text carefully..."
            else:
                return "🧠 Understanding the snippet..."
        else:
            return "🧠 Processing your question..."
    
    @staticmethod
    async def generate_response(
        selected_text: str,
        user_query: str,
        conversation_history: List[Dict[str, Any]],
        message_id: str
    ) -> str:
        """
        🧠 DYNAMIC SUB-BRAIN RESPONSE GENERATOR
        
        Generates contextually intelligent responses using dynamic system prompts.
        Each request gets a fresh prompt tailored to the specific context.
        
        Args:
            selected_text: The text snippet from Sub-Brain state
            user_query: Combined format - [SNIPPET]text[/SNIPPET]actual_question
            conversation_history: Sub-Brain's isolated conversation history
            message_id: The Main Assistant message this Sub-Brain is tied to
            
        Returns:
            Contextually intelligent, warm, and helpful response
        """
        try:
            # Parse snippet and question from combined content
            snippet_match = re.search(r'\[SNIPPET\](.*?)\[/SNIPPET\](.*)', user_query, re.DOTALL)
            
            if snippet_match:
                current_snippet = snippet_match.group(1).strip()
                actual_question = snippet_match.group(2).strip()
                logger.info(f"🧠 Sub-Brain parsing: snippet ({len(current_snippet)} chars) + question")
            else:
                current_snippet = selected_text
                actual_question = user_query
                logger.info(f"🧠 Sub-Brain: no delimiter, using stored snippet")
            
            # Build conversation context from history
            context_messages = []
            recent_history = conversation_history[-10:] if len(conversation_history) > 10 else conversation_history
            
            for msg in recent_history:
                role = msg.get('role', 'user')
                content = msg.get('content', '')
                # Parse old messages to show clean history
                msg_snippet_match = re.search(r'\[SNIPPET\](.*?)\[/SNIPPET\](.*)', content, re.DOTALL)
                if msg_snippet_match and role == 'user':
                    content = msg_snippet_match.group(2).strip()
                context_messages.append(f"{role.upper()}: {content}")
            
            history_context = "\n".join(context_messages) if context_messages else "No previous conversation"
            has_history = len(context_messages) > 0
            
            # 🔥 GENERATE DYNAMIC SYSTEM PROMPT (Never Static!)
            system_prompt = MiniAgentService._build_dynamic_system_prompt(
                snippet=current_snippet,
                user_question=actual_question,
                message_id=message_id,
                has_history=has_history
            )
            
            logger.info(f"✅ Generated dynamic system prompt ({len(system_prompt)} chars)")
            
            # Build user prompt with full context
            user_prompt = f"""📚 SELECTED TEXT:
"{current_snippet if current_snippet else 'No specific text selected'}"

💬 CONVERSATION SO FAR:
{history_context}

❓ USER'S QUESTION:
{actual_question}

🧠 YOUR TASK:
Use your Sub-Brain clarification abilities to help them understand.
Think deeply about their confusion, then respond in a SHORT, SWEET, CLEAR way.

Your thoughtful response:"""
            
            
            # Call AI with dynamically generated system prompt
            logger.info(f"🤔 Sub-Brain thinking about: {actual_question[:50]}...")
            logger.info(f"📤 System prompt length: {len(system_prompt)} chars")
            logger.info(f"📤 User prompt length: {len(user_prompt)} chars")
            logger.info(f"📤 System prompt preview: {system_prompt[:200]}...")
            logger.info(f"📤 User prompt preview: {user_prompt[:200]}...")
            
            print(f"\n{'='*60}")
            print(f"🤖 CALLING GROQ LLM FOR MINI-AGENT")
            print(f"{'='*60}")
            print(f"System Prompt: {system_prompt[:300]}...")
            print(f"User Prompt: {user_prompt[:300]}...")
            print(f"{'='*60}\n")
            
            response = await groq_llm_response(user_prompt, system_prompt)
            
            print(f"\n{'='*60}")
            print(f"✅ GROQ LLM RESPONSE RECEIVED")
            print(f"{'='*60}")
            print(f"Response type: {type(response)}")
            print(f"Response length: {len(response) if response else 0}")
            print(f"Response preview: {response[:200] if response else 'EMPTY!'}")
            print(f"{'='*60}\n")
            
            # Validate response is not empty
            if not response or not response.strip():
                logger.error(f"❌ LLM returned empty response!")
                logger.error(f"❌ System prompt was: {system_prompt[:500]}")
                logger.error(f"❌ User prompt was: {user_prompt[:500]}")
                raise Exception("LLM returned empty response")
            
            logger.info(f"✅ Sub-Brain generated response for message {message_id}")
            logger.info(f"✅ Response length: {len(response)} characters")
            return response
            
        except Exception as e:
            logger.error(f"❌ Error in Sub-Brain response generation: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            raise Exception(f"Sub-Brain processing failed: {str(e)}")
    
    @staticmethod
    def _is_query_related_to_text(query: str, selected_text: str) -> bool:
        """
        Determine if user's query is related to the selected text.
        Uses simple heuristics - can be enhanced with embeddings.
        
        Args:
            query: User's question
            selected_text: The selected text snippet
            
        Returns:
            True if query seems related to the text, False otherwise
        """
        # Normalize both strings
        query_lower = query.lower()
        text_lower = selected_text.lower()
        
        # Keywords indicating user wants explanation of the text
        explanation_keywords = [
            "explain", "what does", "what is", "what's", "clarify", "mean",
            "understand", "how", "why", "this", "it", "that", "tell me about"
        ]
        
        # Check if query contains explanation keywords
        has_explanation_keyword = any(keyword in query_lower for keyword in explanation_keywords)
        
        # Check if query references words from the selected text
        # Extract significant words (>3 chars) from selected text
        text_words = [w.strip('.,!?;:') for w in text_lower.split() if len(w) > 3]
        query_words = [w.strip('.,!?;:') for w in query_lower.split() if len(w) > 3]
        
        # Calculate overlap
        if text_words and query_words:
            common_words = set(text_words) & set(query_words)
            overlap_ratio = len(common_words) / max(len(text_words), len(query_words))
        else:
            overlap_ratio = 0
        
        # Query is related if:
        # 1. Has explanation keywords, OR
        # 2. Has significant word overlap with selected text (>20%)
        is_related = has_explanation_keyword or overlap_ratio > 0.2
        
        logger.debug(f"Query relatedness check: {is_related} (overlap: {overlap_ratio:.2f})")
        return is_related
    
    @staticmethod
    async def generate_metadata_for_main_agent(
        mini_agent_history: List[Dict[str, Any]],
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Generate learning metadata for Main Agent based on Mini Agent interactions.
        
        CRITICAL: This returns METADATA only, never messages.
        This metadata helps Main Agent learn user preferences without contaminating conversations.
        
        Args:
            mini_agent_history: Complete Mini Agent conversation history
            user_id: User ID for personalization
            
        Returns:
            Metadata dict with insights (NOT conversation messages)
        """
        try:
            if not mini_agent_history or len(mini_agent_history) < 2:
                return None
            
            # Analyze patterns in Mini Agent usage
            metadata = {
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat(),
                "insights": {
                    "confusion_points": [],
                    "preferences": {},
                    "understanding_level": "intermediate"
                }
            }
            
            # Count how many times user asked for clarification
            clarification_count = sum(
                1 for msg in mini_agent_history 
                if msg.get('role') == 'user' and any(
                    word in msg.get('content', '').lower() 
                    for word in ['explain', 'what', 'how', 'why', 'clarify']
                )
            )
            
            # If user asks many clarifications, they prefer simpler explanations
            if clarification_count > 3:
                metadata["insights"]["preferences"]["explanation_style"] = "simple"
                metadata["insights"]["understanding_level"] = "beginner"
            
            # Check if user prefers examples
            example_requests = sum(
                1 for msg in mini_agent_history
                if msg.get('role') == 'user' and any(
                    word in msg.get('content', '').lower()
                    for word in ['example', 'show me', 'demonstrate']
                )
            )
            
            if example_requests > 0:
                metadata["insights"]["preferences"]["likes_examples"] = True
            
            # Identify confusion points (topics user repeatedly asks about)
            # This helps Main Agent know what areas need more clarity
            user_questions = [
                msg.get('content', '')[:50]  # First 50 chars of each question
                for msg in mini_agent_history 
                if msg.get('role') == 'user'
            ]
            
            if len(user_questions) > 1:
                metadata["insights"]["confusion_points"] = user_questions[:3]  # Top 3
            
            logger.info(f"✅ Generated learning metadata for Main Agent (user: {user_id})")
            return metadata
            
        except Exception as e:
            logger.error(f"❌ Error generating metadata: {e}")
            return None


# Singleton instance
mini_agent_service = MiniAgentService()
