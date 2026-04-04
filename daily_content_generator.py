"""Daily 'Fake Problem of the Day' social media content generator."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from config import Config
from logger import logger
from ollama_client import OllamaClient


class DailyContentGenerator:
    """Generates platform-specific 'Fake Problem of the Day' social media posts."""

    def __init__(self):
        """Initialize with self.enabled gated by DAILY_CONTENT_ENABLED env var.

        Uses OpenAI when OPENAI_API_KEY is set and Ollama is unavailable
        (e.g., in CI/GitHub Actions). Falls back to Ollama for local use.
        """
        self.enabled = os.getenv("DAILY_CONTENT_ENABLED", "true").lower() == "true"
        self.use_openai = (
            bool(Config.OPENAI_API_KEY)
            and os.getenv("DAILY_CONTENT_USE_OPENAI", "false").lower() == "true"
        )
        if self.use_openai:
            import openai

            self.openai_client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)
            self.ollama = None
        else:
            self.ollama = OllamaClient(model=Config.OLLAMA_MODEL)
            self.openai_client = None
        self.topic_data_dir = Path("topic_data")

    def generate_fake_problem(self, topic_hint: Optional[str] = None) -> dict:
        """Generate platform-specific fake problem content.

        Args:
            topic_hint: Optional topic to inspire the fake problem.

        Returns:
            Dict with keys 'twitter', 'instagram', 'tiktok', or empty dict
            if disabled.
        """
        if not self.enabled:
            logger.warning("Daily content generator disabled")
            return {}

        topic_context = ""
        if topic_hint:
            topic_context = f"\nUse this topic as loose inspiration (don't copy it directly): {topic_hint}"
        elif self.topic_data_dir.exists():
            topic_context = self._load_topic_inspiration()

        prompt = self._build_prompt(topic_context)

        try:
            response = self._call_llm(prompt)
            return self._parse_response(response)
        except Exception as e:
            logger.warning("Failed to generate daily content: %s", e)
            return {}

    def _call_llm(self, prompt: str) -> str:
        """Call LLM backend (OpenAI or Ollama).

        Args:
            prompt: System prompt for content generation.

        Returns:
            Raw response text from the LLM.
        """
        user_msg = "Generate a Fake Problem of the Day with platform-specific versions. Return ONLY valid JSON."
        if self.use_openai and self.openai_client:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                temperature=0.9,
                max_tokens=500,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": user_msg},
                ],
            )
            return response.choices[0].message.content
        return self.ollama.chat(
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.9,
            max_tokens=500,
        )

    def generate_and_save(self, output_dir: Optional[Path] = None) -> Optional[Path]:
        """Generate fake problem content and save to a JSON file.

        Args:
            output_dir: Directory to save output. Defaults to Config.OUTPUT_DIR.

        Returns:
            Path to saved JSON file, or None on failure.
        """
        if not self.enabled:
            logger.warning("Daily content generator disabled")
            return None

        content = self.generate_fake_problem()
        if not content:
            return None

        if output_dir is None:
            output_dir = Path(Config.OUTPUT_DIR) / "daily_content"
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = output_dir / f"fake_problem_{timestamp}.json"

        payload = {
            "generated_at": datetime.now().isoformat(),
            "content": content,
        }

        output_path.write_text(json.dumps(payload, indent=2))
        logger.info("Daily content saved to %s", output_path)
        return output_path

    def _build_prompt(self, topic_context: str) -> str:
        """Build the system prompt for the LLM.

        Args:
            topic_context: Optional context string about topics.

        Returns:
            System prompt string.
        """
        podcast_name = Config.PODCAST_NAME
        return f"""You are a comedy writer for {podcast_name}. Your style is dry, observational humor about relatable everyday absurdity.

Examples of the tone:
- "Fake Problem: My ice cream melted before I finished my existential crisis"
- "Fake Problem: I can't find a parking spot at the gym so I guess I'll stay unhealthy"
- "Fake Problem: I have too many streaming services to ever feel bored but I'm still bored"
{topic_context}

Generate ONE fake problem and format it for three platforms. Return ONLY a JSON object with these exact keys:

- "twitter": The fake problem observation. Under 280 characters. Dry humor, no hashtags, no emojis.
- "instagram": The same core joke but add 1-2 emojis and end with #fakeproblems
- "tiktok": A punchy hook version under 150 characters, designed to make someone stop scrolling.

Return raw JSON only. No markdown, no code fences, no explanation."""

    def _parse_response(self, response: str) -> dict:
        """Parse the LLM response into a content dict.

        Args:
            response: Raw LLM response string.

        Returns:
            Dict with twitter/instagram/tiktok keys, or empty dict on parse failure.
        """
        cleaned = response.strip()
        # Strip markdown code fences if present
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            lines = [line for line in lines if not line.strip().startswith("```")]
            cleaned = "\n".join(lines)

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("Failed to parse LLM response as JSON: %s", cleaned[:200])
            return {}

        expected_keys = {"twitter", "instagram", "tiktok"}
        if not expected_keys.issubset(data.keys()):
            missing = expected_keys - set(data.keys())
            logger.warning("LLM response missing keys: %s", missing)
            return {}

        return {
            "twitter": str(data["twitter"]),
            "instagram": str(data["instagram"]),
            "tiktok": str(data["tiktok"]),
        }

    def _load_topic_inspiration(self) -> str:
        """Load a random topic from the latest scored_topics file.

        Returns:
            Topic context string, or empty string if no topics found.
        """
        scored_files = sorted(self.topic_data_dir.glob("scored_topics_*.json"))
        if not scored_files:
            return ""

        latest_file = scored_files[-1]
        try:
            data = json.loads(latest_file.read_text())
            topics_by_cat = data.get("topics_by_category", {})
            # Grab the first recommended topic we find
            for topics in topics_by_cat.values():
                for topic in topics:
                    score = topic.get("score", {})
                    if score.get("recommended", False):
                        title = topic.get("title", "")
                        return f"\nUse this topic as loose inspiration (don't copy it directly): {title}"
        except Exception as e:
            logger.warning("Failed to load topic inspiration: %s", e)

        return ""
