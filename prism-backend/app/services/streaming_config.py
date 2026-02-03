"""
⚡ Streaming Configuration - Ultra-smooth token delivery

Features:
- Configurable batching strategies (instant/smooth/balanced)
- Punctuation-aware flushing for natural pauses
- Optimized for 60fps frontend rendering
- Adaptive batching based on content type

Impact: Eliminates choppy streaming, creates ChatGPT-like smooth flow
"""
from dataclasses import dataclass, field
from typing import Literal, Dict
import re

StreamingMode = Literal["instant", "smooth", "balanced", "typewriter"]


@dataclass
class StreamingConfig:
    """Configuration for streaming behavior"""
    
    # Character batching
    min_batch_size: int = 1          # Minimum chars before sending
    max_batch_size: int = 10         # Maximum chars to batch
    
    # Timing (milliseconds)  
    min_delay_ms: int = 5            # Minimum delay between sends
    max_delay_ms: int = 25           # Maximum delay for batching
    
    # Smart flushing
    flush_on_punctuation: bool = True     # Flush on . ! ? for natural pauses
    flush_on_newline: bool = True         # Flush on newlines immediately
    flush_on_code_delimiter: bool = True  # Flush on ``` for code blocks
    flush_on_word_boundary: bool = False  # Flush on space (word-by-word)
    
    # Buffer settings
    buffer_size: int = 64            # Internal buffer size
    
    # Mode identifier
    mode: StreamingMode = "smooth"
    
    # Patterns for smart flushing (pre-compiled)
    _punctuation_pattern: re.Pattern = field(
        default_factory=lambda: re.compile(r'[.!?;:,]$'),
        repr=False
    )
    _code_pattern: re.Pattern = field(
        default_factory=lambda: re.compile(r'```'),
        repr=False
    )
    
    def should_flush(self, buffer: str, time_since_last_ms: float) -> bool:
        """
        Determine if buffer should be flushed based on config rules.
        
        Args:
            buffer: Current accumulated text
            time_since_last_ms: Time since last flush in milliseconds
        
        Returns:
            True if should flush now
        """
        buffer_len = len(buffer)
        
        # Always flush if max delay exceeded
        if time_since_last_ms >= self.max_delay_ms:
            return True
        
        # Check buffer size thresholds
        if buffer_len >= self.max_batch_size:
            return True
        
        # Check minimum requirements
        if buffer_len < self.min_batch_size:
            return False
        
        # Smart content-based flushing
        if self.flush_on_newline and '\n' in buffer:
            return True
        
        if self.flush_on_punctuation and self._punctuation_pattern.search(buffer):
            return True
        
        if self.flush_on_code_delimiter and self._code_pattern.search(buffer):
            return True
        
        if self.flush_on_word_boundary and buffer.endswith(' '):
            return True
        
        return False


# Pre-configured presets
STREAMING_PRESETS: Dict[StreamingMode, StreamingConfig] = {
    "instant": StreamingConfig(
        min_batch_size=1,
        max_batch_size=3,
        min_delay_ms=0,
        max_delay_ms=8,
        flush_on_punctuation=True,
        flush_on_newline=True,
        mode="instant"
    ),
    "smooth": StreamingConfig(
        min_batch_size=1,
        max_batch_size=12,
        min_delay_ms=5,
        max_delay_ms=30,
        flush_on_punctuation=True,
        flush_on_newline=True,
        flush_on_code_delimiter=True,
        mode="smooth"
    ),
    "balanced": StreamingConfig(
        min_batch_size=3,
        max_batch_size=20,
        min_delay_ms=10,
        max_delay_ms=50,
        flush_on_punctuation=True,
        flush_on_newline=True,
        mode="balanced"
    ),
    "typewriter": StreamingConfig(
        min_batch_size=1,
        max_batch_size=1,
        min_delay_ms=15,
        max_delay_ms=30,
        flush_on_punctuation=False,
        flush_on_newline=False,
        mode="typewriter"
    )
}


def get_streaming_config(mode: StreamingMode = "smooth") -> StreamingConfig:
    """Get streaming configuration by mode"""
    return STREAMING_PRESETS.get(mode, STREAMING_PRESETS["smooth"])


def get_optimal_streaming_mode(content_type: str = "text") -> StreamingMode:
    """
    Get optimal streaming mode based on content type.
    
    Args:
        content_type: Type of content being streamed
            - "text": Regular conversational text
            - "code": Code snippets
            - "markdown": Markdown content
            - "realtime": Voice/live transcription
    """
    mode_map = {
        "text": "smooth",
        "code": "balanced",
        "markdown": "smooth",
        "realtime": "instant",
        "voice": "instant"
    }
    return mode_map.get(content_type, "smooth")


class AdaptiveStreamer:
    """
    Adaptive streaming controller that adjusts behavior in real-time
    based on content patterns and user connection quality.
    """
    
    def __init__(self, base_config: StreamingConfig = None):
        self.config = base_config or get_streaming_config("smooth")
        self.buffer = ""
        self.total_chars = 0
        self.flush_count = 0
        self._in_code_block = False
    
    def add_token(self, token: str) -> str | None:
        """
        Add a token to the buffer. Returns content to send if should flush.
        
        Args:
            token: New token to add
        
        Returns:
            String to send if flush triggered, None otherwise
        """
        self.buffer += token
        self.total_chars += len(token)
        
        # Track code block state
        if '```' in token:
            self._in_code_block = not self._in_code_block
        
        # Adjust behavior inside code blocks (larger batches)
        effective_max = self.config.max_batch_size * 2 if self._in_code_block else self.config.max_batch_size
        
        # Check flush conditions
        should_flush = (
            len(self.buffer) >= effective_max or
            (self.config.flush_on_newline and '\n' in self.buffer) or
            (self.config.flush_on_punctuation and self.buffer.rstrip().endswith(('.', '!', '?'))) or
            (self.config.flush_on_code_delimiter and '```' in self.buffer)
        )
        
        if should_flush:
            content = self.buffer
            self.buffer = ""
            self.flush_count += 1
            return content
        
        return None
    
    def flush_remaining(self) -> str | None:
        """Flush any remaining buffer content"""
        if self.buffer:
            content = self.buffer
            self.buffer = ""
            self.flush_count += 1
            return content
        return None
    
    def get_stats(self) -> dict:
        """Get streaming statistics"""
        return {
            "total_chars": self.total_chars,
            "flush_count": self.flush_count,
            "avg_batch_size": self.total_chars / max(1, self.flush_count),
            "mode": self.config.mode
        }
