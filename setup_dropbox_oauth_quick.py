"""
Quick Dropbox OAuth setup with command-line arguments.
Usage: python setup_dropbox_oauth_quick.py <app_key> <app_secret>
"""

import dropbox
from dropbox import DropboxOAuth2FlowNoRedirect
import sys
from pathlib import Path


def setup_dropbox_oauth(app_key, app_secret):
    """Set up Dropbox OAuth with the provided credentials."""

    print("="*60)
    print("DROPBOX OAUTH SETUP - PERMANENT TOKEN REFRESH")
    print("="*60)
    print()
    print(f"App Key: {app_key}")
    print(f"App Secret: {app_secret[:4]}...{app_secret[-4:]}")
    print()

    # Create OAuth flow
    auth_flow = DropboxOAuth2FlowNoRedirect(
        app_key,
        app_secret,
        token_access_type='offline'  # This requests a refresh token
    )

    # Get authorization URL
    authorize_url = auth_flow.start()

    print("STEP: Authorize the App")
    print("-" * 60)
    print()
    print("1. Open this URL in your browser:")
    print()
    print(f"   {authorize_url}")
    print()
    print("2. Click 'Allow' to authorize the app")
    print("3. Copy the authorization code from the page")
    print()
    print("Paste the authorization code here and press Enter...")
    print()

    # Return the auth_flow and URL so user can complete manually
    return auth_flow, authorize_url


def complete_oauth(auth_flow, app_key, app_secret, auth_code):
    """Complete the OAuth flow with the authorization code."""

    try:
        # Complete the authorization and get tokens
        oauth_result = auth_flow.finish(auth_code)

        print()
        print("="*60)
        print("SUCCESS! OAuth Setup Complete")
        print("="*60)
        print()

        # Save to .env file
        env_file = Path(".env")
        env_lines = []

        if env_file.exists():
            with open(env_file, 'r') as f:
                env_lines = f.readlines()

        # Update or add OAuth credentials
        updated_keys = set()
        new_lines = []

        for line in env_lines:
            if line.startswith('DROPBOX_APP_KEY='):
                new_lines.append(f'DROPBOX_APP_KEY={app_key}\n')
                updated_keys.add('DROPBOX_APP_KEY')
            elif line.startswith('DROPBOX_APP_SECRET='):
                new_lines.append(f'DROPBOX_APP_SECRET={app_secret}\n')
                updated_keys.add('DROPBOX_APP_SECRET')
            elif line.startswith('DROPBOX_REFRESH_TOKEN='):
                new_lines.append(f'DROPBOX_REFRESH_TOKEN={oauth_result.refresh_token}\n')
                updated_keys.add('DROPBOX_REFRESH_TOKEN')
            elif line.startswith('DROPBOX_ACCESS_TOKEN='):
                # Keep the old access token line but comment it out
                new_lines.append(f'# {line}')
                new_lines.append(f'# NOTE: Access token is now auto-generated from refresh token\n')
            else:
                new_lines.append(line)

        # Add missing keys
        if 'DROPBOX_APP_KEY' not in updated_keys:
            new_lines.append(f'\n# Dropbox OAuth Credentials\n')
            new_lines.append(f'DROPBOX_APP_KEY={app_key}\n')
        if 'DROPBOX_APP_SECRET' not in updated_keys:
            new_lines.append(f'DROPBOX_APP_SECRET={app_secret}\n')
        if 'DROPBOX_REFRESH_TOKEN' not in updated_keys:
            new_lines.append(f'DROPBOX_REFRESH_TOKEN={oauth_result.refresh_token}\n')

        # Write back to .env
        with open(env_file, 'w') as f:
            f.writelines(new_lines)

        print("[OK] Credentials saved to .env file")
        print()
        print("Your refresh token will never expire!")
        print("The system will automatically generate new access tokens as needed.")
        print()

        # Test the connection
        print("Testing connection with new credentials...")
        dbx = dropbox.Dropbox(
            app_key=app_key,
            app_secret=app_secret,
            oauth2_refresh_token=oauth_result.refresh_token
        )

        # Test by getting account info
        account = dbx.users_get_current_account()
        print(f"[OK] Successfully connected as: {account.name.display_name}")
        print()
        print("Setup complete! You can now run your automation scripts.")
        return True

    except Exception as e:
        print()
        print(f"[ERROR] Failed to complete authorization: {e}")
        print()
        print("Common issues:")
        print("- Make sure you enabled the required permissions in the Dropbox app settings")
        print("- Make sure you clicked 'Submit' after selecting permissions")
        print("- Try generating a new authorization code")
        return False


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python setup_dropbox_oauth_quick.py <app_key> <app_secret> [auth_code]")
        print()
        print("Example:")
        print("  Step 1: python setup_dropbox_oauth_quick.py nllyfhg1l322hzk c5r5993ae0u3b50")
        print("  Step 2: Open the URL, get the code, then:")
        print("  Step 3: python setup_dropbox_oauth_quick.py nllyfhg1l322hzk c5r5993ae0u3b50 YOUR_AUTH_CODE")
        sys.exit(1)

    app_key = sys.argv[1]
    app_secret = sys.argv[2]

    if len(sys.argv) >= 4:
        # Complete the OAuth with provided auth code
        auth_code = sys.argv[3]

        # Recreate the auth flow
        auth_flow = DropboxOAuth2FlowNoRedirect(
            app_key,
            app_secret,
            token_access_type='offline'
        )
        auth_flow.start()

        complete_oauth(auth_flow, app_key, app_secret, auth_code)
    else:
        # Just generate the URL
        auth_flow, authorize_url = setup_dropbox_oauth(app_key, app_secret)
        print()
        print("=" * 60)
        print("NEXT STEP:")
        print("=" * 60)
        print()
        print("After you get the authorization code, run:")
        print()
        print(f"python setup_dropbox_oauth_quick.py {app_key} {app_secret} YOUR_AUTH_CODE_HERE")
        print()
