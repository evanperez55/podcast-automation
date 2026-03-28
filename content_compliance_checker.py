"""Content compliance checker — analyzes podcast transcripts against YouTube community guidelines."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import openai

from config import Config
from logger import logger


VIOLATION_CATEGORIES = [
    "hate_speech",
    "graphic_violence",
    "dangerous_misinformation",  # medical/health claims without scientific basis
    "harassment",
    "sexual_content",
    "self_harm_promotion",
]

SEVERITY_MAP = {
    "hate_speech": "critical",
    "graphic_violence": "warning",
    "dangerous_misinformation": "critical",
    "harassment": "warning",
    "sexual_content": "warning",
    "self_harm_promotion": "critical",
}

COMPLIANCE_PROMPT_TEMPLATE = """Analyze this podcast transcript for YouTube Community Guidelines violations.

YouTube prohibits:
- hate_speech: Dehumanizing content targeting protected groups (race, religion, gender, etc.)
- dangerous_misinformation: False medical/health claims that could cause real harm (e.g., "drinking bleach cures cancer")
- graphic_violence: Explicit descriptions of real violence or instructions for causing harm
- harassment: Targeted attacks or threats against real private individuals
- sexual_content: Explicit sexual descriptions
- self_harm_promotion: Encouraging suicide, self-harm, or eating disorders

TRANSCRIPT:
{transcript}

Return ONLY a JSON array. Each element:
{{
  "start_timestamp": "HH:MM:SS",
  "end_timestamp": "HH:MM:SS",
  "text": "exact quoted text",
  "category": "<one of the categories above>",
  "reason": "brief explanation"
}}

If no violations found, return an empty array: []

{context}
"""

_COMPLIANCE_CONTEXTS = {
    "permissive": (
        "Context: This is a comedy podcast. Dark humor, profanity, and edgy jokes are NOT "
        "violations unless they specifically dehumanize real protected groups or contain "
        "genuinely dangerous false health claims that could physically harm listeners."
    ),
    "strict": (
        "Context: This is a serious factual podcast. Apply community guidelines strictly. "
        "Flag any content that could be construed as harmful, misleading, or offensive to "
        "a general audience, even if it may have been intended as humor."
    ),
    "standard": (
        "Context: Apply standard YouTube community guidelines without additional leniency "
        "or strictness. Flag clear violations as defined above."
    ),
}


def _build_compliance_prompt(transcript: str) -> str:
    """Build a genre-aware compliance prompt for the given transcript.

    Reads COMPLIANCE_STYLE from Config (with default 'permissive' for backward compat).

    Args:
        transcript: Formatted transcript string to inject into the prompt.

    Returns:
        Complete prompt string ready to send to GPT-4o.
    """
    style = getattr(Config, "COMPLIANCE_STYLE", "permissive")
    context = _COMPLIANCE_CONTEXTS.get(style, _COMPLIANCE_CONTEXTS["permissive"])
    return COMPLIANCE_PROMPT_TEMPLATE.format(transcript=transcript, context=context)


class ContentComplianceChecker:
    """Analyze podcast transcripts for YouTube community guidelines violations using GPT-4o."""

    def __init__(self):
        """Initialize compliance checker with optional OpenAI client."""
        self.enabled = os.getenv("COMPLIANCE_ENABLED", "true").lower() == "true"
        if self.enabled:
            self.client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)
        logger.info(
            "Content compliance checker %s", "ready" if self.enabled else "disabled"
        )

    def check_transcript(
        self,
        transcript_data: dict,
        episode_output_dir,
        episode_number: int,
        timestamp: str | None = None,
    ) -> dict:
        """Analyze transcript for YouTube policy violations.

        Args:
            transcript_data: Transcript dict with 'segments' and 'words' lists.
            episode_output_dir: Directory to write the compliance report JSON.
            episode_number: Episode number (used in report filename).
            timestamp: Optional timestamp string for the report filename. If None,
                       uses current UTC time.

        Returns:
            dict with keys:
              - flagged: list of {start_seconds, end_seconds, text, category, severity, reason}
              - critical: bool (True if any "critical" severity item found)
              - report_path: str path to saved JSON report (or None if disabled)
        """
        if not self.enabled:
            return {"flagged": [], "critical": False, "report_path": None}

        if timestamp is None:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

        # Format transcript using segments for compact, timestamped representation
        formatted_transcript = self._format_transcript(transcript_data)

        # Build and send compliance prompt
        prompt = _build_compliance_prompt(formatted_transcript)

        logger.info(
            "Checking transcript for content compliance (episode %s)...", episode_number
        )

        response = self.client.chat.completions.create(
            model="gpt-4o",
            max_tokens=4000,
            temperature=0.1,  # deterministic classification
            messages=[
                {
                    "role": "system",
                    "content": "You are a content compliance reviewer for YouTube. Respond only with valid JSON.",
                },
                {"role": "user", "content": prompt},
            ],
        )

        response_text = response.choices[0].message.content

        # Parse JSON response (strip any leading/trailing non-JSON text)
        violations = self._parse_response(response_text)

        # Convert timestamps and attach severity
        flagged = []
        for item in violations:
            start_seconds = self._timestamp_to_seconds(
                item.get("start_timestamp", "00:00:00")
            )
            end_seconds = self._timestamp_to_seconds(
                item.get("end_timestamp", "00:00:00")
            )
            category = item.get("category", "")
            severity = SEVERITY_MAP.get(category, "warning")
            flagged.append(
                {
                    "start_seconds": start_seconds,
                    "end_seconds": end_seconds,
                    "text": item.get("text", ""),
                    "category": category,
                    "severity": severity,
                    "reason": item.get("reason", ""),
                }
            )

        critical = any(item["severity"] == "critical" for item in flagged)

        result = {
            "flagged": flagged,
            "critical": critical,
            "report_path": None,
        }

        # Save the report
        report_path = self.save_report(
            result=result,
            episode_output_dir=episode_output_dir,
            episode_number=episode_number,
            timestamp=timestamp,
        )
        result["report_path"] = str(report_path)

        logger.info(
            "Compliance check complete: %d flagged, critical=%s",
            len(flagged),
            critical,
        )

        return result

    def save_report(
        self,
        result: dict,
        episode_output_dir,
        episode_number: int,
        timestamp: str,
    ) -> Path:
        """Write compliance report JSON to the episode output directory.

        Args:
            result: Output of check_transcript() (flagged, critical, report_path).
            episode_output_dir: Directory to write the report into.
            episode_number: Episode number for the filename.
            timestamp: Timestamp string for the filename.

        Returns:
            Path to the written JSON file.
        """
        episode_output_dir = Path(episode_output_dir)
        episode_output_dir.mkdir(parents=True, exist_ok=True)

        filename = f"compliance_report_{episode_number}_{timestamp}.json"
        report_path = episode_output_dir / filename

        flagged = result.get("flagged", [])
        critical_items = [
            item for item in flagged if item.get("severity") == "critical"
        ]
        warning_items = [item for item in flagged if item.get("severity") == "warning"]

        report = {
            "episode_number": episode_number,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "critical": result.get("critical", False),
            "flagged": critical_items,
            "warnings": warning_items,
        }

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

        logger.info("Compliance report saved: %s", report_path)
        return report_path

    def get_censor_entries(self, compliance_result: dict) -> list:
        """Convert flagged compliance items to censor_timestamps-compatible dicts.

        These can be merged directly into analysis["censor_timestamps"] so that
        AudioProcessor.apply_censorship() will mute the flagged segments.

        Args:
            compliance_result: Output of check_transcript() with a 'flagged' list.

        Returns:
            List of dicts with start_seconds, end_seconds, reason, context.
        """
        entries = []
        for item in compliance_result.get("flagged", []):
            entries.append(
                {
                    "start_seconds": item["start_seconds"],
                    "end_seconds": item["end_seconds"],
                    "reason": f"Compliance: {item['category']}",
                    "context": item["text"][:100],
                }
            )
        return entries

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _format_transcript(self, transcript_data: dict) -> str:
        """Format transcript segments as timestamped text lines.

        Each line: [HH:MM:SS] segment text

        Args:
            transcript_data: Dict with 'segments' list of {start, end, text}.

        Returns:
            Formatted string ready to inject into the compliance prompt.
        """
        segments = transcript_data.get("segments", [])
        lines = []
        for segment in segments:
            start_ts = self._seconds_to_timestamp(segment.get("start", 0.0))
            text = segment.get("text", "").strip()
            lines.append(f"[{start_ts}] {text}")
        return "\n".join(lines)

    @staticmethod
    def _seconds_to_timestamp(seconds: float) -> str:
        """Convert float seconds to HH:MM:SS."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    @staticmethod
    def _timestamp_to_seconds(timestamp_str: str) -> float:
        """Convert HH:MM:SS to float seconds."""
        parts = timestamp_str.split(":")
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        elif len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        return float(parts[0])

    @staticmethod
    def _parse_response(response_text: str) -> list:
        """Extract JSON array from GPT-4o response text.

        GPT-4o may wrap the array in markdown code fences or add explanatory text.

        Args:
            response_text: Raw string from GPT-4o.

        Returns:
            Parsed list of violation dicts.
        """
        text = response_text.strip()

        # Strip markdown code fences if present
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:])
            if text.endswith("```"):
                text = text[: text.rfind("```")]

        # Find the JSON array boundaries
        start = text.find("[")
        end = text.rfind("]") + 1

        if start == -1 or end == 0:
            logger.warning(
                "No JSON array found in compliance response; treating as empty."
            )
            return []

        try:
            return json.loads(text[start:end])
        except json.JSONDecodeError as e:
            logger.error("Failed to parse compliance JSON response: %s", e)
            return []
