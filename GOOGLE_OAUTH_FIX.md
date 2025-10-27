# Fix: "Access blocked: Authorization Error"

This error occurs when your Google OAuth app is in Testing mode and you haven't added yourself as a test user.

## Quick Fix (2 minutes)

### Option 1: Add Test Users (Recommended for Testing)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project
3. Navigate to **APIs & Services** → **OAuth consent screen**
4. Scroll down to **Test users** section
5. Click **+ ADD USERS**
6. Add your email address (the one you're trying to sign in with)
7. Click **SAVE**
8. Try logging in again - it should work now!

### Option 2: Publish Your App (For Production)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to **APIs & Services** → **OAuth consent screen**
3. Click **PUBLISH APP** button
4. Confirm by clicking **CONFIRM**
5. Your app is now available to all users

**Note:** Publishing requires verification if you request sensitive scopes. For basic profile and email, verification is usually not required.

## Detailed Steps for Test Users

1. **Go to OAuth Consent Screen:**
   - https://console.cloud.google.com/apis/credentials/consent

2. **Add Test Users:**
   ```
   Click on "OAuth consent screen" in left menu
   Scroll to "Test users" section
   Click "+ ADD USERS"
   Enter email addresses (one per line):
     - Your email
     - Any other emails you want to test with
   Click "SAVE"
   ```

3. **Verify Publishing Status:**
   - If status shows "Testing", only test users can sign in
   - If status shows "In production", anyone can sign in

## Common Issues

### "Access blocked: This app's request is invalid"
**Fix:** Check your redirect URI in Google Console matches exactly:
- `http://127.0.0.1:8000/accounts/google/login/callback/`

### "Error 400: redirect_uri_mismatch"
**Fix:** 
1. Go to Google Cloud Console → Credentials
2. Click on your OAuth 2.0 Client ID
3. Under "Authorized redirect URIs", make sure you have:
   - `http://127.0.0.1:8000/accounts/google/login/callback/`
4. Click **SAVE**

### "Social application not found"
**Fix:** Configure in Django admin:
1. Go to http://127.0.0.1:8000/admin/
2. Navigate to **Social applications**
3. Add new application with Google credentials
4. Select the correct site

## Verification Checklist

✅ OAuth consent screen configured
✅ Your email added as test user (if in Testing mode)
✅ Redirect URI: `http://127.0.0.1:8000/accounts/google/login/callback/`
✅ Client ID and Secret set in Django admin
✅ Site domain set to `127.0.0.1:8000` in Django admin

## Current Settings Status

- ✅ OAUTH_PKCE_ENABLED: True (Enhanced security)
- ✅ SOCIALACCOUNT_AUTO_SIGNUP: True (Auto-create accounts)
- ✅ Email verification: Optional

## Testing Steps

1. Add yourself as test user in Google Console
2. Clear browser cookies/cache or use incognito mode
3. Visit: http://127.0.0.1:8000/register/
4. Click "Continue with Google"
5. Select your Google account
6. Grant permissions
7. You should be redirected back and logged in!

## For Production

When ready to go live:

1. **Publish your OAuth app** in Google Console
2. **Update redirect URIs** to include your production domain:
   - `https://yourdomain.com/accounts/google/login/callback/`
3. **Update Django Site** in admin to your production domain
4. **Add production Client ID/Secret** as environment variables
5. **Use HTTPS** (required for production OAuth)

## Still Having Issues?

Check the Django server console for detailed error messages. Common errors:

- `SocialApp matching query does not exist` → Configure in Django admin
- `redirect_uri_mismatch` → Check Google Console redirect URIs
- `invalid_client` → Check Client ID and Secret are correct

---

**Most likely cause of your current error:** Your email is not added as a test user in Google Cloud Console. Add it following Option 1 above!
