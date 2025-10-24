# Email Setup Instructions for Gaumaatri Contact Form

## ✅ What's Already Done
- Contact form now sends emails to `gaumaatri@gmail.com`
- Email configuration is set up in settings.py
- Both contact forms will send email notifications

## 🔧 Steps to Enable Email Sending

### Step 1: Enable 2-Step Verification in Gmail
1. Go to your Google Account: https://myaccount.google.com/
2. Click on **Security** in the left menu
3. Under "How you sign in to Google", click on **2-Step Verification**
4. Follow the steps to enable it

### Step 2: Generate an App Password
1. After enabling 2-Step Verification, go back to Security
2. Click on **2-Step Verification** again
3. Scroll down to **App passwords** and click on it
4. Select:
   - **App:** Mail
   - **Device:** Other (Custom name) - type "Django Gaumaatri"
5. Click **Generate**
6. Google will show you a **16-character password** (like: `abcd efgh ijkl mnop`)
7. **Copy this password** - you won't see it again!

### Step 3: Set the Environment Variable

Before running your Django server, set the email password:

```bash
export EMAIL_PASSWORD="your-16-character-app-password"
```

Then start your server:
```bash
python manage.py runserver
```

**For permanent setup** (add to your shell profile):
```bash
# Add this line to ~/.zshrc (or ~/.bash_profile)
export EMAIL_PASSWORD="your-16-character-app-password"

# Then reload:
source ~/.zshrc
```

## 📧 How It Works

When someone fills out the contact form with:
- Name
- Email
- Phone
- Message

You will receive an email at **gaumaatri@gmail.com** with:
```
Subject: New Contact Form Submission from [Name]

New contact form submission received:

Name: [Name]
Email: [Email]
Phone: [Phone]

Message:
[Their message]

---
Sent from Gaumaatri Website Contact Form
```

## 🧪 Testing

1. Set up the app password as described above
2. Restart your Django server
3. Go to http://127.0.0.1:8000/contact/
4. Fill out the form and submit
5. Check your gaumaatri@gmail.com inbox!

## ⚠️ Important Notes

- **Never commit the app password to Git**
- The app password is different from your regular Gmail password
- If emails aren't sending, check the terminal for error messages
- Gmail may block emails if you send too many too quickly
- For production, consider using a dedicated email service like SendGrid or AWS SES

## 🔙 Switch Back to Console (Development Mode)

If you want to see emails in the terminal instead of actually sending them (useful for testing), change this in `settings.py`:

```python
# Change this:
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

# To this:
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
```

Then restart the server. Emails will be printed to the terminal instead of sent.
