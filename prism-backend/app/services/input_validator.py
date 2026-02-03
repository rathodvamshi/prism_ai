"""
Input Validation Service
Client and server-side input validation for AI prompts.
"""

from typing import List, Optional
from pydantic import BaseModel, validator
from fastapi import HTTPException
import re


class InputValidation(BaseModel):
    """Input validation result"""
    is_valid: bool
    line_count: int
    size_bytes: int
    size_mb: float
    errors: List[str] = []
    warnings: List[str] = []


class InputLimits(BaseModel):
    """Configurable input limits - optimized for small project"""
    max_lines: int = 3000
    max_size_bytes: int = 300 * 1024  # 300 KB
    warn_lines_threshold: int = 2400  # 80% of max
    warn_size_threshold: int = 240 * 1024  # 80% of max


class InputValidator:
    """
    Validates user input against size and line count limits.
    Prevents memory pressure and UI freezes.
    """
    
    def __init__(self, limits: Optional[InputLimits] = None):
        self.limits = limits or InputLimits()
    
    def validate(self, content: str) -> InputValidation:
        """
        Validate input content.
        Returns validation result with errors and warnings.
        """
        errors = []
        warnings = []
        
        # Count lines
        lines = content.split('\n')
        line_count = len(lines)
        
        # Calculate size
        size_bytes = len(content.encode('utf-8'))
        size_mb = size_bytes / (1024 * 1024)
        
        # Check line count limit
        if line_count > self.limits.max_lines:
            errors.append(
                f"Input too large. Please split your message. "
                f"(Current: {line_count:,} lines, Maximum: {self.limits.max_lines:,} lines)"
            )
        elif line_count > self.limits.warn_lines_threshold:
            warnings.append(
                f"Approaching line limit ({line_count:,} / {self.limits.max_lines:,} lines)"
            )
        
        # Check size limit
        if size_bytes > self.limits.max_size_bytes:
            errors.append(
                f"Input too large. Please split your message. "
                f"(Current: {size_mb:.2f} MB, Maximum: {self.limits.max_size_bytes / (1024 * 1024):.2f} MB)"
            )
        elif size_bytes > self.limits.warn_size_threshold:
            warnings.append(
                f"Approaching size limit ({size_mb:.2f} / {self.limits.max_size_bytes / (1024 * 1024):.2f} MB)"
            )
        
        # Check for extremely long lines (potential performance issue)
        max_line_length = max(len(line) for line in lines) if lines else 0
        if max_line_length > 10000:
            warnings.append(
                f"Input contains very long line ({max_line_length:,} characters). "
                "Consider breaking it up for better performance."
            )
        
        # Check for null bytes (can cause issues)
        if '\x00' in content:
            errors.append("Input contains null bytes which are not allowed")
        
        is_valid = len(errors) == 0
        
        return InputValidation(
            is_valid=is_valid,
            line_count=line_count,
            size_bytes=size_bytes,
            size_mb=round(size_mb, 2),
            errors=errors,
            warnings=warnings
        )
    
    def validate_or_raise(self, content: str) -> InputValidation:
        """
        Validate input and raise HTTPException if invalid.
        Use this in API endpoints for automatic error responses.
        """
        validation = self.validate(content)
        
        if not validation.is_valid:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Input validation failed",
                    "errors": validation.errors,
                    "line_count": validation.line_count,
                    "size_mb": validation.size_mb
                }
            )
        
        return validation


# Pre-configured validators for different use cases
default_validator = InputValidator()

# Stricter validator for free tier users
strict_validator = InputValidator(
    InputLimits(
        max_lines=10000,
        max_size_bytes=500 * 1024,  # 500KB
        warn_lines_threshold=8000,
        warn_size_threshold=400 * 1024
    )
)

# More lenient for enterprise users
enterprise_validator = InputValidator(
    InputLimits(
        max_lines=100000,
        max_size_bytes=10 * 1024 * 1024,  # 10MB
        warn_lines_threshold=80000,
        warn_size_threshold=8 * 1024 * 1024
    )
)


def sanitize_input(content: str) -> str:
    """
    Sanitize user input by removing potentially problematic characters.
    Use cautiously as it modifies user input.
    """
    # Remove null bytes
    content = content.replace('\x00', '')
    
    # Normalize line endings
    content = content.replace('\r\n', '\n').replace('\r', '\n')
    
    # Remove excessive whitespace at end of lines
    lines = content.split('\n')
    lines = [line.rstrip() for line in lines]
    content = '\n'.join(lines)
    
    return content


def truncate_input(content: str, limits: Optional[InputLimits] = None) -> str:
    """
    Truncate input to fit within limits.
    Use as fallback when validation fails.
    """
    limits = limits or InputLimits()
    
    # Truncate by lines
    lines = content.split('\n')
    if len(lines) > limits.max_lines:
        lines = lines[:limits.max_lines]
        content = '\n'.join(lines)
    
    # Truncate by size
    while len(content.encode('utf-8')) > limits.max_size_bytes:
        lines = lines[:-1]  # Remove last line
        content = '\n'.join(lines)
        
        if not lines:  # Safety check
            break
    
    return content
