# YouTube Token Management - How It Works

## Token Types

### Access Token (Short-lived)
- **Lifetime**: 1 hour
- **Purpose**: Used for actual API calls
- **Auto-refresh**: Yes, handled automatically by the code

### Refresh Token (Long-lived)
- **Lifetime**: Indefinite (until manually revoked)
- **Purpose**: Used to get new access tokens
- **Storage**: Saved in `credentials/youtube_token.pickle`

## How Auto-Refresh Works

1. **Initial Setup** (once)
   - Run `python setup_youtube_auth.py`
   - Browser opens, you authorize the app
   - You get both access token + refresh token
   - Both saved to `youtube_token.pickle`

2. **Normal Operation** (automatic)
   - Script loads saved credentials
   - If access token expired (after 1 hour), automatically uses refresh token to get new one
   - You never have to re-authenticate manually
   - This happens silently in the background

3. **When Re-auth is Needed** (rare)
   - Refresh token was revoked (you revoked access in Google account settings)
   - Token hasn't been used in 6+ months (Google expires inactive tokens)
   - OAuth consent screen configuration changed
   - **Just run setup script again to get new tokens**

## Updated Code Improvements

The YouTube uploader now has **better error handling**:

```python
# Old behavior: Crashed on refresh failure
if creds.expired and creds.refresh_token:
    creds.refresh(Request())  # Would crash if refresh token invalid

# New behavior: Auto-recovers by re-authenticating
if creds.expired and creds.refresh_token:
    try:
        creds.refresh(Request())  # Try to refresh
    except:
        # If refresh fails, trigger OAuth flow to get new tokens
        creds = None
```

## Best Practices

### To Prevent Expiration:
1. ✅ Run your automation at least once every 6 months
2. ✅ Don't revoke access in Google Account settings
3. ✅ Keep the same OAuth client credentials

### When Tokens Expire:
1. Run: `python setup_youtube_auth.py`
2. Authorize in browser (one time)
3. Done! Auto-refresh resumes

## Token Lifecycle Example

```
Day 1:     Authenticate → Get access token (1hr) + refresh token (∞)
Day 1+1h:  Access expires → Auto-refresh using refresh token → Get new access (1hr)
Day 1+2h:  Access expires → Auto-refresh → Get new access (1hr)
Day 1+3h:  Access expires → Auto-refresh → Get new access (1hr)
...continues indefinitely...

Day 180:   Refresh token still valid → Auto-refresh continues
Day 365:   Refresh token still valid → Auto-refresh continues

Only if:   User revokes access OR Google expires due to inactivity
Then:      Need to re-run setup_youtube_auth.py (one-time)
```

## Summary

**After initial setup, you should NEVER need to re-authenticate** unless:
- You manually revoke access
- You don't use the automation for 6+ months
- OAuth credentials change in Google Cloud

The system is designed to **just work** forever with automatic token refresh!
