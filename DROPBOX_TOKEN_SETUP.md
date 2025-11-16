# Dropbox OAuth Setup - Never Manually Refresh Tokens Again!

## The Problem

Dropbox short-lived access tokens expire after **4 hours**. This means you have to manually regenerate a new token every time you want to run your podcast automation. This is annoying and interrupts your workflow.

## The Solution

Use **OAuth 2.0 with Refresh Tokens** - this gives you a token that **never expires** and automatically generates new access tokens as needed.

## Quick Setup (5 minutes)

### Step 1: Run the Setup Script

```bash
python setup_dropbox_oauth.py
```

The script will guide you through the entire process interactively.

### Step 2: Create/Configure Your Dropbox App

When prompted, you'll need to:

1. Go to https://www.dropbox.com/developers/apps
2. Click **"Create app"**
3. Choose:
   - **API**: Scoped access
   - **Access**: Full Dropbox
   - **Name**: Something like "Podcast Automation" or "Fake Problems Automation"
4. Click **"Create app"**

### Step 3: Set Permissions

**IMPORTANT**: After creating the app, you MUST set permissions:

1. Go to the **"Permissions"** tab
2. Enable these permissions:
   - `files.metadata.write`
   - `files.metadata.read`
   - `files.content.write`
   - `files.content.read`
   - `sharing.write`
   - `sharing.read`
3. Click **"Submit"** at the bottom of the page
   - ⚠️ **Don't skip this!** The authorization will fail if you don't submit permissions.

### Step 4: Get Your Credentials

1. Go back to the **"Settings"** tab
2. Copy your **App key**
3. Copy your **App secret**
4. Enter both when the setup script asks for them

### Step 5: Authorize the App

The setup script will:

1. Give you an authorization URL
2. Open this URL in your browser
3. Click **"Allow"** to authorize the app
4. Copy the authorization code from the page
5. Paste it back into the script

### Step 6: Done!

The script will automatically:

- ✅ Save your credentials to `.env`
- ✅ Generate a refresh token that never expires
- ✅ Test the connection
- ✅ Update your configuration

## What Gets Added to Your .env File

The setup script adds these lines to your `.env`:

```bash
DROPBOX_APP_KEY=your_app_key_here
DROPBOX_APP_SECRET=your_app_secret_here
DROPBOX_REFRESH_TOKEN=your_refresh_token_here
```

Your old `DROPBOX_ACCESS_TOKEN` will be commented out (no longer needed).

## How It Works

When you run any automation script:

1. The system checks if you have `DROPBOX_REFRESH_TOKEN` set
2. If yes, it uses that to automatically generate fresh access tokens
3. If no, it falls back to the old `DROPBOX_ACCESS_TOKEN` (with 4-hour expiry)

The refresh token **never expires**, so you'll never have to manually refresh again!

## Verification

After setup, you should see this when running scripts:

```
[OK] Connected to Dropbox (using auto-refresh token)
```

Instead of:

```
[OK] Connected to Dropbox (using short-lived token)
[INFO] Consider setting up OAuth refresh token with: python setup_dropbox_oauth.py
```

## Troubleshooting

### "Authorization failed" or "Invalid permissions"

- Make sure you enabled the permissions in Step 3
- Make sure you clicked **"Submit"** after selecting permissions
- Try generating a new authorization code

### "App key or secret invalid"

- Double-check you copied the App Key and App Secret correctly
- Make sure you're using the credentials from the "Settings" tab

### "Token already exists in .env"

- This is fine! The script will update the existing values
- Your old access token will be preserved as a comment

## Benefits

✅ **Never expires** - Set it once, use it forever
✅ **Automatic refresh** - Tokens are generated on-demand
✅ **Secure** - Uses OAuth 2.0 best practices
✅ **Zero maintenance** - No more manual token regeneration
✅ **Backwards compatible** - Falls back to old tokens if not configured

## Need Help?

If you encounter issues:

1. Check the Dropbox app permissions are enabled and submitted
2. Make sure you copied the App Key and Secret correctly
3. Try deleting the app and starting fresh
4. Run `python setup_dropbox_oauth.py` again

---

**Pro Tip**: Once this is set up, you can run your automation scripts 24/7 without ever worrying about expired tokens!
