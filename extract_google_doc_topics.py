"""Extract all topics from Google Doc and save to JSON."""

import json
from pathlib import Path
from google_docs_tracker import GoogleDocsTopicTracker


def extract_google_doc_topics():
    """Extract all topics from the Google Doc."""
    print("="*60)
    print("EXTRACTING TOPICS FROM GOOGLE DOC")
    print("="*60)

    try:
        # Initialize tracker
        tracker = GoogleDocsTopicTracker()

        # Get document content
        print("[INFO] Fetching Google Doc...")
        document = tracker.get_document_content()

        # Extract topics
        print("[INFO] Extracting topics...")
        topics = tracker.extract_topics(document)

        print(f"[OK] Found {len(topics)} topics")

        # Convert to simpler format for JSON
        topics_list = []
        for i, topic in enumerate(topics):
            topics_list.append({
                'id': i + 1,
                'text': topic['text'],
                'start_index': topic['start_index'],
                'end_index': topic['end_index']
            })

        # Save to JSON
        output_path = Path('topic_data/google_doc_topics.json')
        output_path.parent.mkdir(exist_ok=True)

        output_data = {
            'total_topics': len(topics_list),
            'extracted_date': str(Path(__file__).stat().st_mtime),
            'topics': topics_list
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        print(f"[OK] Saved to {output_path}")
        print(f"[OK] Total topics extracted: {len(topics_list)}")

        # Show first 10 topics as preview
        print("\n[PREVIEW] First 10 topics:")
        for topic in topics_list[:10]:
            preview = topic['text'][:80] + "..." if len(topic['text']) > 80 else topic['text']
            print(f"  {topic['id']}. {preview}")

        print("\n" + "="*60)
        return output_data

    except Exception as e:
        print(f"[ERROR] Failed to extract topics: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == '__main__':
    extract_google_doc_topics()
