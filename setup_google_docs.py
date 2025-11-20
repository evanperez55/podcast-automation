"""Setup script for Google Docs API authentication."""

import os
from pathlib import Path
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/documents']


def setup_google_docs():
    """Guide user through Google Docs API setup."""
    print("="*60)
    print("GOOGLE DOCS API SETUP")
    print("="*60)
    print()

    # Check if credentials file exists
    creds_path = Path('google_docs_credentials.json')

    if not creds_path.exists():
        print("[ERROR] google_docs_credentials.json not found!")
        print()
        print("Please follow these steps:")
        print()
        print("1. Go to https://console.cloud.google.com")
        print("2. Create a new project (or select existing)")
        print("3. Enable the Google Docs API:")
        print("   - Click 'Enable APIs and Services'")
        print("   - Search for 'Google Docs API'")
        print("   - Click 'Enable'")
        print()
        print("4. Create OAuth 2.0 credentials:")
        print("   - Go to 'Credentials' in the left sidebar")
        print("   - Click 'Create Credentials' > 'OAuth client ID'")
        print("   - Choose 'Desktop application'")
        print("   - Download the credentials JSON file")
        print()
        print("5. Save the downloaded file as:")
        print(f"   {creds_path.absolute()}")
        print()
        print("6. Run this script again")
        print()
        return False

    # Check if .env has GOOGLE_DOC_ID
    from dotenv import load_dotenv
    load_dotenv()

    doc_id = os.getenv('GOOGLE_DOC_ID')
    if not doc_id or doc_id == 'your_google_doc_id_here':
        print("[ERROR] GOOGLE_DOC_ID not configured in .env file!")
        print()
        print("Please add your Google Doc ID to the .env file:")
        print()
        print("1. Open your Google Doc with podcast topics")
        print("2. Copy the document ID from the URL:")
        print("   https://docs.google.com/document/d/YOUR_DOC_ID_HERE/edit")
        print()
        print("3. Add to .env file:")
        print("   GOOGLE_DOC_ID=YOUR_DOC_ID_HERE")
        print()
        return False

    print("[OK] Found credentials file")
    print("[OK] Found GOOGLE_DOC_ID in .env")
    print()

    # Run OAuth flow
    print("Starting OAuth authentication...")
    print("This will open a browser window for you to authorize access.")
    print()

    try:
        flow = InstalledAppFlow.from_client_secrets_file(
            str(creds_path), SCOPES
        )
        creds = flow.run_local_server(port=0)

        # Save credentials
        token_path = Path('google_docs_token.json')
        with open(token_path, 'w') as token:
            token.write(creds.to_json())

        print()
        print("[OK] Authentication successful!")
        print(f"[OK] Token saved to: {token_path}")
        print()

        # Test access to the document
        print("Testing access to your Google Doc...")
        service = build('docs', 'v1', credentials=creds)
        document = service.documents().get(documentId=doc_id).execute()

        print(f"[OK] Successfully connected to: {document.get('title', 'Unknown')}")
        print()
        print("="*60)
        print("SETUP COMPLETE!")
        print("="*60)
        print()
        print("Your podcast automation will now automatically:")
        print("  - Read topics from your Google Doc")
        print("  - Use Claude AI to match topics with episode transcripts")
        print("  - Move discussed topics to a 'Discussed Topics' section")
        print()
        print("Ready to use! Run your automation as normal.")
        print()

        return True

    except Exception as e:
        print()
        print(f"[ERROR] Authentication failed: {e}")
        print()
        print("Common issues:")
        print("  - Make sure your credentials file is correct")
        print("  - Ensure Google Docs API is enabled in your project")
        print("  - Check that you're using Desktop application credentials")
        print()
        return False


if __name__ == '__main__':
    setup_google_docs()
