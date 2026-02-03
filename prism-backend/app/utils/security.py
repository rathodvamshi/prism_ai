"""
Security Middleware and Validation System
Implements comprehensive security measures for the application
"""

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import time
import logging
from typing import Dict, Set
import re
import ipaddress
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

def get_client_ip(request: Request) -> str:
    """Get client IP address from request"""
    # Try X-Forwarded-For first (if behind proxy)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    
    # Try X-Real-IP
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fall back to direct client
    if hasattr(request, "client") and request.client:
        return request.client.host
    
    return "unknown"

class SecurityMiddleware(BaseHTTPMiddleware):
    """
    Comprehensive security middleware for request validation and protection
    """
    
    def __init__(self, app, max_request_size: int = 10 * 1024 * 1024):  # 10MB default
        super().__init__(app)
        self.max_request_size = max_request_size
        self.blocked_ips: Set[str] = set()
        # Patterns kept for reference or specific route usage, not global middleware scan
        self.suspicious_patterns = [
            r'<script.*?>.*?</script>', 
            r'javascript:',              
            r'on\w+\s*=',               
            r'union\s+select',          
            r'drop\s+table',            
            r'delete\s+from',           
            r'\.\./.*\.\.',             
            r'file://',                 
            r'data:',                   
        ]
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.suspicious_patterns]
        
        # 🟢 WHITELIST: Safe internal routes
        self.whitelisted_prefixes = [
            "/api/streaming/",
            "/api/finalize",
            "/health",
            "/auth/me",
            "/docs",
            "/openapi.json"
        ]

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Initialize security state
        request.state.security_flag = False
        request.state.threat_detected = None
        
        try:
            # Check IP blocking (STRICT BLOCKING for blacklist)
            client_ip = get_client_ip(request)
            if client_ip in self.blocked_ips:
                logger.warning(f"🚫 Blocked request from blacklisted IP: {client_ip}")
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": "Access denied"}
                )
            
            # 🔍 WHITELIST CHECK
            is_whitelisted = any(request.url.path.startswith(prefix) for prefix in self.whitelisted_prefixes)
            
            # ⚠️ SMART SECURITY CHANGE:
            # We REMOVED body scanning from Middleware to preventing Stream Consumption errors.
            # Security is now "Observational" in middleware (Headers/IP) 
            # and "Specific" in route handlers (InputValidator).
            
            # Security headers validation (Passive Log -> Flag)
            self._validate_security_headers(request)
            
            # Process request (ALWAYS ALLOW valid traffic)
            response = await call_next(request)
            
            # Add security headers to response
            self._add_security_headers(response)
            
            # Log request timing (optional)
            # process_time = time.time() - start_time
            # logger.info(f"Request processed: {request.method} {request.url.path} - {process_time:.3f}s")
            
            return response

        except Exception as e:
            # 🛡️ FAIL SAFE: Middleware should never crash the app
            logger.error(f"Security middleware error: {e}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={
                    "error": "INTERNAL_SECURITY_ERROR",
                    "message": "An unexpected security check error occurred."
                }
            )
    
    def _contains_malicious_content(self, content: str) -> bool:
        """Check if content contains malicious patterns"""
        for pattern in self.compiled_patterns:
            if pattern.search(content):
                return True
        return False
    
    def _validate_security_headers(self, request: Request):
        """Validate security-related headers"""
        # Check User-Agent
        user_agent = request.headers.get("user-agent", "")
        if not user_agent or len(user_agent) > 1000:
            logger.warning(f"Suspicious User-Agent from {get_client_ip(request)}")
        
        # Check for common attack headers
        dangerous_headers = ["x-forwarded-for", "x-real-ip"]
        for header in dangerous_headers:
            value = request.headers.get(header, "")
            if value and not self._is_valid_ip(value):
                logger.warning(f"Suspicious {header} header: {value}")
    
    def _is_valid_ip(self, ip_string: str) -> bool:
        """Validate IP address format"""
        try:
            ipaddress.ip_address(ip_string.split(',')[0].strip())
            return True
        except ValueError:
            return False
    
    def _add_security_headers(self, response):
        """Add security headers to response"""
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    
    def block_ip(self, ip: str):
        """Block an IP address"""
        self.blocked_ips.add(ip)
        logger.info(f"IP blocked: {ip}")
    
    def unblock_ip(self, ip: str):
        """Unblock an IP address"""
        self.blocked_ips.discard(ip)
        logger.info(f"IP unblocked: {ip}")

class FormInputValidator:
    """
    Comprehensive input validation system for Forms and Auth
    (Email, Password, Sanitization)
    """
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format with enhanced security"""
        if not email or len(email) > 254:
            return False
        
        # Basic email regex (RFC 5322 compliant)
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return False
        
        # Additional security checks
        if '..' in email or email.startswith('.') or email.endswith('.'):
            return False
        
        return True
    
    @staticmethod
    def validate_password_strength(password: str) -> tuple[bool, list[str]]:
        """
        Validate password strength with detailed feedback
        Returns (is_valid, list_of_issues)
        """
        issues = []
        
        if len(password) < 8:
            issues.append("Password must be at least 8 characters long")
        
        if len(password) > 128:
            issues.append("Password must not exceed 128 characters")
        
        if not re.search(r'[A-Z]', password):
            issues.append("Password must contain at least one uppercase letter")
        
        if not re.search(r'[a-z]', password):
            issues.append("Password must contain at least one lowercase letter")
        
        if not re.search(r'\d', password):
            issues.append("Password must contain at least one digit")
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            issues.append("Password must contain at least one special character")
        
        # Check for common weak patterns
        weak_patterns = [
            r'123456',
            r'password',
            r'qwerty',
            r'abc123',
            r'admin',
        ]
        
        for pattern in weak_patterns:
            if re.search(pattern, password.lower()):
                issues.append("Password contains common weak patterns")
                break
        
        return len(issues) == 0, issues
    
    @staticmethod
    def sanitize_text_input(text: str, max_length: int = 1000, allow_html: bool = False) -> str:
        """
        Sanitize text input to prevent injection attacks
        """
        if not text:
            return ""
        
        # Trim and limit length
        text = str(text).strip()[:max_length]
        
        if not allow_html:
            # Remove HTML tags and dangerous characters
            text = re.sub(r'<[^>]+>', '', text)
            text = re.sub(r'[<>"\']', '', text)
        
        # Remove control characters
        text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\r\t')
        
        return text
    
    @staticmethod
    def validate_user_id(user_id: str) -> bool:
        """Validate MongoDB ObjectId format"""
        if not user_id or len(user_id) != 24:
            return False
        
        try:
            int(user_id, 16)  # Check if it's a valid hex string
            return True
        except ValueError:
            return False
    
    @staticmethod
    def validate_json_size(data: dict, max_size: int = 1024 * 1024) -> bool:
        """Validate JSON data size"""
        import json
        try:
            json_str = json.dumps(data)
            return len(json_str.encode('utf-8')) <= max_size
        except (TypeError, ValueError):
            return False

class AuthenticationSecurity:
    """
    Enhanced authentication security measures
    """
    
    def __init__(self):
        self.failed_attempts: Dict[str, Dict] = {}
        self.lockout_duration = timedelta(minutes=15)
        self.max_attempts = 5
    
    def record_failed_attempt(self, identifier: str) -> bool:
        """
        Record failed login attempt and return if account should be locked
        """
        now = datetime.now()
        
        if identifier not in self.failed_attempts:
            self.failed_attempts[identifier] = {
                'count': 0,
                'first_attempt': now,
                'last_attempt': now
            }
        
        attempts = self.failed_attempts[identifier]
        
        # Reset if lockout period has passed
        if now - attempts['last_attempt'] > self.lockout_duration:
            attempts['count'] = 0
            attempts['first_attempt'] = now
        
        attempts['count'] += 1
        attempts['last_attempt'] = now
        
        logger.warning(f"Failed login attempt {attempts['count']} for {identifier}")
        
        return attempts['count'] >= self.max_attempts
    
    def is_locked_out(self, identifier: str) -> tuple[bool, int]:
        """
        Check if account is locked out and return remaining time
        """
        if identifier not in self.failed_attempts:
            return False, 0
        
        attempts = self.failed_attempts[identifier]
        
        if attempts['count'] < self.max_attempts:
            return False, 0
        
        time_since_last = datetime.now() - attempts['last_attempt']
        if time_since_last > self.lockout_duration:
            # Lockout period has passed
            del self.failed_attempts[identifier]
            return False, 0
        
        remaining_seconds = int((self.lockout_duration - time_since_last).total_seconds())
        return True, remaining_seconds
    
    def reset_attempts(self, identifier: str):
        """Reset failed attempts for successful login"""
        if identifier in self.failed_attempts:
            del self.failed_attempts[identifier]
    
    def validate_jwt_token(self, token: str) -> bool:
        """Enhanced JWT token validation"""
        if not token:
            return False
        
        # Basic format check
        parts = token.split('.')
        if len(parts) != 3:
            return False
        
        # Check for suspicious patterns
        if any(char in token for char in ['<', '>', '"', "'"]):
            logger.warning("Suspicious JWT token detected")
            return False
        
        return True

# Global instances
security_middleware = SecurityMiddleware
form_input_validator = FormInputValidator()
auth_security = AuthenticationSecurity()

# Simple rate limiting (can be enhanced later with Redis)
class SimpleRateLimiter:
    def __init__(self):
        self.requests = {}
        
    def is_allowed(self, key: str, limit: int, window: int = 60) -> bool:
        """Simple in-memory rate limiting"""
        now = time.time()
        
        if key not in self.requests:
            self.requests[key] = []
            
        # Clean old requests
        self.requests[key] = [req_time for req_time in self.requests[key] 
                            if now - req_time < window]
        
        # Check if limit exceeded
        if len(self.requests[key]) >= limit:
            return False
            
        # Add current request
        self.requests[key].append(now)
        return True

simple_rate_limiter = SimpleRateLimiter()

# Export main components
__all__ = [
    'SecurityMiddleware',
    'FormInputValidator', 
    'AuthenticationSecurity',
    'security_middleware',
    'form_input_validator',
    'auth_security',
    'simple_rate_limiter',
    'get_client_ip'
]