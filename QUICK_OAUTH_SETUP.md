# Quick Google OAuth Setup - Gaumaatri

## What's Been Done ✅

1. ✅ Installed `django-allauth` package
2. ✅ Updated Django settings with Google OAuth configuration
3. ✅ Updated login and register pages with "Continue with Google" button
4. ✅ Database migrations completed
5. ✅ Changed logo from banner2.jpg to logo.png on both pages

## What You Need to Do 🔧

### 1. Get Google OAuth Credentials (5 minutes)

1. Visit: https://console.cloud.google.com/
2. Create new project or select existing
3. Go to: **APIs & Services** → **Credentials**
4. Click: **Create Credentials** → **OAuth client ID**
5. Configure OAuth consent screen if needed:
   - App name: `Gaumaatri`
   - Email: `gaumaatri@gmail.com`
6. Create OAuth Client ID:
   - Type: **Web application**
   - Name: `Gaumaatri Django`
   - Authorized redirect URIs: `http://127.0.0.1:8000/accounts/google/login/callback/`
7. Copy **Client ID** and **Client Secret**

### 2. Set Environment Variables

Run these commands in your terminal (replace with your actual values):

```bash
export GOOGLE_CLIENT_ID="your-client-id.apps.googleusercontent.com"
export GOOGLE_CLIENT_SECRET="your-client-secret"
```

### 3. Configure in Django Admin

1. Start server: `python3.12 manage.py runserver`
2. Go to: http://127.0.0.1:8000/admin/
3. **Sites section:**
   - Click on `example.com`
   - Domain: `127.0.0.1:8000`
   - Display name: `Gaumaatri`
   - Save
4. **Social applications section:**
   - Add new
   - Provider: `Google`
   - Name: `Google`
   - Client ID: (paste from Google Console)
   - Secret key: (paste from Google Console)
   - Sites: Move `127.0.0.1:8000` to "Chosen sites"
   - Save

### 4. Test It! 🎉

1. Visit: http://127.0.0.1:8000/register/
2. Click "Continue with Google"
3. Select your Google account
4. You're logged in!

## Pages Updated

- ✅ `/register/` - Has Google sign-in button
- ✅ `/login/` - Has Google sign-in button
- ✅ Both pages now use logo.png instead of banner2.jpg

## Files Modified

1. `ghee_store/settings.py` - Added allauth configuration
2. `ghee_store/urls.py` - Added allauth URLs
3. `store/templates/store/register.html` - Added Google button
4. `store/templates/store/login.html` - Added Google button + logo update
5. Database - New tables created for social authentication

## Troubleshooting

**"Social application not found"**
→ Complete step 3 above (Django admin configuration)

**"redirect_uri_mismatch"**
→ Check redirect URI is exactly: `http://127.0.0.1:8000/accounts/google/login/callback/`

**"Client ID not set"**
→ Set environment variables (step 2) and restart Django server

## Next Steps

After testing locally, update for production:
1. Add production domain to Google Console
2. Update Site domain in Django admin
3. Set environment variables on production server
4. Use HTTPS in production

---

For detailed instructions, see: `GOOGLE_OAUTH_SETUP.md`
