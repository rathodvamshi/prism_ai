from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from app.config import settings
from app.utils.llm_client import get_llm_response
import json

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