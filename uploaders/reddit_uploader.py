"""Reddit uploader for podcast episode announcements."""

import praw
from typing import Optional, Dict, Any, List

from config import Config
from logger import logger
from retry_utils import retry_with_backoff


class RedditUploader:
    """Handle Reddit posts for podcast promotion."""

    def __init__(self):
        """Initialize Reddit uploader via PRAW."""
        self.client_id = Config.REDDIT_CLIENT_ID
        self.client_secret = Config.REDDIT_CLIENT_SECRET
        self.username = Config.REDDIT_USERNAME
        self.password = Config.REDDIT_PASSWORD
        self.user_agent = Config.REDDIT_USER_AGENT

        if not all([self.client_id, self.client_secret, self.username, self.password]):
            raise ValueError(
                "Reddit API credentials not configured in .env file.\n"
                "Setup instructions:\n"
                "1. Go to https://www.reddit.com/prefs/apps\n"
                "2. Create a 'script' app\n"
                "3. Add to .env:\n"
                "   - REDDIT_CLIENT_ID=your_client_id\n"
                "   - REDDIT_CLIENT_SECRET=your_client_secret\n"
                "   - REDDIT_USERNAME=your_username\n"
                "   - REDDIT_PASSWORD=your_password"
            )

        self.reddit = praw.Reddit(
            client_id=self.client_id,
            client_secret=self.client_secret,
            username=self.username,
            password=self.password,
            user_agent=self.user_agent,
        )

    @retry_with_backoff(
        max_retries=3,
        base_delay=2.0,
        retryable_exceptions=(ConnectionError, TimeoutError, OSError),
    )
    def post_link(
        self,
        subreddit: str,
        title: str,
        url: str,
        flair_text: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Post a link to a subreddit.

        Args:
            subreddit: Subreddit name (without r/)
            title: Post title (max 300 characters)
            url: URL to share
            flair_text: Optional flair text

        Returns:
            Dictionary with post info, or None if failed
        """
        try:
            logger.info("Posting to r/%s", subreddit)
            logger.info("Title: %s", title[:100])

            sub = self.reddit.subreddit(subreddit)
            submission = sub.submit(
                title=title[:300],
                url=url,
                flair_text=flair_text,
            )

            post_url = f"https://www.reddit.com{submission.permalink}"
            logger.info("Reddit post successful!")
            logger.info("Post URL: %s", post_url)

            return {
                "post_id": submission.id,
                "post_url": post_url,
                "subreddit": subreddit,
                "title": title,
                "status": "success",
            }

        except praw.exceptions.RedditAPIException as e:
            logger.error("Reddit API error in r/%s: %s", subreddit, e)
            return None
        except Exception as e:
            logger.error("Failed to post to r/%s: %s", subreddit, e)
            return None

    @retry_with_backoff(
        max_retries=3,
        base_delay=2.0,
        retryable_exceptions=(ConnectionError, TimeoutError, OSError),
    )
    def post_text(
        self,
        subreddit: str,
        title: str,
        body: str,
        flair_text: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Post a text/self post to a subreddit.

        Args:
            subreddit: Subreddit name (without r/)
            title: Post title (max 300 characters)
            body: Post body text (markdown supported)
            flair_text: Optional flair text

        Returns:
            Dictionary with post info, or None if failed
        """
        try:
            logger.info("Posting text to r/%s", subreddit)
            logger.info("Title: %s", title[:100])

            sub = self.reddit.subreddit(subreddit)
            submission = sub.submit(
                title=title[:300],
                selftext=body,
                flair_text=flair_text,
            )

            post_url = f"https://www.reddit.com{submission.permalink}"
            logger.info("Reddit text post successful!")
            logger.info("Post URL: %s", post_url)

            return {
                "post_id": submission.id,
                "post_url": post_url,
                "subreddit": subreddit,
                "title": title,
                "status": "success",
            }

        except praw.exceptions.RedditAPIException as e:
            logger.error("Reddit API error in r/%s: %s", subreddit, e)
            return None
        except Exception as e:
            logger.error("Failed to post to r/%s: %s", subreddit, e)
            return None

    def post_episode_announcement(
        self,
        episode_number: int,
        episode_summary: str,
        youtube_url: Optional[str] = None,
        subreddits: Optional[List[str]] = None,
        episode_title: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Post episode announcement to configured subreddits.

        Args:
            episode_number: Episode number
            episode_summary: Summary from AI analysis
            youtube_url: Optional YouTube URL for full episode
            subreddits: Optional list of subreddits to post to
            episode_title: Optional episode title

        Returns:
            List of post results (one per subreddit)
        """
        if not subreddits:
            subreddits = Config.REDDIT_SUBREDDITS

        if not subreddits:
            logger.warning("No subreddits configured for Reddit posting")
            return []

        title = (
            f"{Config.PODCAST_NAME} Episode {episode_number} - {episode_title}"
            if episode_title
            else f"{Config.PODCAST_NAME} - Episode {episode_number}"
        )

        results = []
        for subreddit in subreddits:
            if youtube_url:
                result = self.post_link(
                    subreddit=subreddit,
                    title=title,
                    url=youtube_url,
                )
            else:
                body = f"{episode_summary}\n\n"
                body += f"Episode {episode_number} of {Config.PODCAST_NAME}"
                result = self.post_text(
                    subreddit=subreddit,
                    title=title,
                    body=body,
                )

            if result:
                results.append(result)

        return results


def create_reddit_caption(
    episode_number: int,
    episode_title: str,
    episode_summary: str,
    youtube_url: Optional[str] = None,
) -> str:
    """
    Create a Reddit post body for an episode.

    Args:
        episode_number: Episode number
        episode_title: Episode title
        episode_summary: Episode summary
        youtube_url: Optional YouTube URL

    Returns:
        Formatted post body (markdown)
    """
    body = f"# Episode {episode_number}: {episode_title}\n\n"
    body += f"{episode_summary}\n\n"
    if youtube_url:
        body += f"**Watch/Listen:** {youtube_url}\n\n"
    body += "---\n*What did you think? Drop your thoughts below!*"
    return body
