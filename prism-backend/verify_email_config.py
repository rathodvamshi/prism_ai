"""
Email Configuration Verification Script

This script checks if your SendGrid email configuration is properly set up.
Run this before starting the application to ensure email notifications will work.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def verify_email_config():
    """Verify SendGrid email configuration"""
    print("=" * 60)
    print("📧 EMAIL CONFIGURATION VERIFICATION")
    print("=" * 60)
    
    issues = []
    warnings = []
    
    # Check SENDGRID_API_KEY
    api_key = os.getenv("SENDGRID_API_KEY", "")
    if not api_key:
        issues.append("❌ SENDGRID_API_KEY is not set in .env file")
    elif not api_key.startswith("SG."):
        warnings.append("⚠️  SENDGRID_API_KEY doesn't start with 'SG.' - might be invalid")
    else:
        print(f"✅ SENDGRID_API_KEY: {'*' * 20}{api_key[-8:]}")
    
    # Check SENDER_EMAIL
    sender_email = os.getenv("SENDER_EMAIL", "")
    if not sender_email:
        issues.append("❌ SENDER_EMAIL is not set in .env file")
    elif "@" not in sender_email:
        issues.append("❌ SENDER_EMAIL is not a valid email address")
    else:
        print(f"✅ SENDER_EMAIL: {sender_email}")
    
    # Check MAIL_FROM (alternative)
    mail_from = os.getenv("MAIL_FROM", "")
    if mail_from:
        print(f"ℹ️  MAIL_FROM: {mail_from} (alternative sender)")
    
    print("\n" + "=" * 60)
    
    if issues:
        print("❌ CONFIGURATION ISSUES:")
        for issue in issues:
            print(f"   {issue}")
        print("\n💡 FIX:")
        print("   1. Create/edit .env file in prism-backend folder")
        print("   2. Add these lines:")
        print('      SENDGRID_API_KEY="SG.your_actual_api_key_here"')
        print('      SENDER_EMAIL="your-verified-email@domain.com"')
        print("\n   Get your SendGrid API key from:")
        print("   https://app.sendgrid.com/settings/api_keys")
        return False
    
    if warnings:
        print("⚠️  WARNINGS:")
        for warning in warnings:
            print(f"   {warning}")
        print()
    
    print("✅ Email configuration looks good!")
    print("\n📝 NEXT STEPS:")
    print("   1. Make sure your sender email is verified in SendGrid")
    print("   2. Start the backend: python -m uvicorn app.main:app --reload")
    print("   3. Create a reminder and wait for it to trigger")
    print("   4. Check your email inbox!")
    
    return True


def test_sendgrid_connection():
    """Test actual connection to SendGrid (optional)"""
    try:
        from sendgrid import SendGridAPIClient
        
        api_key = os.getenv("SENDGRID_API_KEY", "")
        if not api_key:
            return
        
        print("\n" + "=" * 60)
        print("🔌 TESTING SENDGRID CONNECTION")
        print("=" * 60)
        
        sg = SendGridAPIClient(api_key)
        # Test API key validity by checking user profile
        response = sg.client.user.profile.get()
        
        if response.status_code == 200:
            print("✅ Successfully connected to SendGrid!")
            print(f"   Status Code: {response.status_code}")
        else:
            print(f"⚠️  SendGrid responded with status: {response.status_code}")
            
    except ImportError:
        print("⚠️  SendGrid library not installed. Run: pip install sendgrid")
    except Exception as e:
        print(f"❌ SendGrid connection failed: {str(e)}")
        print("   Check your API key and internet connection")


if __name__ == "__main__":
    print("\n")
    config_ok = verify_email_config()
    
    if config_ok:
        test_sendgrid_connection()
    
    print("\n" + "=" * 60)
    print()
