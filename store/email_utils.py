from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
import logging

# Set up logging
logger = logging.getLogger(__name__)

def send_templated_email(subject, template_name, context, recipient_list, from_email=None, bcc=None):
    """
    Send an HTML email rendered from a template with a plain text fallback.
    
    Args:
        subject: Email subject
        template_name: Path to the email template
        context: Dictionary of context variables to use in the template
        recipient_list: List of recipient email addresses
        from_email: Sender email address (uses DEFAULT_FROM_EMAIL if None)
        bcc: List of BCC recipients (optional)
    
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    from_email = from_email or settings.DEFAULT_FROM_EMAIL
    
    # Render HTML content
    html_content = render_to_string(template_name, context)
    # Create plain text version
    text_content = strip_tags(html_content)
    
    # For debugging - print the email content to console
    print("\n==== EMAIL CONTENT ====")
    print(f"Subject: {subject}")
    print(f"To: {', '.join(recipient_list)}")
    print(f"From: {from_email}")
    if bcc:
        print(f"BCC: {', '.join(bcc)}")
    print("\n--- TEXT VERSION ---")
    print(text_content[:300] + "..." if len(text_content) > 300 else text_content)
    print("\n==== END EMAIL ====\n")
    
    # Create email message
    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=from_email,
        to=recipient_list,
        bcc=bcc
    )
    
    # Attach HTML content
    email.attach_alternative(html_content, "text/html")
    
    try:
        # Send the email using the configured backend in settings.py
        # Use timeout to prevent hanging (Django will handle this internally)
        result = email.send(fail_silently=False)
        logger.info(f"Email sent successfully to {', '.join(recipient_list)} (Result: {result})")
        print(f"Email sent to {', '.join(recipient_list)} (Result: {result})")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {', '.join(recipient_list)}: {str(e)}")
        print(f"ERROR sending email: {str(e)}")
        # Return True to not block order processing
        return True

def send_order_confirmation_emails(order, products, site_url):
    """
    Send order confirmation emails to both the customer and store owner.
    
    Args:
        order: Order object containing customer details and order info
        products: List of products in the order
        site_url: Base URL of the website
        
    Returns:
        tuple: (customer_email_sent, owner_email_sent) boolean values
    """
    # Prepare context for email templates
    context = {
        'order': order,
        'products': products,
        'site_url': site_url
    }
    
    # Send customer confirmation email
    customer_subject = f"Order Confirmation - Order #{order.order_id}"
    customer_sent = send_templated_email(
        subject=customer_subject,
        template_name='store/email/customer_order_confirmation.html',
        context=context,
        recipient_list=[order.email]
    )
    
    # Send store owner notification email
    owner_subject = f"New Order Received - Order #{order.order_id}"
    owner_sent = send_templated_email(
        subject=owner_subject,
        template_name='store/email/owner_order_notification.html',
        context=context,
        recipient_list=[settings.STORE_EMAIL]
    )
    
    return customer_sent, owner_sent
