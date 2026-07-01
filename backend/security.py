"""
Security middleware and utilities for FastAPI application.
Provides input validation, rate limiting, and security headers.
"""

from typing import Optional
from urllib.parse import urlparse
import re
from functools import wraps
import time
from collections import defaultdict
from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimiter:
    """Simple in-memory rate limiter."""
    
    def __init__(self, requests: int = 100, period: int = 60):
        self.requests = requests
        self.period = period
        self.clients = defaultdict(list)
    
    def is_allowed(self, client_ip: str) -> bool:
        """Check if client is within rate limit."""
        now = time.time()
        cutoff = now - self.period
        
        # Clean old requests
        self.clients[client_ip] = [
            req_time for req_time in self.clients[client_ip]
            if req_time > cutoff
        ]
        
        if len(self.clients[client_ip]) >= self.requests:
            return False
        
        self.clients[client_ip].append(now)
        return True


class SecurityMiddleware(BaseHTTPMiddleware):
    """Middleware for security headers and rate limiting."""
    
    def __init__(self, app, rate_limiter: Optional[RateLimiter] = None):
        super().__init__(app)
        self.rate_limiter = rate_limiter or RateLimiter()
    
    async def dispatch(self, request: Request, call_next):
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        
        # Check rate limit
        if not self.rate_limiter.is_allowed(client_ip):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        
        # Process request
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        
        return response


class InputValidator:
    """Input validation utilities."""
    
    @staticmethod
    def validate_url(url: str, allowed_schemes: list = None) -> bool:
        """Validate URL format and scheme."""
        if allowed_schemes is None:
            allowed_schemes = ["http", "https"]
        
        try:
            parsed = urlparse(url)
            if parsed.scheme not in allowed_schemes:
                return False
            if not parsed.netloc:
                return False
            return True
        except Exception:
            return False
    
    @staticmethod
    def validate_command(command: str) -> bool:
        """Validate command string (prevent injection)."""
        # Whitelist safe characters
        safe_pattern = r'^[a-zA-Z0-9\s\-_/\.]+$'
        return bool(re.match(safe_pattern, command))
    
    @staticmethod
    def validate_identifier(identifier: str, max_length: int = 255) -> bool:
        """Validate identifier string (alphanumeric + underscore)."""
        if not identifier or len(identifier) > max_length:
            return False
        pattern = r'^[a-zA-Z0-9_\-]+$'
        return bool(re.match(pattern, identifier))
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Remove potentially dangerous characters from filename."""
        # Remove path traversal attempts
        filename = filename.replace('..', '').replace('/', '').replace('\\', '')
        # Keep only safe characters
        safe_chars = re.sub(r'[^a-zA-Z0-9._\-]', '_', filename)
        return safe_chars[:255]  # Limit length


def require_validation(*validators):
    """Decorator to require input validation on endpoints."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Run validators
            for validator in validators:
                if not validator(*args, **kwargs):
                    raise HTTPException(status_code=400, detail="Invalid input")
            return await func(*args, **kwargs)
        return wrapper
    return decorator
