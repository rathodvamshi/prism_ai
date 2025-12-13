#!/usr/bin/env python3
"""
Security Key Generator for PRISM AI Backend
Generates secure keys for JWT and encryption purposes.
"""

import secrets
import string
import hashlib
from datetime import datetime

def generate_jwt_secret(length: int = 64) -> str:
    """Generate a secure JWT secret key"""
    return secrets.token_urlsafe(length)

def generate_encryption_key() -> str:
    """Generate a 32-character encryption key (required for AES-256)"""
    return secrets.token_hex(16)  # 16 bytes = 32 hex characters

def generate_api_key(length: int = 32) -> str:
    """Generate a secure API key"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def generate_password(length: int = 20) -> str:
    """Generate a secure password"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def main():
    """Generate all required security keys"""
    print("🔐 PRISM AI Security Key Generator")
    print("=" * 50)
    print()
    
    # Generate keys
    jwt_secret = generate_jwt_secret()
    encryption_key = generate_encryption_key()
    api_key = generate_api_key()
    secure_password = generate_password()
    
    # Display results
    print("📋 Copy these values to your .env.local file:")
    print("-" * 50)
    print(f"JWT_SECRET={jwt_secret}")
    print(f"ENCRYPTION_KEY={encryption_key}")
    print()
    
    print("🔑 Additional Security Values:")
    print("-" * 30)
    print(f"Sample API Key: {api_key}")
    print(f"Secure Password: {secure_password}")
    print()
    
    print("⚠️  SECURITY REMINDERS:")
    print("- Never commit these keys to version control")
    print("- Store them securely in your .env.local file")
    print("- Generate new keys for each environment (dev/staging/prod)")
    print("- Rotate these keys regularly (every 3-6 months)")
    print()
    
    # Key strength info
    jwt_entropy = len(jwt_secret) * 6  # Base64 encoding provides ~6 bits per character
    print(f"📊 Security Strength:")
    print(f"- JWT Secret: {len(jwt_secret)} chars (~{jwt_entropy} bits entropy)")
    print(f"- Encryption Key: 32 chars (256 bits - AES-256 compatible)")
    print()
    
    print(f"Generated on: {datetime.now().isoformat()}")

if __name__ == "__main__":
    main()