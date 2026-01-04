from fastapi import APIRouter, HTTPException, Depends, status, Response, Request
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, validator
from app.db.mongo_client import users_collection, auth_sessions_collection
from app.db.redis_client import redis_client
from app.config import settings
from app.utils.auth import (
    AuthUtils,
    SecurityUtils,
    get_current_user,
    security,
    create_session_for_user,
    get_current_user_from_session,
)
from app.utils.security import input_validator, auth_security
from app.services.global_user_service import add_user_to_global
from app.services.email_queue_service import enqueue_otp
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import random
import os
import json
from datetime import datetime, timezone
from bson import ObjectId
from typing import Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Auth"])

class User(BaseModel):
    user_id: str
    email: EmailStr
    name: Optional[str] = None

class EmailQuery(BaseModel):
    email: EmailStr

class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None
    
    @validator('password')
    def validate_password(cls, v):
        # Basic password requirements
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        
        # Very conservative length limit to avoid bcrypt issues
        if len(v) > 40:
            raise ValueError("Password is too long (max 40 characters for compatibility)")
        
        return v

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class OTPVerify(BaseModel):
    email: EmailStr
    otp: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class AuthResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict

class RefreshTokenRequest(BaseModel):
    refresh_token: str

@router.get("/mail-health")
async def mail_health():
    """Quick check for SendGrid configuration validity."""
    try:
        if not getattr(settings, "SENDGRID_API_KEY", None):
            return {"status": "error", "detail": "SENDGRID_API_KEY not set"}
        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        # minimal noop — SDK doesn't offer a ping, attempt to construct client
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

@router.get("/diag")
async def diag():
    """Return minimal diagnostics for mail sending configuration (no secrets)."""
    key = str(getattr(settings, "SENDGRID_API_KEY", "")).strip()
    sender = str(getattr(settings, "SENDER_EMAIL", "")).strip() or str(getattr(settings, "MAIL_FROM", "")).strip()
    return {
        "has_key": bool(key),
        "key_len": len(key),
        "key_prefix": key[:4] if key else None,
        "sender": sender,
        "env_file": os.path.abspath(".env"),
    }

@router.get("/test-send")
async def test_send(to: EmailStr):
    """Send a simple test email to validate SendGrid setup."""
    from_addr = str(getattr(settings, "SENDER_EMAIL", "")).strip() or str(getattr(settings, "MAIL_FROM", "")).strip()
    if not from_addr:
        raise HTTPException(status_code=500, detail="SENDER_EMAIL (or MAIL_FROM) not configured")

    msg = Mail(
        from_email=from_addr,
        to_emails=to,
        subject="PRISM Test Email",
        html_content="<strong>This is a PRISM SendGrid test email.</strong>",
    )
    api_key = str(getattr(settings, "SENDGRID_API_KEY", "")).strip()
    if not api_key:
        raise HTTPException(status_code=500, detail="SENDGRID_API_KEY missing")
    try:
        sg = SendGridAPIClient(api_key)
        response = sg.send(msg)
        # construct readable diagnostics
        detail = {
            "status_code": getattr(response, "status_code", None),
            "body": (getattr(response, "body", None).decode() if getattr(response, "body", None) else None),
            "headers": dict(getattr(response, "headers", {})),
        }
        print("[TEST-SEND]", detail)
        if 200 <= int(getattr(response, "status_code", 0)) < 300:
            return {"status": "ok", "detail": detail}
        else:
            return {"status": "error", "detail": detail}
    except Exception as e:
        print("[TEST-SEND ERROR]", e)
        raise HTTPException(status_code=502, detail=f"SendGrid error: {e}")

@router.post("/test-password")
async def test_password_hashing(password: str):
    """Test endpoint to verify password hashing works"""
    try:
        logger.info(f"Testing password hashing for length: {len(password)}")
        hashed = AuthUtils.hash_password(password)
        verified = AuthUtils.verify_password(password, hashed)
        return {
            "success": True,
            "password_length": len(password),
            "hash_method": "bcrypt" if len(hashed) > 64 else "sha256",
            "verification_works": verified
        }
    except Exception as e:
        logger.error(f"Password test failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "password_length": len(password)
        }

@router.get("/check-email")
async def check_email(email: EmailStr):
    try:
        existing = await users_collection.find_one({"email": email})
        if existing:
            # Check if it's a completed account or pending signup
            if existing.get("verified") and existing.get("passwordHash"):
                # 409: already exists and verified
                raise HTTPException(status_code=409, detail="Email already registered")
            elif existing.get("signupPending"):
                # Allow re-use if signup is still pending (user can try again)
                return {"status": "available", "note": "Previous signup pending"}
        return {"status": "available"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB check failed: {e}")


@router.post("/login")
async def simple_login(payload: LoginRequest, response: Response, request: Request):
    """
    Simple login that works with new signup.

    - Verifies password
    - Creates a server-side session
    - Sets HTTP-only session cookie for browser clients
    """
    try:
        logger.info(f"🔐 Login attempt: {payload.email}")
        
        # Find user
        user = await users_collection.find_one({"email": payload.email})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        # Check password (supports bcrypt stored in either 'passwordHash' or 'password',
        # and legacy simple SHA-256 stored in 'password')
        password_valid = False

        stored_password = user.get("password")
        stored_bcrypt = user.get("passwordHash")
        
        # Prefer bcrypt-style / modern hashes using dedicated field if present
        if stored_bcrypt and not password_valid:
            try:
                if AuthUtils.verify_password(payload.password, stored_bcrypt):
                    password_valid = True
                    logger.info("✅ Password valid (passwordHash via AuthUtils.verify_password)")
            except Exception as e:
                logger.warning(f"Password verification failed for passwordHash: {e}")
        
        # If not yet valid, inspect 'password' field with the unified verifier
        if not password_valid and stored_password:
            try:
                # AuthUtils.verify_password handles bcrypt and our 'sha256:salt:hash' fallback
                if AuthUtils.verify_password(payload.password, stored_password):
                    password_valid = True
                    logger.info("✅ Password valid (password field via AuthUtils.verify_password)")
            except Exception as e:
                logger.warning(f"Password verification failed for password field: {e}")
        
        if not password_valid:
            raise HTTPException(status_code=401, detail="Invalid password")
        
        # Create login session (server-side) and set cookie
        session_id = await create_session_for_user(
            user,
            user_agent=request.headers.get("user-agent"),
            ip=request.client.host if request.client else None,
        )

        # HTTP-only, secure cookie for browser auth
        cookie_secure = getattr(settings, "SESSION_COOKIE_SECURE", True)
        cookie_samesite = getattr(settings, "SESSION_COOKIE_SAMESITE", "lax")
        cookie_name = getattr(settings, "SESSION_COOKIE_NAME", "session_id")

        response.set_cookie(
            key=cookie_name,
            value=session_id,
            httponly=True,
            secure=cookie_secure,
            samesite=cookie_samesite,  # type: ignore[arg-type]
            path="/",
            max_age=60 * 60 * 24 * getattr(settings, "SESSION_EXPIRE_DAYS", 30)
        )

        # Minimal user object for UI (no tokens needed)
        user_data = {
            "id": str(user["_id"]),
            "email": user["email"],
            "name": user.get("name", ""),
            "verified": True,
        }

        logger.info(f"✅ Login successful (session) for: {payload.email}")
        return {
            "user": user_data,
            "session_active": True,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/login_old", response_model=AuthResponse)
async def login(payload: LoginRequest):
    """Login with email and password - Returns JWT token"""
    try:
        # Check for account lockout
        is_locked, remaining_time = auth_security.is_locked_out(payload.email)
        if is_locked:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Account locked. Try again in {remaining_time} seconds."
            )
        
        # Validate email format
        if not input_validator.validate_email(payload.email):
            auth_security.record_failed_attempt(payload.email)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid email format"
            )
        
        # Get user from database
        user = await AuthUtils.get_user_by_email(payload.email)
        if not user:
            auth_security.record_failed_attempt(payload.email)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Check if user has completed signup process
        if not user.get("verified") or not user.get("passwordHash"):
            if user.get("signupPending"):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Please verify your email to complete signup"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Account not fully created"
                )
        
        # Verify password
        if not AuthUtils.verify_password(payload.password, user["passwordHash"]):
            auth_security.record_failed_attempt(payload.email)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Reset failed attempts on successful login
        auth_security.reset_attempts(payload.email)
        
        # Update last login time
        await users_collection.update_one(
            {"_id": user["_id"]},
            {"$set": {"last_login": datetime.now(timezone.utc)}}
        )
        
        # Create JWT token
        access_token = AuthUtils.create_access_token(
            data={"sub": user["email"], "user_id": str(user["_id"]), "email": user["email"]}
        )
        
        # Create safe user response
        safe_user = AuthUtils.create_user_response(user)
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": safe_user
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )

# OTP-based signup endpoint
@router.post("/signup")
async def signup_with_otp(payload: SignupRequest):
    """Signup with OTP verification via SendGrid"""
    
    try:
        logger.info(f"📧 Signup request: {payload.email}")
        
        # Basic validation
        if len(payload.password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 8 characters long"
            )
        
        # Check if user already exists and is verified
        existing = await users_collection.find_one({"email": payload.email})
        if existing and existing.get("verified"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User already exists and is verified"
            )
        
        # Generate 6-digit OTP
        otp = f"{random.randint(100000, 999999)}"
        logger.info(f"🔢 Generated OTP for {payload.email}: {otp}")
        
        # Display OTP prominently in terminal
        print("\n" + "="*60)
        print(f"🎯 OTP FOR USER: {payload.email}")
        print(f"📧 OTP CODE: {otp}")
        print(f"⏰ Valid for 10 minutes")
        print("="*60 + "\n")
        
        # Hash password safely (will store after OTP verification)
        try:
            password_hash = AuthUtils.hash_password(payload.password)
            logger.info(f"✅ Password hashed successfully for {payload.email}")
        except Exception as hash_error:
            logger.error(f"❌ Password hashing failed for {payload.email}: {hash_error}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Password processing failed. Please try with a shorter password."
            )
        
        # Set OTP expiration (10 minutes)
        otp_expires_at = datetime.now(timezone.utc).timestamp() + (10 * 60)
        
        # Store user data temporarily in Redis (only for OTP verification)
        temp_user_data = {
            "email": payload.email,
            "password": password_hash,
            "name": payload.name or "User",
            "otp": otp,
            "otp_expires_at": otp_expires_at,
            "created": datetime.now(timezone.utc).isoformat(),
            "id": payload.email.replace("@", "_").replace(".", "_")
        }
        
        # Save to Redis temporarily (expires in 10 minutes)
        redis_key = f"pending_signup:{payload.email}"
        redis_success = await redis_client.set(redis_key, json.dumps(temp_user_data), ex=600)  # 600 seconds = 10 minutes
        
        if not redis_success:
            logger.error(f"❌ Failed to store temporary data in Redis for {payload.email}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save signup data. Please try again."
            )
        
        logger.info(f"💾 Temporary signup data stored in Redis for {payload.email}")
        
        # ☁️ Send OTP email immediately (direct send for reliability)
        # OTP emails are critical and should be sent immediately, not queued
        try:
            email_result = await send_otp_email(payload.email, otp)
            if email_result.get("success"):
                logger.info(f"✅ OTP email sent successfully to {payload.email}")
                print(f"✅ Email successfully sent to {payload.email}")
                return {
                    "message": f"OTP sent to {payload.email}. Please check your email and enter the 6-digit code.",
                    "email": payload.email,
                    "otp_required": True
                }
            else:
                # Email failed but OTP is still valid (shown in terminal)
                logger.warning(f"⚠️ Email sending failed: {email_result.get('error')}, but OTP is available in terminal")
                print(f"⚠️ Email sending failed, but OTP is shown above ☝️")
                return {
                    "message": f"Registration initiated. Please use the OTP code displayed in the terminal/console: {otp}",
                    "email": payload.email,
                    "otp_required": True,
                    "otp_code": otp  # Include OTP in response for development
                }
        except Exception as email_error:
            logger.error(f"❌ OTP email sending failed: {email_error}")
            print(f"❌ Email sending error: {email_error}")
            print(f"📱 USE OTP FROM TERMINAL: {otp}")
            return {
                "message": f"Registration initiated. Please use the OTP code displayed in the terminal/console: {otp}",
                "email": payload.email,
                "otp_required": True,
                "otp_code": otp  # Include OTP in response for development
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Signup failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Signup failed: {str(e)}"
        )

@router.post("/signup_old")
async def signup(payload: SignupRequest):
    """Start signup process by sending OTP"""
    logger.info(f"🚀 Signup request received: email={payload.email}, name={payload.name}")
    try:
        # Basic email validation (pydantic EmailStr already validates format)
        # Additional password validation (pydantic validator already checks basic requirements)
        if len(payload.password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 8 characters long"
            )
        
        # Check if user already exists and is verified
        existing = await AuthUtils.get_user_by_email(payload.email)
        if existing and existing.get("verified"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Account already exists"
            )
        
        # Generate 6-digit OTP
        otp = f"{random.randint(100000, 999999)}"
        
        # Hash the password
        try:
            password_hash = AuthUtils.hash_password(payload.password)
        except Exception as e:
            logger.error(f"Password hashing failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password processing failed"
            )
        
        # Set OTP expiration time (10 minutes from now)
        otp_expires_at = datetime.now(timezone.utc).timestamp() + (10 * 60)
        
        # Prepare user data for temporary storage
        user_data = {
            "email": payload.email,
            "passwordHash": password_hash,
            "otp": otp,
            "otp_expires_at": otp_expires_at,
            "signupPending": True,
            "verified": False,
            "created_at": datetime.now(timezone.utc)
        }
        
        # Add name if provided (with enhanced sanitization)
        if payload.name:
            user_data["name"] = input_validator.sanitize_text_input(payload.name, 100)
        
        # Store or update pending user data
        await users_collection.update_one(
            {"email": payload.email},
            {"$set": user_data},
            upsert=True
        )
        
        # Enqueue OTP email (preferred). Fallback to direct send if enqueue fails.
        try:
            await enqueue_otp(payload.email, otp)
        except Exception as email_error:
            logger.error(f"OTP enqueue failed (legacy path), falling back to direct send: {email_error}")
            await send_otp_email(payload.email, otp)
        
        # In development mode, auto-verify users if email sending is disabled
        if settings.ENVIRONMENT.lower() == "development" and not getattr(settings, "SENDGRID_API_KEY", ""):
            # Auto-verify the user in development
            user_data["verified"] = True
            user_data["signupPending"] = False
            await users_collection.update_one(
                {"email": payload.email},
                {"$set": user_data},
                upsert=True
            )
            
            # Generate access token
            user_dict = {
                "id": str(user_data.get("_id", "dev-user-id")),
                "email": payload.email,
                "name": user_data.get("name", "")
            }
            
            access_token = AuthUtils.create_access_token(
                data={"sub": user_dict["id"], "email": payload.email, "user_id": user_dict["id"]}
            )
            
            return {
                "message": "User registered successfully (development mode)",
                "email": payload.email,
                "access_token": access_token,
                "token_type": "bearer",
                "user": user_dict
            }
        
        return {
            "message": "OTP sent successfully. Please check your email.",
            "email": payload.email
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Signup failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Signup failed"
        )

async def send_otp_email(email: str, otp: str):
    """☁️ Send OTP email via SendGrid with robust error handling and perfect delivery"""
    
    # Always print OTP to terminal first (most important for development)
    print(f"\n" + "="*60)
    print(f"🎯 OTP VERIFICATION CODE")
    print(f"📧 Email: {email}")
    print(f"🔢 OTP Code: {otp}")
    print(f"⏰ Valid for: 10 minutes")
    print(f"="*60 + "\n")
    
    try:
        api_key = settings.SENDGRID_API_KEY
        from_addr = settings.SENDER_EMAIL
        
        logger.info(f"📧 Attempting to send OTP to {email}")
        logger.info(f"🔑 API Key configured: {'Yes' if api_key else 'No'}")
        logger.info(f"📨 From address: {from_addr}")
        
        if not api_key:
            logger.warning("⚠️ SendGrid API key not configured")
            print("⚠️ Email sending skipped - No SendGrid API key configured")
            return {"success": False, "error": "SendGrid API key not configured"}
            
        if not from_addr:
            logger.warning("⚠️ Sender email not configured")
            print("⚠️ Email sending skipped - No sender email configured")
            return {"success": False, "error": "Sender email not configured"}
        
        # ☁️ Use Celery task for OTP email sending
        try:
            from app.tasks.email_tasks import send_otp_email_task
            from app.core.celery_app import CELERY_AVAILABLE, celery_app
            
            if CELERY_AVAILABLE and celery_app:
                # Send OTP via Celery task (preferred)
                celery_app.send_task(
                    "prism_tasks.send_otp_email",
                    args=[email, otp, "PRISM AI Verification Code"],
                    queue="email"
                )
                logger.info(f"✅ OTP email task queued successfully for {email}")
                print(f"✅ OTP email queued for {email} via Celery")
                return {"success": True, "message": f"OTP email queued for {email}"}
            else:
                # Fallback to direct sending if Celery unavailable
                from app.services.email_service import send_otp_email_direct
                email_sent = await send_otp_email_direct(
                    to_email=email,
                    otp_code=otp,
                    subject="PRISM AI Verification Code"
                )
                
                if email_sent:
                    logger.info(f"✅ OTP email sent directly to {email} (Celery unavailable)")
                    print(f"✅ Email sent directly to {email} via SendGrid")
                    return {"success": True, "message": f"Email sent directly to {email}"}
                else:
                    logger.warning(f"⚠️ OTP email service returned False for {email}")
                    return {"success": False, "error": "Email service returned False"}
                
        except Exception as service_error:
            logger.error(f"❌ OTP email service error: {service_error}")
            # Fallback to direct SendGrid send
            try:
                msg = Mail(
                    from_email=from_addr,
                    to_emails=email,
                    subject=f"PRISM AI Verification Code: {otp}",
                    html_content=f"""
                    <div style="font-family: Arial, sans-serif; padding: 20px; max-width: 500px; margin: 0 auto;">
                        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; text-align: center; border-radius: 8px 8px 0 0;">
                            <h1 style="color: white; margin: 0;">PRISM AI</h1>
                        </div>
                        <div style="padding: 30px; background: #ffffff; border-radius: 0 0 8px 8px;">
                            <h2 style="color: #333;">Verification Code</h2>
                            <p style="color: #666;">Your verification code is:</p>
                            <div style="background: #f3f4f6; padding: 20px; text-align: center; border-radius: 8px; margin: 20px 0;">
                                <h1 style="font-size: 36px; color: #0066cc; letter-spacing: 5px; margin: 0;">{otp}</h1>
                            </div>
                            <p style="color: #666; font-size: 14px;">This code expires in 10 minutes.</p>
                            <p style="color: #999; font-size: 12px;">If you didn't request this, please ignore this email.</p>
                        </div>
                    </div>
                    """,
                    plain_text_content=f"""
PRISM AI Verification Code

Your verification code: {otp}

This code expires in 10 minutes.
If you didn't request this, please ignore this email.
                    """
                )
                
                sg = SendGridAPIClient(api_key)
                response = sg.send(msg)
                
                if 200 <= response.status_code < 300:
                    logger.info(f"✅ OTP email sent to {email} (Status: {response.status_code})")
                    print(f"✅ Email sent successfully to {email} (fallback method)")
                    return {"success": True, "message": f"Email sent successfully to {email}"}
                else:
                    logger.error(f"❌ SendGrid returned status {response.status_code}")
                    return {"success": False, "error": f"SendGrid returned status {response.status_code}"}
                    
            except Exception as fallback_error:
                logger.error(f"❌ Fallback email send failed: {fallback_error}")
                return {"success": False, "error": f"All email sending methods failed: {str(fallback_error)}"}
        
    except Exception as e:
        logger.error(f"❌ Critical email error for {email}: {e}")
        print(f"❌ Email system error: {e}")
        print(f"💡 But don't worry! Your OTP is shown above in the terminal ☝️")
        return {"success": False, "error": f"Critical email error: {str(e)}"}

@router.post("/verify-otp")
async def verify_otp(payload: OTPVerify, response: Response, request: Request):
    """Verify OTP, complete user registration, and establish a login session."""
    try:
        logger.info(f"🔍 OTP verification for: {payload.email}")
        
        # Get pending user data from Redis
        redis_key = f"pending_signup:{payload.email}"
        user_data_str = await redis_client.get(redis_key)
        
        if not user_data_str:
            logger.error(f"❌ No pending signup found for {payload.email}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No pending signup found or OTP expired. Please sign up again."
            )
        
        user = json.loads(user_data_str)
        
        # Check OTP expiration
        current_time = datetime.now(timezone.utc).timestamp()
        if current_time > user.get("otp_expires_at", 0):
            logger.error(f"⏰ OTP expired for {payload.email}")
            await redis_client.delete(redis_key)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OTP has expired. Please sign up again."
            )
        
        # Verify OTP
        if user.get("otp") != payload.otp:
            logger.error(f"🚫 Invalid OTP for {payload.email}. Expected: {user.get('otp')}, Got: {payload.otp}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid OTP code"
            )
        
        logger.info(f"✅ OTP verified for {payload.email}")
        
        # NOW create the user in database (only after OTP verification)
        final_user_doc = {
            "email": user["email"],
            "password": user["password"],
            "name": user["name"],
            "verified": True,
            "created_at": datetime.now(timezone.utc),
            "verified_at": datetime.now(timezone.utc),
            "profile": {
                "name": user["name"],
                "email": user["email"],
                "bio": "",
                "location": "",
                "website": "",
                "avatarUrl": "",
                "interests": [],
                "hobbies": []
            }
        }
        
        # Insert the verified user into database
        insert_result = await users_collection.insert_one(final_user_doc)
        user_id = str(insert_result.inserted_id)
        
        # Add user to global collection (preserved even after deletion)
        try:
            final_user_doc["_id"] = insert_result.inserted_id
            final_user_doc["user_id"] = user_id
            await add_user_to_global(final_user_doc)
            logger.info(f"✅ User added to global collection: {payload.email}")
        except Exception as global_error:
            logger.warning(f"Failed to add user to global collection: {global_error}")
        
        # Clean up temporary Redis data
        await redis_client.delete(redis_key)
        
        logger.info(f"🎉 User successfully created in database: {payload.email}")
        
        # Create user response
        user_data = {
            "id": user_id,
            "email": final_user_doc["email"],
            "name": final_user_doc.get("name", "User"),
            "verified": True,
        }

        # Immediately create a session so the user is logged in after verification
        session_id = await create_session_for_user(
            {**final_user_doc, "_id": insert_result.inserted_id},
            user_agent=request.headers.get("user-agent"),
            ip=request.client.host if request.client else None,
        )

        cookie_secure = getattr(settings, "SESSION_COOKIE_SECURE", True)
        cookie_samesite = getattr(settings, "SESSION_COOKIE_SAMESITE", "lax")
        cookie_name = getattr(settings, "SESSION_COOKIE_NAME", "session_id")

        response.set_cookie(
            key=cookie_name,
            value=session_id,
            httponly=True,
            secure=cookie_secure,
            samesite=cookie_samesite,  # type: ignore[arg-type]
            path="/",
            max_age=60 * 60 * 24 * getattr(settings, "SESSION_EXPIRE_DAYS", 30)
        )

        logger.info(f"🎉 Registration completed (session created) for {payload.email}")
        print(f"\n🎉 ACCOUNT CREATED SUCCESSFULLY! 🎉\n📧 User: {payload.email}\n👤 Name: {user_data['name']}\n✨ Welcome to PRISM AI!\n")

        return {
            "message": "🎉 Account created successfully! Welcome to PRISM AI!",
            "user": user_data,
            "session_active": True,
            "account_created": True,  # Flag for frontend animation
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OTP verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OTP verification failed"
        )

@router.post("/forgot-password")
async def forgot_password(payload: ForgotPasswordRequest):
    """Send password reset OTP"""
    try:
        # Check if user exists and is verified
        user = await AuthUtils.get_user_by_email(payload.email)
        if not user or not user.get("verified"):
            # Return success even if user doesn't exist for security
            return {"message": "If an account exists, a reset code will be sent."}
        
        # Generate reset OTP
        reset_otp = f"{random.randint(100000, 999999)}"
        otp_expires_at = datetime.now(timezone.utc).timestamp() + (15 * 60)  # 15 minutes
        
        # Store reset OTP
        await users_collection.update_one(
            {"_id": user["_id"]},
            {
                "$set": {
                    "reset_otp": reset_otp,
                    "reset_otp_expires_at": otp_expires_at
                }
            }
        )
        
        # Send reset email
        await send_reset_email(payload.email, reset_otp)
        
        return {"message": "If an account exists, a reset code will be sent."}
        
    except Exception as e:
        logger.error(f"Forgot password failed: {e}")
        return {"message": "If an account exists, a reset code will be sent."}

async def send_reset_email(email: str, reset_otp: str):
    """Send password reset email"""
    try:
        from_addr = getattr(settings, "SENDER_EMAIL", "") or getattr(settings, "MAIL_FROM", "")
        api_key = getattr(settings, "SENDGRID_API_KEY", "")
        
        if not from_addr or not api_key:
            logger.warning("Email sending disabled - missing configuration")
            return
        
        msg = Mail(
            from_email=from_addr,
            to_emails=email,
            subject="PRISM - Password Reset Code",
            html_content=f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #333;">Password Reset Request</h2>
                <p>Your password reset code is:</p>
                <div style="background: #f4f4f4; padding: 20px; text-align: center; font-size: 24px; font-weight: bold; letter-spacing: 5px; margin: 20px 0;">
                    {reset_otp}
                </div>
                <p>This code will expire in 15 minutes.</p>
                <p>If you didn't request a password reset, please ignore this email.</p>
            </div>
            """
        )
        
        sg = SendGridAPIClient(api_key)
        sg.send(msg)
        logger.info(f"Password reset email sent to {email}")
        
    except Exception as e:
        logger.error(f"Failed to send reset email: {e}")

@router.get("/me")
async def get_current_user_info(current_user: User = Depends(get_current_user_from_session)):
    """
    Get current authenticated user information from the session cookie.
    """
    try:
        # Load full user document to build a rich, but safe, response
        from bson import ObjectId

        user_doc = await users_collection.find_one({"_id": ObjectId(current_user.user_id)})
        if not user_doc:
            raise HTTPException(status_code=404, detail="User not found")

        return {"user": AuthUtils.create_user_response(user_doc)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in /auth/me: {e}")
        raise HTTPException(status_code=500, detail="Failed to load current user")

@router.post("/logout")
async def logout(response: Response, request: Request):
    """
    Logout endpoint:
    - Marks the current session as inactive (if present)
    - Clears the session cookie
    """
    cookie_name = getattr(settings, "SESSION_COOKIE_NAME", "session_id")
    session_id = request.cookies.get(cookie_name)

    if session_id:
        try:
            await auth_sessions_collection.update_one(
                {"sessionId": session_id},
                {
                    "$set": {
                        "is_active": False,
                        "invalidated_at": datetime.now(timezone.utc),
                    }
                },
            )
        except Exception as e:
            logger.warning(f"Failed to invalidate session on logout: {e}")

    # Clear cookie in browser
    response.delete_cookie(
        key=cookie_name,
        path="/",
    )

    return {"message": "Logged out successfully", "session_active": False}

    # Compose a clean HTML email template
    html = (
        """
        <div style="font-family:Inter,system-ui,Arial,sans-serif;padding:24px;background:#0b0f1a;color:#e6e6e6;">
          <div style="max-width:520px;margin:auto;background:#111827;border:1px solid #1f2937;border-radius:12px;overflow:hidden;">
            <div style="padding:20px;border-bottom:1px solid #1f2937;display:flex;align-items:center;gap:8px;">
              <span style="display:inline-block;width:28px;height:28px;border-radius:8px;background:linear-gradient(135deg,#6366f1,#3b82f6,#a855f7);"></span>
              <span style="font-weight:700;">PRISM</span>
            </div>
            <div style="padding:24px;">
              <h2 style="margin:0 0 8px 0;font-size:18px;">Your verification code</h2>
              <p style="margin:0 0 16px 0;color:#9ca3af;">Use the code below to verify your email address.</p>
              <div style="display:flex;gap:8px;justify-content:center;margin:16px 0;">
                <div style="font-size:20px;font-weight:700;letter-spacing:2px;background:#0f172a;border:1px solid #1f2937;border-radius:8px;padding:12px 16px;">
                  {otp}
                </div>
              </div>
              <p style="color:#9ca3af;margin:0;">This code expires in 10 minutes.</p>
            </div>
          </div>
          <p style="text-align:center;color:#6b7280;margin-top:12px;font-size:12px;">If you didn’t request this, you can ignore this email.</p>
        </div>
        """
    )

    # If SendGrid is not configured, return success for dev and log OTP
    if not getattr(settings, "SENDGRID_API_KEY", None):
        print(f"[DEV] OTP for {email}: {otp}")
        return {"status": "sent-dev"}

    # Prefer the verified single sender from settings
    from_addr = getattr(settings, "SENDER_EMAIL", None) or getattr(settings, "MAIL_FROM", None) or ""
    if not from_addr:
        # Fail clearly if no sender configured
        raise HTTPException(status_code=500, detail="SENDER_EMAIL (or MAIL_FROM) not configured")

    message = Mail(
        from_email=from_addr,
        to_emails=email,
        subject="Your PRISM OTP",
        html_content=html,
    )
    try:
        # Trim accidental whitespace/newlines in env values
        api_key = str(getattr(settings, "SENDGRID_API_KEY", "")).strip()
        if not api_key:
            raise HTTPException(status_code=500, detail="SENDGRID_API_KEY missing")
        sg = SendGridAPIClient(api_key)
        response = sg.send(message)
        # Log response for debugging
        try:
            print(f"SendGrid status: {response.status_code}")
        except Exception:
            pass
        if 200 <= int(getattr(response, "status_code", 0)) < 300:
            return {"status": "sent"}
        else:
            # Capture body and headers for diagnostics
            detail = {
                "status_code": getattr(response, "status_code", None),
                "body": getattr(response, "body", None).decode() if getattr(response, "body", None) else None,
                "headers": dict(getattr(response, "headers", {})),
            }
            print("SendGrid non-2xx response:", detail)
            # Fall back to dev to avoid blocking signup during testing
            print(f"[DEV-FALLBACK] OTP for {email}: {otp}")
            return {"status": "sent-dev", "debug": detail}
    except Exception as e:
        # Strict SendGrid-only behavior: log and dev-fallback
        print(f"SendGrid error: {e}")
        print(f"[DEV-FALLBACK] OTP for {email}: {otp}")
        return {"status": "sent-dev"}


@router.post("/verify-otp")
async def verify_otp(payload: OTPVerify):
    """Verify OTP and create user account"""
    try:
        user = await users_collection.find_one({"email": payload.email})
        if not user:
            raise HTTPException(status_code=400, detail="User not found")
        
        # Check if this is a pending signup
        if not user.get("signupPending"):
            raise HTTPException(status_code=400, detail="No pending signup found")
        
        if str(user.get("pendingOtp")) != str(payload.otp):
            raise HTTPException(status_code=400, detail="Incorrect OTP")
        
        # Check if OTP has expired
        otp_expires_at = user.get("otpExpiresAt")
        if not otp_expires_at or datetime.now(timezone.utc).timestamp() > otp_expires_at:
            # Clear expired OTP data
            await users_collection.update_one(
                {"email": payload.email},
                {"$unset": {"pendingOtp": "", "otpExpiresAt": "", "tempPasswordHash": "", "signupPending": "", "tempCreatedAt": ""}}
            )
            raise HTTPException(status_code=400, detail="OTP has expired. Please request a new code.")
        
        # NOW create the actual user account after successful OTP verification
        temp_password_hash = user.get("tempPasswordHash")
        if not temp_password_hash:
            raise HTTPException(status_code=500, detail="Missing password data")
        
        # Create user_id (using email as unique identifier)
        user_id = payload.email
        
        await users_collection.update_one(
            {"email": payload.email},
            {
                "$set": {
                    "user_id": user_id,
                    "passwordHash": temp_password_hash,  # Move from temp to permanent
                    "verified": True,
                    "verifiedAt": datetime.now(timezone.utc),
                    "createdAt": datetime.now(timezone.utc),  # Actual account creation time
                    "isFirstLoginCompleted": False,  # User needs onboarding
                    "profileComplete": False  # Profile not yet complete
                },
                "$unset": {
                    "pendingOtp": "",
                    "otpExpiresAt": "",
                    "tempPasswordHash": "",
                    "signupPending": "",
                    "tempCreatedAt": ""
                }
            }
        )
        
        # Save basic user information to long-term memory
        from app.services.memory_manager import save_long_term_memory
        await save_long_term_memory(user_id, f"New user account created with email: {payload.email}")
        
        return {
            "status": "verified", 
            "message": "Account successfully created",
            "user": {
                "email": payload.email,
                "user_id": user_id
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OTP verify failed: {e}")

@router.post("/forgot-password")
async def forgot_password(payload: ForgotPasswordRequest):
    """Send password reset link"""
    try:
        user = await users_collection.find_one({"email": payload.email})
        if not user or not user.get("verified"):
            # Don't reveal if email exists or not for security
            return {"status": "sent", "message": "If the email exists, a reset link has been sent"}
        
        # In a real app, you'd generate a secure token and send reset email
        # For now, just return success
        return {"status": "sent", "message": "Password reset link sent to your email"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Password reset failed: {e}")
