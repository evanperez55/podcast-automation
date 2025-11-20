"""Extract episode summaries from all analysis.json files."""

import json
from pathlib import Path
import re


def extract_episode_number(filename):
    """Extract episode number from filename."""
    match = re.search(r'Episode #(\d+)', filename)
    if match:
        return int(match.group(1))
    return None


def extract_episode_summaries():
    """Extract summaries from all episode analysis files."""
    print("="*60)
    print("EXTRACTING EPISODE SUMMARIES")
    print("="*60)

    output_dir = Path('output')
    episodes = []

    # Find all analysis.json files
    analysis_files = list(output_dir.glob('ep_*/Episode*_analysis.json'))
    print(f"[INFO] Found {len(analysis_files)} analysis files")

    for analysis_file in sorted(analysis_files):
        try:
            # Extract episode number
            ep_num = extract_episode_number(analysis_file.name)
            if ep_num is None:
                print(f"[WARNING] Could not extract episode number from {analysis_file.name}")
                continue

            # Only process episodes 1-24 as requested
            if ep_num > 24:
                continue

            # Read analysis file
            with open(analysis_file, 'r', encoding='utf-8') as f:
                analysis_data = json.load(f)

            # Extract relevant data
            episode_info = {
                'episode_number': ep_num,
                'file_name': analysis_file.name,
                'episode_summary': analysis_data.get('episode_summary', ''),
                'best_clips': []
            }

            # Extract clip information
            for clip in analysis_data.get('best_clips', []):
                episode_info['best_clips'].append({
                    'title': clip.get('suggested_title', ''),
                    'description': clip.get('description', ''),
                    'why_interesting': clip.get('why_interesting', ''),
                    'duration': clip.get('duration_seconds', 0)
                })

            # Also get social captions for more context
            social_captions = analysis_data.get('social_captions', {})
            episode_info['youtube_description'] = social_captions.get('youtube', '')

            episodes.append(episode_info)
            print(f"[OK] Episode {ep_num}: {len(episode_info['best_clips'])} clips")

        except Exception as e:
            print(f"[ERROR] Failed to process {analysis_file.name}: {e}")
            continue

    # Sort by episode number
    episodes.sort(key=lambda x: x['episode_number'])

    # Save to JSON
    output_path = Path('topic_data/episode_summaries.json')
    output_path.parent.mkdir(exist_ok=True)

    output_data = {
        'total_episodes': len(episodes),
        'episode_range': f"1-{max(ep['episode_number'] for ep in episodes) if episodes else 0}",
        'episodes': episodes
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"\n[OK] Saved to {output_path}")
    print(f"[OK] Total episodes processed: {len(episodes)}")

    # Show summary
    print("\n[SUMMARY] Episodes processed:")
    for ep in episodes:
        print(f"  Episode {ep['episode_number']}: {ep['episode_summary'][:60]}...")

    print("\n" + "="*60)
    return output_data


if __name__ == '__main__':
    extract_episode_summaries()
