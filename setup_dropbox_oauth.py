"""
Set up Dropbox OAuth 2.0 with refresh tokens for permanent access.

This script helps you obtain a long-lived refresh token that can automatically
generate new access tokens without manual intervention.
"""

import dropbox
from dropbox import DropboxOAuth2FlowNoRedirect
import os
from pathlib import Path


def setup_dropbox_oauth():
    """
    Interactive setup for Dropbox OAuth with refresh tokens.

    This will guide you through:
    1. Creating an app in Dropbox (if needed)
    2. Getting your App Key and App Secret
    3. Generating a refresh token that never expires
    """

    print("="*60)
    print("DROPBOX OAUTH SETUP - PERMANENT TOKEN REFRESH")
    print("="*60)
    print()
    print("This setup will give you a refresh token that automatically")
    print("generates new access tokens, so you never have to manually")
    print("refresh again!")
    print()

    # Step 1: Get App Key and Secret
    print("STEP 1: Get Your Dropbox App Credentials")
    print("-" * 60)
    print()
    print("1. Go to: https://www.dropbox.com/developers/apps")
    print("2. Click 'Create app'")
    print("3. Choose:")
    print("   - API: Scoped access")
    print("   - Access: Full Dropbox")
    print("   - Name: Something like 'Podcast Automation'")
    print("4. After creating, go to the 'Permissions' tab and enable:")
    print("   - files.metadata.write")
    print("   - files.metadata.read")
    print("   - files.content.write")
    print("   - files.content.read")
    print("   - sharing.write")
    print("   - sharing.read")
    print("5. Click 'Submit' at the bottom of the permissions page")
    print("6. Go back to the 'Settings' tab")
    print()

    app_key = input("Enter your App key: ").strip()
    app_secret = input("Enter your App secret: ").strip()

    if not app_key or not app_secret:
        print("[ERROR] App key and secret are required!")
        return

    print()
    print("STEP 2: Authorize the App")
    print("-" * 60)

    # Create OAuth flow
    auth_flow = DropboxOAuth2FlowNoRedirect(
        app_key,
        app_secret,
        token_access_type='offline'  # This requests a refresh token
    )

    # Get authorization URL
    authorize_url = auth_flow.start()

    print()
    print("1. Open this URL in your browser:")
    print()
    print(f"   {authorize_url}")
    print()
    print("2. Click 'Allow' to authorize the app")
    print("3. Copy the authorization code from the page")
    print()

    auth_code = input("Enter the authorization code: ").strip()

    if not auth_code:
        print("[ERROR] Authorization code is required!")
        return

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
        print("Next steps:")
        print("1. The DropboxHandler has been updated to use refresh tokens")
        print("2. You can now run your automation without manual token refresh")
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

    except Exception as e:
        print()
        print(f"[ERROR] Failed to complete authorization: {e}")
        print()
        print("Common issues:")
        print("- Make sure you enabled the required permissions in the Dropbox app settings")
        print("- Make sure you clicked 'Submit' after selecting permissions")
        print("- Try generating a new authorization code")
        return


if __name__ == '__main__':
    try:
        setup_dropbox_oauth()
    except KeyboardInterrupt:
        print("\n[WARNING] Setup cancelled by user")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
