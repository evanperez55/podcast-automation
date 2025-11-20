"""Google Docs topic tracker for automatically marking discussed topics."""

import json
from typing import List, Dict, Tuple
from datetime import datetime
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from pathlib import Path
import anthropic
from config import Config

# Google Docs API scopes
SCOPES = ['https://www.googleapis.com/auth/documents']


class GoogleDocsTopicTracker:
    """Track and update discussed topics in a Google Doc."""

    def __init__(self):
        """Initialize Google Docs API client."""
        self.creds = None
        self.service = None
        self.anthropic_client = anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY)

        if not Config.GOOGLE_DOC_ID:
            raise ValueError(
                "GOOGLE_DOC_ID not configured in .env file\n"
                "Please add your Google Doc ID (from the URL)"
            )

        self.doc_id = Config.GOOGLE_DOC_ID
        self._authenticate()

    def _authenticate(self):
        """Authenticate with Google Docs API."""
        token_path = Path('google_docs_token.json')
        creds_path = Path('google_docs_credentials.json')

        # Load existing token if available
        if token_path.exists():
            self.creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

        # If credentials are invalid or don't exist, authenticate
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                if not creds_path.exists():
                    raise FileNotFoundError(
                        f"Google Docs credentials file not found: {creds_path}\n"
                        "Please download credentials from Google Cloud Console and save as google_docs_credentials.json"
                    )

                flow = InstalledAppFlow.from_client_secrets_file(
                    str(creds_path), SCOPES
                )
                self.creds = flow.run_local_server(port=0)

            # Save credentials for next time
            with open(token_path, 'w') as token:
                token.write(self.creds.to_json())

        # Build the service
        self.service = build('docs', 'v1', credentials=self.creds)
        print("[OK] Google Docs API authenticated")

    def get_document_content(self) -> Dict:
        """
        Fetch the Google Doc content.

        Returns:
            Document structure from Google Docs API
        """
        try:
            document = self.service.documents().get(documentId=self.doc_id).execute()
            return document
        except HttpError as error:
            print(f"[ERROR] Failed to fetch document: {error}")
            raise

    def extract_topics(self, document: Dict) -> List[Dict]:
        """
        Extract topics from the Google Doc.

        This looks for topics in the document that are NOT in the "Discussed Topics" section.

        Args:
            document: Document structure from Google Docs API

        Returns:
            List of topics with their positions in the document
        """
        topics = []
        discussed_section_start = None

        content = document.get('body', {}).get('content', [])

        for element in content:
            if 'paragraph' in element:
                paragraph = element['paragraph']
                elements = paragraph.get('elements', [])

                for para_element in elements:
                    if 'textRun' in para_element:
                        text = para_element['textRun'].get('content', '').strip()

                        # Check if this is the "Discussed Topics" header
                        if 'Discussed Topics' in text or 'DISCUSSED TOPICS' in text.upper():
                            discussed_section_start = element.get('startIndex', 0)
                            break

                        # If we have text and we're not in discussed section yet
                        if text and (discussed_section_start is None or
                                   element.get('startIndex', 0) < discussed_section_start):
                            # Skip empty lines, headers, etc.
                            if len(text) > 3 and not text.startswith('#'):
                                topics.append({
                                    'text': text,
                                    'start_index': element.get('startIndex', 0),
                                    'end_index': element.get('endIndex', 0)
                                })

        return topics

    def match_topics_with_transcript(
        self,
        topics: List[Dict],
        transcript_text: str,
        episode_summary: str,
        episode_number: int
    ) -> List[Dict]:
        """
        Use Claude AI to intelligently match topics with the transcript.

        Args:
            topics: List of topic dictionaries from the Google Doc
            transcript_text: Full transcript text
            episode_summary: Summary of the episode from Claude analysis
            episode_number: Episode number

        Returns:
            List of matched topics with confidence scores
        """
        if not topics:
            return []

        print(f"[INFO] Analyzing {len(topics)} topics against transcript...")

        # Build topic list for Claude
        topic_list = "\n".join([f"{i+1}. {t['text']}" for i, t in enumerate(topics)])

        prompt = f"""You are analyzing a podcast transcript to identify which topics from a topic list were discussed in this episode.

**EPISODE INFORMATION:**
Episode #{episode_number}
Summary: {episode_summary}

**TOPICS TO CHECK:**
{topic_list}

**YOUR TASK:**
For each topic in the list above, determine if it was discussed in this episode based on the summary and transcript.

A topic is "discussed" if:
- The main subject matter matches (even if wording is different)
- A significant portion of conversation was about this topic
- The topic was a central theme or story in the episode

A topic is NOT discussed if:
- Only briefly mentioned in passing
- Used as a minor example or analogy
- Not actually covered despite similar keywords

**OUTPUT FORMAT:**
Return ONLY a JSON array with this exact structure:
[
  {{
    "topic_number": 1,
    "topic_text": "exact topic text from list",
    "discussed": true/false,
    "confidence": 0.0-1.0,
    "reason": "brief explanation why it was or wasn't discussed"
  }}
]

**TRANSCRIPT EXCERPT (first 3000 chars):**
{transcript_text[:3000]}

Remember: Return ONLY the JSON array, no other text."""

        try:
            response = self.anthropic_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                temperature=0.1,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            response_text = response.content[0].text.strip()

            # Extract JSON from response (in case Claude adds any extra text)
            if response_text.startswith('['):
                matches = json.loads(response_text)
            else:
                # Try to find JSON array in the response
                import re
                json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
                if json_match:
                    matches = json.loads(json_match.group(0))
                else:
                    print("[WARNING] Could not parse Claude's response")
                    return []

            # Filter for discussed topics with reasonable confidence
            discussed_topics = []
            for match in matches:
                if match.get('discussed', False) and match.get('confidence', 0) > 0.6:
                    topic_idx = match['topic_number'] - 1
                    if 0 <= topic_idx < len(topics):
                        topic = topics[topic_idx].copy()
                        topic['confidence'] = match['confidence']
                        topic['reason'] = match.get('reason', '')
                        discussed_topics.append(topic)

            print(f"[OK] Found {len(discussed_topics)} discussed topics")
            return discussed_topics

        except Exception as e:
            print(f"[ERROR] Topic matching failed: {e}")
            return []

    def move_topics_to_discussed_section(
        self,
        discussed_topics: List[Dict],
        episode_number: int
    ) -> bool:
        """
        Move discussed topics to the "Discussed Topics" section in the Google Doc.

        Args:
            discussed_topics: List of topics that were discussed
            episode_number: Episode number for annotation

        Returns:
            True if successful, False otherwise
        """
        if not discussed_topics:
            print("[INFO] No topics to move")
            return True

        try:
            # Get current document
            document = self.get_document_content()

            # Find or create "Discussed Topics" section
            discussed_section_index = self._find_discussed_section(document)

            requests = []

            # If no "Discussed Topics" section exists, create it
            if discussed_section_index is None:
                # Add section at the end of document
                doc_end_index = document.get('body', {}).get('content', [])[-1].get('endIndex', 1)

                requests.append({
                    'insertText': {
                        'location': {'index': doc_end_index - 1},
                        'text': '\n\n--- DISCUSSED TOPICS ---\n\n'
                    }
                })

                discussed_section_index = doc_end_index - 1 + len('\n\n--- DISCUSSED TOPICS ---\n\n')

            # Sort topics by their position in reverse (delete from bottom to top)
            # This prevents index shifting issues
            sorted_topics = sorted(discussed_topics, key=lambda t: t['start_index'], reverse=True)

            # For each discussed topic, delete from original position and add to discussed section
            date_str = datetime.now().strftime("%Y-%m-%d")

            for topic in sorted_topics:
                topic_text = topic['text']

                # Delete from original position
                requests.append({
                    'deleteContentRange': {
                        'range': {
                            'startIndex': topic['start_index'],
                            'endIndex': topic['end_index']
                        }
                    }
                })

            # Add all discussed topics to the discussed section
            # (Add them at the beginning of the discussed section)
            for topic in reversed(sorted_topics):  # Reverse to maintain order
                topic_text = topic['text']
                confidence = topic.get('confidence', 0)
                reason = topic.get('reason', '')

                new_topic_text = f"• {topic_text} - Episode {episode_number} ({date_str})\n"

                requests.append({
                    'insertText': {
                        'location': {'index': discussed_section_index},
                        'text': new_topic_text
                    }
                })

            # Execute all requests in batch
            if requests:
                self.service.documents().batchUpdate(
                    documentId=self.doc_id,
                    body={'requests': requests}
                ).execute()

                print(f"[OK] Moved {len(discussed_topics)} topics to 'Discussed Topics' section")
                return True

            return True

        except HttpError as error:
            print(f"[ERROR] Failed to update document: {error}")
            return False

    def _find_discussed_section(self, document: Dict) -> int:
        """
        Find the start index of the "Discussed Topics" section.

        Returns:
            Start index of section, or None if not found
        """
        content = document.get('body', {}).get('content', [])

        for element in content:
            if 'paragraph' in element:
                paragraph = element['paragraph']
                elements = paragraph.get('elements', [])

                for para_element in elements:
                    if 'textRun' in para_element:
                        text = para_element['textRun'].get('content', '').strip()

                        if 'DISCUSSED TOPICS' in text.upper() or '--- DISCUSSED TOPICS ---' in text:
                            # Return the index after this header
                            return element.get('endIndex', 0)

        return None

    def update_topics_for_episode(
        self,
        transcript_text: str,
        episode_summary: str,
        episode_number: int
    ) -> Dict:
        """
        Main method to update Google Doc with discussed topics.

        Args:
            transcript_text: Full transcript text
            episode_summary: Episode summary from Claude
            episode_number: Episode number

        Returns:
            Dictionary with update results
        """
        print("\n" + "="*60)
        print("UPDATING GOOGLE DOCS TOPIC TRACKER")
        print("="*60)

        try:
            # Fetch document
            print("[INFO] Fetching Google Doc...")
            document = self.get_document_content()

            # Extract topics
            print("[INFO] Extracting topics from document...")
            topics = self.extract_topics(document)
            print(f"[OK] Found {len(topics)} active topics")

            if not topics:
                print("[INFO] No topics found to check")
                return {
                    'success': True,
                    'topics_checked': 0,
                    'topics_moved': 0
                }

            # Match topics with transcript using Claude
            discussed_topics = self.match_topics_with_transcript(
                topics,
                transcript_text,
                episode_summary,
                episode_number
            )

            if not discussed_topics:
                print("[INFO] No topics matched this episode")
                return {
                    'success': True,
                    'topics_checked': len(topics),
                    'topics_moved': 0,
                    'discussed_topics': []
                }

            # Show what will be moved
            print(f"\n[INFO] Topics to move to 'Discussed' section:")
            for topic in discussed_topics:
                confidence_pct = int(topic['confidence'] * 100)
                print(f"  • {topic['text'][:60]}... ({confidence_pct}% confidence)")
                print(f"    Reason: {topic['reason']}")

            # Move topics to discussed section
            success = self.move_topics_to_discussed_section(
                discussed_topics,
                episode_number
            )

            print("="*60)

            return {
                'success': success,
                'topics_checked': len(topics),
                'topics_moved': len(discussed_topics),
                'discussed_topics': [t['text'] for t in discussed_topics]
            }

        except Exception as e:
            print(f"[ERROR] Topic tracker update failed: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }


def test_topic_tracker():
    """Test the Google Docs topic tracker."""
    try:
        tracker = GoogleDocsTopicTracker()

        # Test with fake data
        test_transcript = """
        Today we're talking about an interesting fake problem - what if you ate too much cheese?
        There's this crazy story about a guy who ate 6-9 pounds of cheese every day and started
        oozing cholesterol from his hands. It's absolutely disgusting but fascinating.
        """

        test_summary = "Discussion about extreme cheese consumption and its health consequences"

        result = tracker.update_topics_for_episode(
            transcript_text=test_transcript,
            episode_summary=test_summary,
            episode_number=999
        )

        print("\n[TEST RESULTS]")
        print(json.dumps(result, indent=2))

    except Exception as e:
        print(f"[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    test_topic_tracker()
