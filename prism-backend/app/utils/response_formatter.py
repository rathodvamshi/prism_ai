"""
🎨 Response Formatter Utility
=============================

Enhances AI responses with emojis, icons, and visual formatting.
Makes responses more engaging and user-friendly.
"""

import re
from typing import List, Dict, Any, Optional


class ResponseFormatter:
    """
    Formats AI responses with emojis, icons, and visual elements.
    """
    
    # Emoji mapping for common contexts
    EMOJI_MAP = {
        # Greetings & Positive
        "greeting": ["👋", "🌟", "✨", "😊"],
        "positive": ["✅", "🎉", "🎊", "💪", "🌟", "✨", "👍"],
        "success": ["🎉", "🚀", "✨", "🏆", "✅"],
        
        # Thinking & Ideas
        "thinking": ["🤔", "💭", "🧠"],
        "idea": ["💡", "✨", "🎯", "💡"],
        "suggestion": ["💡", "✨", "📌"],
        
        # Tasks & Actions
        "task": ["📝", "✅", "📌", "🎯"],
        "reminder": ["⏰", "📅", "🔔"],
        "completed": ["✅", "🎉", "✨"],
        
        # Information
        "info": ["📚", "📖", "💡", "ℹ️"],
        "tip": ["💡", "✨", "🎯"],
        "note": ["📝", "📌", "ℹ️"],
        
        # Support & Emotions
        "support": ["🫂", "❤️", "💙", "🤗", "💚"],
        "encouragement": ["💪", "🌟", "✨", "🚀"],
        "celebration": ["🎉", "🎊", "🎈", "✨"],
        
        # Technology
        "tech": ["💻", "🚀", "⚡", "🔧"],
        "code": ["💻", "⚡", "🔨"],
        "ai": ["🤖", "🧠", "✨"],
        
        # Fun & Hobbies
        "fun": ["🎮", "🎨", "🎵", "🎬", "🎭"],
        "music": ["🎵", "🎶", "🎧"],
        "art": ["🎨", "🖼️", "✨"],
        "sports": ["⚽", "🏀", "🎾", "🏃"],
        
        # Food & Lifestyle
        "food": ["🍕", "🍔", "🍰", "☕", "🍎"],
        "travel": ["✈️", "🌍", "🗺️", "🏖️"],
        "work": ["💼", "📊", "📈", "📋"],
        "health": ["💪", "🏃", "🧘", "❤️"],
        
        # Communication
        "question": ["❓", "🤔", "💭"],
        "answer": ["💡", "✨", "📝"],
        "thanks": ["🙏", "❤️", "✨"],
    }
    
    # Context-based emoji selection
    CONTEXT_KEYWORDS = {
        "name": ["name", "called", "i'm", "i am"],
        "location": ["live", "from", "location", "city", "country"],
        "work": ["work", "job", "occupation", "developer", "engineer"],
        "hobby": ["hobby", "hobbies", "like to", "enjoy", "love"],
        "goal": ["goal", "want", "aspire", "plan", "dream"],
        "task": ["task", "todo", "remind", "schedule"],
        "help": ["help", "assist", "support", "guide"],
        "thanks": ["thank", "thanks", "appreciate"],
    }
    
    @staticmethod
    def detect_context(message: str) -> List[str]:
        """Detect context from message to select appropriate emojis"""
        message_lower = message.lower()
        contexts = []
        
        for context, keywords in ResponseFormatter.CONTEXT_KEYWORDS.items():
            if any(keyword in message_lower for keyword in keywords):
                contexts.append(context)
        
        return contexts if contexts else ["general"]
    
    @staticmethod
    def get_emoji_for_context(context: str) -> str:
        """Get appropriate emoji for a context"""
        emoji_list = ResponseFormatter.EMOJI_MAP.get(context, ["✨"])
        import random
        return random.choice(emoji_list)
    
    @staticmethod
    def enhance_response(
        response: str,
        user_name: Optional[str] = None,
        context: Optional[List[str]] = None,
        add_emojis: bool = True,
        add_formatting: bool = True
    ) -> str:
        """
        Enhance AI response with emojis and formatting.
        
        Args:
            response: Original AI response
            user_name: User's name for personalization
            context: List of context keywords
            add_emojis: Whether to add emojis
            add_formatting: Whether to add markdown formatting
        
        Returns:
            Enhanced response with emojis and formatting
        """
        if not response:
            return response
        
        enhanced = response
        
        # Add greeting emoji if response starts with greeting
        if add_emojis:
            if any(word in enhanced.lower()[:20] for word in ["hi", "hello", "hey", "greetings"]):
                emoji = ResponseFormatter.get_emoji_for_context("greeting")
                if not enhanced.startswith(emoji):
                    enhanced = f"{emoji} {enhanced}"
        
        # Add context-appropriate emojis
        if add_emojis and context:
            for ctx in context:
                emoji = ResponseFormatter.get_emoji_for_context(ctx)
                # Add emoji at strategic points (beginning of sentences, after periods)
                enhanced = ResponseFormatter._add_emojis_strategically(enhanced, emoji, ctx)
        
        # Personalize with user name
        if user_name and add_formatting:
            # Replace generic references with user name
            enhanced = enhanced.replace("the user", user_name)
            enhanced = enhanced.replace("you", user_name)
        
        # Add formatting for lists
        if add_formatting:
            enhanced = ResponseFormatter._format_lists(enhanced)
            enhanced = ResponseFormatter._format_emphasis(enhanced)
        
        return enhanced
    
    @staticmethod
    def _add_emojis_strategically(text: str, emoji: str, context: str) -> str:
        """Add emojis at strategic points in the text"""
        # Don't over-emoji - check if already has emojis
        if any(char in text for char in ["👋", "🌟", "✨", "✅", "🎉", "💡"]):
            return text
        
        # Add emoji at the beginning if it's a positive/success message
        if context in ["success", "positive", "greeting"]:
            if not text.startswith(emoji):
                text = f"{emoji} {text}"
        
        return text
    
    @staticmethod
    def _format_lists(text: str) -> str:
        """Format lists with bullet points and emojis"""
        # Convert numbered lists to bullet points with emojis
        lines = text.split('\n')
        formatted_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                formatted_lines.append(line)
                continue
            
            # Check if it's a list item
            if re.match(r'^\d+[\.\)]\s+', line):
                # Convert to bullet with emoji
                content = re.sub(r'^\d+[\.\)]\s+', '', line)
                formatted_lines.append(f"• {content}")
            elif line.startswith('- ') or line.startswith('* '):
                # Already a bullet, add emoji if appropriate
                content = line[2:].strip()
                formatted_lines.append(f"• {content}")
            else:
                formatted_lines.append(line)
        
        return '\n'.join(formatted_lines)
    
    @staticmethod
    def _format_emphasis(text: str) -> str:
        """Add markdown emphasis to important points"""
        # Bold important phrases (already done by LLM usually)
        # Just ensure consistency
        return text
    
    @staticmethod
    def add_visual_break(text: str, emoji: str = "✨") -> str:
        """Add visual break with emoji"""
        return f"{emoji}\n\n{text}\n\n{emoji}"
    
    @staticmethod
    def format_task_response(task_description: str, due_date: Optional[str] = None) -> str:
        """Format task-related response with appropriate emojis"""
        response = f"📝 **Task Created:** {task_description}"
        if due_date:
            response += f"\n⏰ **Due:** {due_date}"
        response += "\n✅ I'll remind you when it's time!"
        return response
    
    @staticmethod
    def format_memory_response(memory_type: str, content: str) -> str:
        """Format memory-related response"""
        emoji_map = {
            "name": "👤",
            "location": "📍",
            "interest": "🎯",
            "hobby": "🎨",
            "preference": "❤️",
            "goal": "🎯",
            "skill": "💪",
        }
        
        emoji = emoji_map.get(memory_type, "💡")
        return f"{emoji} **Got it!** I've saved that you {content.lower()}. I'll remember this for future conversations! ✨"
    
    @staticmethod
    def format_error_response(error_message: str, friendly: bool = True) -> str:
        """Format error messages in a friendly way"""
        if friendly:
            return f"😅 Oops! {error_message}\n\nLet me try a different approach... 💡"
        return f"❌ Error: {error_message}"


# Global instance
response_formatter = ResponseFormatter()
