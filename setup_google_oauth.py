#!/usr/bin/env python3
"""
Script to set up Google OAuth in Django admin automatically.
This creates the necessary Site and SocialApp entries.
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ghee_store.settings')
django.setup()

from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp

def setup_google_oauth():
    """Setup Google OAuth configuration"""
    
    print("=" * 60)
    print("Google OAuth Setup for Gaumaatri")
    print("=" * 60)
    
    # Step 1: Update or create Site
    print("\n1. Setting up Site...")
    site, created = Site.objects.get_or_create(id=1)
    site.domain = '127.0.0.1:8000'
    site.name = 'Gaumaatri'
    site.save()
    if created:
        print(f"   ✓ Created new site: {site.name}")
    else:
        print(f"   ✓ Updated existing site: {site.name}")
    
    # Step 2: Get Google credentials from user
    print("\n2. Google OAuth Credentials")
    print("   You need to get these from Google Cloud Console:")
    print("   https://console.cloud.google.com/apis/credentials")
    print()
    
    # Check for environment variables first
    client_id = os.environ.get('GOOGLE_CLIENT_ID', '')
    client_secret = os.environ.get('GOOGLE_CLIENT_SECRET', '')
    
    if not client_id:
        client_id = input("   Enter your Google Client ID: ").strip()
    else:
        print(f"   ✓ Found GOOGLE_CLIENT_ID in environment")
    
    if not client_secret:
        client_secret = input("   Enter your Google Client Secret: ").strip()
    else:
        print(f"   ✓ Found GOOGLE_CLIENT_SECRET in environment")
    
    if not client_id or not client_secret:
        print("\n   ✗ Error: Both Client ID and Secret are required!")
        print("   Please set them as environment variables or enter them when prompted.")
        return False
    
    # Step 3: Create or update SocialApp
    print("\n3. Creating Google Social Application...")
    
    # Try to get existing app
    try:
        app = SocialApp.objects.get(provider='google')
        print("   ℹ Found existing Google app, updating...")
        app.name = 'Google'
        app.client_id = client_id
        app.secret = client_secret
        app.save()
        print("   ✓ Updated Google Social Application")
    except SocialApp.DoesNotExist:
        app = SocialApp.objects.create(
            provider='google',
            name='Google',
            client_id=client_id,
            secret=client_secret,
        )
        print("   ✓ Created new Google Social Application")
    
    # Add the site to the app
    if site not in app.sites.all():
        app.sites.add(site)
        print(f"   ✓ Added site '{site.name}' to Google app")
    
    # Step 4: Verify setup
    print("\n4. Verification")
    print(f"   Site Domain: {site.domain}")
    print(f"   Provider: {app.provider}")
    print(f"   Client ID: {client_id[:20]}...{client_id[-10:]}")
    print(f"   Secret: {'*' * 20}...{client_secret[-4:]}")
    
    print("\n" + "=" * 60)
    print("✓ Setup Complete!")
    print("=" * 60)
    print("\nNext Steps:")
    print("1. Make sure your Google Console has this redirect URI:")
    print("   http://127.0.0.1:8000/accounts/google/login/callback/")
    print("\n2. Add your email as a test user in Google Console")
    print("   (if your app is in Testing mode)")
    print("\n3. Test it by visiting:")
    print("   http://127.0.0.1:8000/register/")
    print("   Click 'Continue with Google'")
    print("\n" + "=" * 60)
    
    return True

if __name__ == '__main__':
    try:
        success = setup_google_oauth()
        if success:
            print("\n✓ You can now use Google Sign-In!")
        else:
            print("\n✗ Setup incomplete. Please try again.")
    except Exception as e:
        print(f"\n✗ Error during setup: {e}")
        import traceback
        traceback.print_exc()
