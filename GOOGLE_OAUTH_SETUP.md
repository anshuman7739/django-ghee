# Google OAuth Setup Guide for Gaumaatri

This guide will help you set up Google OAuth authentication for your Django application.

## Step 1: Create Google OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Navigate to **APIs & Services** > **Credentials**
4. Click **Create Credentials** > **OAuth client ID**
5. If prompted, configure the OAuth consent screen first:
   - Choose **External** user type
   - Fill in the required information:
     - App name: **Gaumaatri**
     - User support email: **gaumaatri@gmail.com**
     - Developer contact: **gaumaatri@gmail.com**
   - Click **Save and Continue**
   - No need to add scopes (default scopes are sufficient)
   - Add test users if in testing mode
   - Click **Save and Continue**

6. Back to creating OAuth client ID:
   - Application type: **Web application**
   - Name: **Gaumaatri Django App**
   - Authorized JavaScript origins:
     - `http://127.0.0.1:8000`
     - `http://localhost:8000`
   - Authorized redirect URIs:
     - `http://127.0.0.1:8000/accounts/google/login/callback/`
     - `http://localhost:8000/accounts/google/login/callback/`
   - Click **Create**

7. Copy your **Client ID** and **Client Secret**

## Step 2: Set Environment Variables

Add these to your environment (in terminal or `.env` file):

```bash
export GOOGLE_CLIENT_ID="your-client-id-here.apps.googleusercontent.com"
export GOOGLE_CLIENT_SECRET="your-client-secret-here"
```

For permanent setup, add to your `~/.zshrc` file:

```bash
echo 'export GOOGLE_CLIENT_ID="your-client-id"' >> ~/.zshrc
echo 'export GOOGLE_CLIENT_SECRET="your-client-secret"' >> ~/.zshrc
source ~/.zshrc
```

## Step 3: Configure Django Admin

1. Start your Django server:
```bash
python3.12 manage.py runserver
```

2. Go to Django admin: http://127.0.0.1:8000/admin/

3. Navigate to **Sites** and click on **example.com**
   - Change domain to: `127.0.0.1:8000`
   - Change display name to: `Gaumaatri`
   - Click **Save**

4. Navigate to **Social applications** (under SOCIAL ACCOUNTS section)
   - Click **Add Social Application**
   - Provider: **Google**
   - Name: **Google OAuth**
   - Client ID: Paste your Google Client ID
   - Secret key: Paste your Google Client Secret
   - Sites: Select `127.0.0.1:8000` and move it to "Chosen sites"
   - Click **Save**

## Step 4: Test Google Login

1. Go to http://127.0.0.1:8000/register/ or http://127.0.0.1:8000/login/
2. Click "Continue with Google"
3. Select your Google account
4. Grant permissions
5. You should be redirected back to your site and logged in!

## Production Setup

For production deployment, update the following:

1. In Google Cloud Console, add your production domain:
   - Authorized JavaScript origins: `https://yourdomain.com`
   - Authorized redirect URIs: `https://yourdomain.com/accounts/google/login/callback/`

2. In Django admin (on production):
   - Update the Site domain to your production domain
   - Update or create a new Social Application with production credentials

3. Set environment variables on your production server

## Troubleshooting

### Error: "redirect_uri_mismatch"
- Make sure the redirect URI in Google Console exactly matches: `http://127.0.0.1:8000/accounts/google/login/callback/`
- Check that the Site domain in Django admin is correct

### Error: "Social application not found"
- Make sure you've created the Social Application in Django admin
- Verify the provider is set to "Google"
- Check that the site is selected in "Chosen sites"

### Error: "Client ID or Secret not found"
- Make sure environment variables are set correctly
- Restart your Django server after setting environment variables
- Check that the Client ID and Secret in Django admin match those from Google Console

## Security Notes

- Never commit your Client Secret to version control
- Use environment variables for sensitive data
- In production, use HTTPS only
- Regularly rotate your OAuth credentials
- Review OAuth consent screen settings before publishing

## Current Status

✅ Django-allauth installed
✅ Google provider configured
✅ Database migrations completed
✅ Login and Register pages updated with Google button
✅ URLs configured

⏳ Pending: Google OAuth credentials setup (requires manual steps above)
