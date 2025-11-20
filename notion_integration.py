"""Notion API integration for Fake Problems Podcast topic management."""

import os
import json
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path
import requests
from dotenv import load_dotenv

load_dotenv()


class NotionTopicManager:
    """Manage podcast topics in Notion database."""

    def __init__(self):
        """Initialize Notion API client."""
        self.api_key = os.getenv('NOTION_API_KEY')
        self.database_id = os.getenv('NOTION_DATABASE_ID')

        if not self.api_key:
            raise ValueError(
                "NOTION_API_KEY not found in .env\n"
                "Get your key from: https://www.notion.so/my-integrations"
            )

        if not self.database_id:
            raise ValueError(
                "NOTION_DATABASE_ID not found in .env\n"
                "Create a database and share it with your integration"
            )

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }

        self.base_url = "https://api.notion.com/v1"

        print("[OK] Notion API initialized")

    def create_topic(self, topic_data: Dict) -> Dict:
        """
        Create a new topic in Notion database.

        Args:
            topic_data: Dictionary with topic information
                {
                    'topic': str (required),
                    'score': float (optional),
                    'category': str (optional),
                    'status': str (optional, default: 'Backlog'),
                    'source': str (optional),
                    'added_by': str (optional),
                    'url': str (optional),
                    'notes': str (optional),
                    'episode_number': int (optional)
                }

        Returns:
            Created page object from Notion API
        """
        # Build properties
        properties = {
            "Topic": {
                "title": [
                    {
                        "text": {
                            "content": topic_data['topic']
                        }
                    }
                ]
            }
        }

        # Add score if provided
        if 'score' in topic_data and topic_data['score'] is not None:
            properties["Score"] = {
                "number": float(topic_data['score'])
            }

        # Add category if provided
        if 'category' in topic_data and topic_data['category']:
            properties["Category"] = {
                "select": {
                    "name": topic_data['category']
                }
            }

        # Add status (default: Backlog)
        status = topic_data.get('status', 'Backlog')
        properties["Status"] = {
            "select": {
                "name": status
            }
        }

        # Add source if provided
        if 'source' in topic_data and topic_data['source']:
            properties["Source"] = {
                "rich_text": [
                    {
                        "text": {
                            "content": topic_data['source']
                        }
                    }
                ]
            }

        # Add URL if provided
        if 'url' in topic_data and topic_data['url']:
            properties["URL"] = {
                "url": topic_data['url']
            }

        # Add episode number if provided
        if 'episode_number' in topic_data and topic_data['episode_number']:
            properties["Episode"] = {
                "number": int(topic_data['episode_number'])
            }

        # Add notes in page content if provided
        children = []
        if 'notes' in topic_data and topic_data['notes']:
            children.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": topic_data['notes']
                            }
                        }
                    ]
                }
            })

        # Create page in database
        url = f"{self.base_url}/pages"
        data = {
            "parent": {"database_id": self.database_id},
            "properties": properties
        }

        if children:
            data["children"] = children

        response = requests.post(url, headers=self.headers, json=data)
        response.raise_for_status()

        return response.json()

    def bulk_create_topics(self, topics: List[Dict]) -> List[Dict]:
        """
        Create multiple topics in Notion.

        Args:
            topics: List of topic dictionaries

        Returns:
            List of created page objects
        """
        created = []
        total = len(topics)

        print(f"[INFO] Creating {total} topics in Notion...")

        for i, topic in enumerate(topics, 1):
            try:
                result = self.create_topic(topic)
                created.append(result)

                if i % 10 == 0:
                    print(f"[INFO] Created {i}/{total} topics...")

            except Exception as e:
                print(f"[ERROR] Failed to create topic: {topic.get('topic', 'Unknown')}")
                print(f"  Error: {e}")

        print(f"[OK] Created {len(created)}/{total} topics")
        return created

    def query_database(
        self,
        filter_params: Optional[Dict] = None,
        sorts: Optional[List[Dict]] = None
    ) -> List[Dict]:
        """
        Query topics from Notion database.

        Args:
            filter_params: Notion filter object
            sorts: List of sort objects

        Returns:
            List of page objects
        """
        url = f"{self.base_url}/databases/{self.database_id}/query"

        data = {}
        if filter_params:
            data["filter"] = filter_params
        if sorts:
            data["sorts"] = sorts

        response = requests.post(url, headers=self.headers, json=data)
        response.raise_for_status()

        return response.json().get('results', [])

    def get_topics_by_status(self, status: str) -> List[Dict]:
        """Get all topics with specific status."""
        filter_params = {
            "property": "Status",
            "select": {
                "equals": status
            }
        }

        return self.query_database(filter_params)

    def update_topic_status(self, page_id: str, new_status: str) -> Dict:
        """Update status of a topic."""
        url = f"{self.base_url}/pages/{page_id}"

        data = {
            "properties": {
                "Status": {
                    "select": {
                        "name": new_status
                    }
                }
            }
        }

        response = requests.patch(url, headers=self.headers, json=data)
        response.raise_for_status()

        return response.json()

    def mark_topic_as_discussed(
        self,
        page_id: str,
        episode_number: int
    ) -> Dict:
        """Mark a topic as discussed in an episode."""
        url = f"{self.base_url}/pages/{page_id}"

        data = {
            "properties": {
                "Status": {
                    "select": {
                        "name": "Published"
                    }
                },
                "Episode": {
                    "number": episode_number
                }
            }
        }

        response = requests.patch(url, headers=self.headers, json=data)
        response.raise_for_status()

        return response.json()


def migrate_google_doc_topics_to_notion():
    """Migrate all topics from Google Doc analysis to Notion."""
    print("="*60)
    print("MIGRATING GOOGLE DOC TOPICS TO NOTION")
    print("="*60)
    print()

    # Load topic matching analysis
    analysis_file = Path('topic_data/topic_matching_analysis.json')
    if not analysis_file.exists():
        print("[ERROR] Topic analysis file not found")
        print("Run topic matching analysis first")
        return

    with open(analysis_file, 'r', encoding='utf-8') as f:
        analysis = json.load(f)

    topics_data = analysis.get('topics', [])
    print(f"[INFO] Found {len(topics_data)} topics to migrate")
    print()

    # Initialize Notion manager
    try:
        notion = NotionTopicManager()
    except ValueError as e:
        print(f"[ERROR] {e}")
        return

    # Convert to Notion format
    notion_topics = []
    for topic in topics_data:
        notion_topic = {
            'topic': topic['topic_text'],
            'status': topic['status_for_notion'],
            'source': 'Google Doc Migration',
            'notes': f"Original ID: {topic['topic_id']}"
        }

        # Add episode if discussed
        if topic['discussed'] and topic['episodes']:
            notion_topic['episode_number'] = topic['episodes'][0]

        # Add confidence as note if matched
        if topic['discussed']:
            notion_topic['notes'] += f"\nMatched with {topic['confidence']*100:.0f}% confidence"
            notion_topic['notes'] += f"\nReason: {topic['reason']}"

        notion_topics.append(notion_topic)

    # Create in batches
    print(f"[INFO] Creating {len(notion_topics)} topics in Notion...")
    print("[WARNING] This may take several minutes...")
    print()

    created = notion.bulk_create_topics(notion_topics)

    print()
    print("="*60)
    print("[SUCCESS] MIGRATION COMPLETE")
    print("="*60)
    print(f"Topics created: {len(created)}/{len(notion_topics)}")
    print()
    print("Next steps:")
    print("1. Open your Notion database")
    print("2. Review imported topics")
    print("3. Add any manual topics")
    print("4. Start planning your next episode!")
    print()


if __name__ == '__main__':
    migrate_google_doc_topics_to_notion()
