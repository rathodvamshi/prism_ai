from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from app.config import settings
from app.utils.llm_client import get_llm_response
import json
from datetime import datetime
from typing import Optional


async def extract_email_details(message: str) -> dict:
    """
    Uses AI to extract: recipient_email, subject, body.
    """
    system_prompt = """
    You are an email parser.
    Extract the following from the user's request:
    1. recipient_email (Look for an email address. If none, return null)
    2. subject (Create a professional subject line)
    3. body (The main content of the email, polished and professional)
    
    Return ONLY valid JSON. Example:
    {
        "recipient_email": "boss@company.com",
        "subject": "Update on Project",
        "body": "Dear Boss, I am writing to inform you..."
    }
    """
    
    response = await get_llm_response(prompt=message, system_prompt=system_prompt)
    
    try:
        start = response.find('{')
        end = response.rfind('}') + 1
        return json.loads(response[start:end])
    except:
        return {"error": "Could not parse email details"}

async def send_email_notification(message: str):
    """
    Orchestrates extraction and sending.
    """
    # 1. Extract Details
    details = await extract_email_details(message)
    
    if not details.get("recipient_email"):
        return "❌ I couldn't find an email address in your request. Please specify who to email."

    # 2. Construct Email
    email_msg = Mail(
        from_email=settings.SENDER_EMAIL,
        to_emails=details["recipient_email"],
        subject=details["subject"],
        html_content=f"<p>{details['body']}</p><br><em>Sent by PRISM AI</em>"
    )

    # 3. Send via SendGrid
    try:
        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        response = sg.send(email_msg)
        
        # ADD THIS PRINT STATEMENT
        print(f"SendGrid Status: {response.status_code}") 
        print(f"SendGrid Body: {response.body}")
        
        return f"📧 Email sent to {details['recipient_email']}! (Subject: {details['subject']})"
    except Exception as e:
        print(f"SendGrid Error: {e}")
        return f"❌ Failed to send email. Error: {str(e)}"


async def send_professional_email(task: dict, retry_count: int = 0, max_retries: int = 3):
    """
    Sends a polished HTML reminder email for a completed task.
    Includes retry logic for failed attempts.
    """
    user_name = task.get("user_name") or "Chief"
    user_email = task.get("user_email") or task.get("email")
    
    # Validation
    if not user_email:
        print("❌ No user email provided in task, cannot send notification")
        raise ValueError("User email is required")
    
    if not user_email or '@' not in user_email:
        print(f"❌ Invalid email address: {user_email}")
        raise ValueError(f"Invalid email address: {user_email}")

    description = task.get("description", "Your scheduled task")
    
    # ☁️ Use display_time if available (shows IST to user), otherwise format due_date
    display_time = task.get("display_time")
    if display_time:
        time_str = display_time  # Already formatted as "2025-12-16 09:00 PM IST"
        date_str = display_time.split(" IST")[0] if " IST" in display_time else display_time
    else:
        due_date = task.get("due_date")
        if isinstance(due_date, datetime):
            time_str = due_date.strftime("%A, %B %d at %I:%M %p")
            date_str = due_date.strftime("%Y-%m-%d %H:%M")
        else:
            time_str = "Soon"
            date_str = "N/A"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin: 0; padding: 20px; background-color: #f5f5f5; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;">
        <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
            <!-- Header -->
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px 20px; text-align: center;">
                <h1 style="margin: 0; color: #ffffff; font-size: 28px; font-weight: 600;">⏰ Reminder Alert</h1>
                <p style="margin: 8px 0 0 0; color: rgba(255, 255, 255, 0.9); font-size: 14px;">PRISM Personal AI Assistant</p>
            </div>
            
            <!-- Body -->
            <div style="padding: 40px 30px;">
                <p style="font-size: 18px; color: #333333; margin: 0 0 12px 0;">Hello <strong style="color: #667eea;">{user_name}</strong>, 👋</p>
                <p style="font-size: 16px; color: #666666; margin: 0 0 24px 0; line-height: 1.5;">It's time! You asked me to remind you about this:</p>
                
                <!-- Task Card -->
                <div style="background: linear-gradient(135deg, #f3f4f6 0%, #e5e7eb 100%); padding: 20px; border-radius: 8px; border-left: 5px solid #667eea; margin: 0 0 24px 0;">
                    <h2 style="margin: 0 0 12px 0; color: #111827; font-size: 20px; font-weight: 600;">{description}</h2>
                    <div style="display: flex; align-items: center; gap: 8px; color: #6b7280; font-size: 14px;">
                        <span style="font-weight: 500;">📅 Scheduled:</span>
                        <span>{time_str}</span>
                    </div>
                </div>
                
                <!-- Status -->
                <div style="background-color: #ecfdf5; border: 1px solid #a7f3d0; border-radius: 8px; padding: 16px; margin: 0 0 24px 0;">
                    <p style="margin: 0; color: #065f46; font-size: 14px; line-height: 1.6;">
                        <strong>✅ Status:</strong> I've marked this task as <strong>Completed</strong> in your dashboard. Keep up the great work! 🚀
                    </p>
                </div>
                
                <p style="font-size: 14px; color: #9ca3af; margin: 0; line-height: 1.6;">
                    This is an automated reminder from your PRISM AI assistant. You're doing amazing at staying organized! 💪
                </p>
            </div>
            
            <!-- Footer -->
            <div style="background-color: #f9fafb; padding: 20px; text-align: center; border-top: 1px solid #e5e7eb;">
                <p style="margin: 0 0 8px 0; color: #6b7280; font-size: 13px;">
                    Sent with 💜 by <strong>PRISM AI</strong>
                </p>
                <p style="margin: 0; color: #9ca3af; font-size: 11px;">
                    {datetime.now().strftime("%B %d, %Y at %I:%M %p")}
                </p>
            </div>
        </div>
    </body>
    </html>
    """

    from_addr = getattr(settings, "SENDER_EMAIL", None) or getattr(settings, "MAIL_FROM", None)
    if not from_addr:
        error_msg = "❌ SENDER_EMAIL not configured in environment"
        print(error_msg)
        raise ValueError(error_msg)

    msg = Mail(
        from_email=from_addr,
        to_emails=user_email,
        subject=f"⏰ Reminder: {description}",
        html_content=html_content,
    )

    try:
        print(f"📧 Attempting to send email to {user_email}...")
        print(f"   From: {from_addr}")
        print(f"   Subject: Reminder: {description}")
        
        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        response = sg.send(msg)
        
        print(f"✅ SendGrid Response: {response.status_code}")
        print(f"   Body: {response.body}")
        print(f"   Headers: {response.headers}")
        
        if response.status_code in [200, 201, 202]:
            print(f"✅ Email successfully sent to {user_email}")
            return True
        else:
            raise Exception(f"Unexpected status code: {response.status_code}")
            
    except Exception as e:
        error_msg = f"❌ SendGrid Error (Attempt {retry_count + 1}/{max_retries}): {str(e)}"
        print(error_msg)
        
        # Fast retry logic - reduced wait times for speed
        if retry_count < max_retries:
            import asyncio
            wait_time = retry_count + 1  # 1, 2, 3 seconds (faster than before)
            print(f"⏳ Fast retry in {wait_time}s...")
            await asyncio.sleep(wait_time)
            return await send_professional_email(task, retry_count + 1, max_retries)
        else:
            print(f"❌ Max retries reached. Email could not be sent.")
            raise Exception(f"Failed to send email after {max_retries} attempts: {str(e)}")


async def send_otp_email_direct(to_email: str, otp_code: str, subject: Optional[str] = None) -> bool:
    """
    ☁️ Sends a high-priority OTP with a professional design.
    Perfect email delivery with robust error handling.
    """
    if not to_email:
        raise ValueError("Email is required for OTP delivery")
    if not otp_code:
        raise ValueError("OTP code is required")

    from_addr = getattr(settings, "SENDER_EMAIL", None) or getattr(settings, "MAIL_FROM", None)
    if not from_addr:
        print("⚠️ SENDER_EMAIL not configured - OTP email cannot be sent")
        raise ValueError("SENDER_EMAIL not configured")

    api_key = getattr(settings, "SENDGRID_API_KEY", None)
    if not api_key:
        print("⚠️ SendGrid API key not configured - OTP email cannot be sent")
        raise ValueError("SendGrid API key not configured")

    subject = subject or "PRISM AI Verification Code"
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin: 0; padding: 20px; background-color: #f5f5f5; font-family: 'Helvetica Neue', Arial, sans-serif;">
        <div style="max-width: 500px; margin: 0 auto; background-color: #ffffff; border: 1px solid #e5e7eb; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 24px; text-align: center;">
                <h1 style="color: white; margin: 0; font-size: 24px; font-weight: 600;">PRISM AI</h1>
                <p style="color: rgba(255, 255, 255, 0.9); margin: 8px 0 0 0; font-size: 14px;">Verification Code</p>
            </div>
            <div style="padding: 32px; text-align: center;">
                <p style="color: #6b7280; font-size: 16px; margin-bottom: 24px;">Here is your secure verification code:</p>
                <div style="background-color: #F3F4F6; display: inline-block; padding: 20px 40px; border-radius: 8px; letter-spacing: 8px; font-weight: bold; font-size: 36px; color: #111827; border: 2px solid #E5E7EB;">
                    {otp_code}
                </div>
                <p style="color: #9ca3af; font-size: 14px; margin-top: 24px; line-height: 1.6;">
                    This code expires in <strong>10 minutes</strong>.<br>
                    If you didn't request this, please ignore this email.
                </p>
            </div>
            <div style="background-color: #f9fafb; padding: 16px; text-align: center; border-top: 1px solid #e5e7eb;">
                <p style="color: #9ca3af; font-size: 12px; margin: 0;">Secured by PRISM Personal AI Assistant</p>
            </div>
        </div>
    </body>
    </html>
    """

    plain_text_content = f"""
PRISM AI Verification Code

Your verification code: {otp_code}

This code expires in 10 minutes.
If you didn't request this, please ignore this email.

Secured by PRISM Personal AI Assistant
    """

    try:
        msg = Mail(
            from_email=from_addr,
            to_emails=to_email,
            subject=subject,
            html_content=html_content,
            plain_text_content=plain_text_content,
        )

        sg = SendGridAPIClient(api_key)
        response = sg.send(msg)
        
        status_code = int(getattr(response, "status_code", 0))
        
        if 200 <= status_code < 300:
            print(f"✅ OTP email sent successfully to {to_email} (Status: {status_code})")
            return True
        else:
            error_msg = f"SendGrid returned status {status_code}"
            print(f"❌ {error_msg}")
            raise Exception(error_msg)
            
    except Exception as e:
        print(f"❌ Failed to send OTP email to {to_email}: {e}")
        raise