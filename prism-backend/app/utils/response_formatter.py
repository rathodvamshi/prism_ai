"""
Response Formatter Utility
==========================

Minimal, semantic-only emoji usage for clean, professional responses.
Emojis are anchors, not decoration - used only with semantic labels.
"""

import re
from typing import List, Dict, Any, Optional


class ResponseFormatter:
    """
    Formats AI responses with controlled, semantic emoji usage.
    Only uses emojis for semantic labels: ✅ ⚠️ 🔑 📌 🚀 ❌
    """
    
    # Allowed emoji mapping for semantic labels only
    ALLOWED_EMOJIS = {
        "best_practice": "✅",
        "warning": "⚠️",
        "key_point": "🔑",
        "note": "📌",
        "performance": "🚀",
        "mistake": "❌",
    }
    
    # Forbidden emojis - these should never appear in responses
    FORBIDDEN_EMOJIS = ["😂", "😭", "🔥", "💀", "🤣", "😜", "🤪", "😍", "🙃"]
    
    @staticmethod
    def remove_forbidden_emojis(text: str) -> str:
        """Remove forbidden emojis from text"""
        for emoji in ResponseFormatter.FORBIDDEN_EMOJIS:
            text = text.replace(emoji, "")
        return text
    
    @staticmethod
    def enhance_response(
        response: str,
        user_name: Optional[str] = None,
        context: Optional[List[str]] = None,
        add_emojis: bool = False,  # Disabled by default - emojis should come from AI, not auto-added
        add_formatting: bool = True
    ) -> str:
        """
        Clean and format AI response.
        Removes forbidden emojis and applies minimal formatting.
        
        Args:
            response: Original AI response
            user_name: User's name for personalization
            context: Not used (kept for compatibility)
            add_emojis: Not used - emojis should come from AI responses
            add_formatting: Whether to add markdown formatting
        
        Returns:
            Cleaned and formatted response
        """
        if not response:
            return response
        
        enhanced = response
        
        # Remove forbidden emojis
        enhanced = ResponseFormatter.remove_forbidden_emojis(enhanced)
        
        # Personalize with user name
        if user_name and add_formatting:
            # Replace generic references with user name
            enhanced = enhanced.replace("the user", user_name)
            enhanced = enhanced.replace("you", user_name)
        
        # Add formatting for lists (keep this - it's useful)
        if add_formatting:
            enhanced = ResponseFormatter._format_lists(enhanced)
            enhanced = ResponseFormatter._format_emphasis(enhanced)
        
        return enhanced
    
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
    def format_task_response(task_description: str, due_date: Optional[str] = None) -> str:
        """Format task-related response with semantic emoji"""
        response = f"✅ **Task Created:** {task_description}"
        if due_date:
            response += f"\n📌 **Due:** {due_date}"
        response += "\nI'll remind you when it's time!"
        return response
    
    @staticmethod
    def format_memory_response(memory_type: str, content: str) -> str:
        """Format memory-related response with minimal emoji"""
        return f"✅ **Got it!** I've saved that you {content.lower()}. I'll remember this for future conversations."
    
    @staticmethod
    def format_error_response(error_message: str, friendly: bool = True) -> str:
        """Format error messages with semantic emoji"""
        if friendly:
            return f"⚠️ **Oops!** {error_message}\n\nLet me try a different approach..."
        return f"❌ **Error:** {error_message}"


# Global instance
response_formatter = ResponseFormatter()
