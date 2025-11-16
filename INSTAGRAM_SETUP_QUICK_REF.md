# Instagram Setup - Quick Reference

Run: `python setup_instagram.py`

## What You'll Do:

### Step 1: Instagram Account (on phone)
- Settings → Account → Switch to Professional Account
- Choose Business or Creator
- Link to Facebook Page

### Step 2-3: Create Facebook App (browser opens)
- developers.facebook.com/apps/create
- Use case: Other
- App type: Business
- Name: Fake Problems Podcast
- Copy App ID and App Secret

### Step 4: Add Instagram API
- In app dashboard: Add Product → Instagram Graph API

### Step 5: Generate Token (browser opens)
- Graph API Explorer
- Select your app
- Generate Access Token
- Permissions: instagram_basic, instagram_content_publish, pages_read_engagement, pages_show_list
- Copy short-lived token

### Step 6: Exchange Token (browser opens automatically)
- Browser shows JSON with new access_token
- Copy the long-lived access_token

### Step 7: Get Page ID (browser opens)
- JSON shows your pages
- Find your page, copy its "id"

### Step 8: Get Instagram ID (browser opens)
- JSON shows instagram_business_account
- Copy the "id" value

### Step 9: Done!
- Script saves to .env
- Tests connection
- Instagram ready!

## Tips:
- Have your phone nearby for Step 1
- Copy/paste carefully (tokens are long!)
- Don't close browser tabs until done
- If stuck, the script will wait for you

Good luck!
