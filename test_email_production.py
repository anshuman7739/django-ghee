"""
Test script for production email configuration.

This script sends a simple test email to verify that the production email
settings are working correctly. Before running this script:

1. Make sure EMAIL_HOST_PASSWORD is correctly set in settings.py with your Google App Password
2. Make sure you have an active internet connection

Usage:
    python test_email_production.py

If successful, you should see "Email sent successfully!" in the console and 
receive an actual email in your inbox.
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ghee_store.settings')
django.setup()

from django.core.mail import EmailMultiAlternatives
from django.conf import settings

def test_email_sending():
    """Send a simple test email to verify production email settings."""
    
    # Email details
    subject = "Test Email from Gaumaatri A2 Desi Ghee"
    from_email = settings.DEFAULT_FROM_EMAIL
    to_email = settings.STORE_EMAIL  # Sending to yourself to test
    
    # Email content
    text_content = """
    This is a test email to verify that the production email settings are working correctly.
    
    If you're seeing this, your email configuration is successful!
    
    Best regards,
    Gaumaatri A2 Desi Ghee Team
    """
    
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #D4AF37; border-radius: 5px;">
        <h2 style="color: #D4AF37; text-align: center;">Test Email</h2>
        <p>This is a test email to verify that the production email settings are working correctly.</p>
        <p><strong>If you're seeing this, your email configuration is successful!</strong></p>
        <p>Email backend: {settings.EMAIL_BACKEND}</p>
        <p>Email host: {settings.EMAIL_HOST}</p>
        <hr style="border-color: #D4AF37;">
        <p style="text-align: center; color: #777;">Best regards,<br>Gaumaatri A2 Desi Ghee Team</p>
    </div>
    """
    
    # Create the email
    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=from_email,
        to=[to_email]
    )
    
    # Add HTML content
    email.attach_alternative(html_content, "text/html")
    
    try:
        # Send the email
        result = email.send()
        print("\n=================================")
        print("✅ Email sent successfully!")
        print(f"   Result: {result}")
        print("   Recipient: " + to_email)
        print("   Check your inbox for the test email.")
        print("=================================\n")
        return True
    except Exception as e:
        print("\n=================================")
        print("❌ Failed to send email!")
        print(f"   Error: {str(e)}")
        print("=================================\n")
        print("Troubleshooting tips:")
        print("1. Check your internet connection")
        print("2. Verify that you've set the correct App Password in settings.py")
        print("3. Make sure 2-Step Verification is enabled on your Google account")
        print("4. Check if 'Less secure app access' is turned off (it should be)")
        print("5. If using Gmail, check if you've exceeded daily sending limits")
        return False

if __name__ == "__main__":
    print("\nTesting production email settings...")
    print(f"Using email backend: {settings.EMAIL_BACKEND}")
    print(f"Sending from: {settings.DEFAULT_FROM_EMAIL}")
    print(f"Sending to: {settings.STORE_EMAIL}")
    
    # Test sending email
    test_email_sending()
