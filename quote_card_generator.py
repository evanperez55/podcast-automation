"""Quote card image generator for shareable social media images."""

import os
from pathlib import Path
from typing import Optional

from client_config import resolve_client_logo_or_raise
from config import Config
from logger import logger


class QuoteCardGenerator:
    """Generates 1080x1080 PNG quote cards for social media sharing."""

    def __init__(self):
        self.enabled = os.getenv("QUOTE_CARD_ENABLED", "true").lower() == "true"
        self.bg_color = os.getenv("QUOTE_CARD_BG_COLOR", "#1a1a2e")
        self.text_color = os.getenv("QUOTE_CARD_TEXT_COLOR", "#ffffff")
        self.accent_color = os.getenv("QUOTE_CARD_ACCENT_COLOR", "#e94560")
        self.font_path = os.getenv("THUMBNAIL_FONT", None)
        self.width = 1080
        self.height = 1080
        self.logo_path = resolve_client_logo_or_raise(
            Config.ASSETS_DIR / "podcast_logo.png", module="QuoteCardGenerator"
        )

    def generate_quote_card(
        self,
        quote_text: str,
        episode_number: int,
        output_path: str,
    ) -> Optional[Path]:
        """Create a 1080x1080 PNG quote card.

        Args:
            quote_text: The quote text to display.
            episode_number: Episode number for the badge.
            output_path: File path where the PNG will be saved.

        Returns:
            Path to the saved image, or None on failure.
        """
        if not self.enabled:
            logger.warning("Quote card generation disabled")
            return None

        try:
            from PIL import Image, ImageDraw

            # Create background
            image = Image.new("RGBA", (self.width, self.height), self.bg_color)
            draw = ImageDraw.Draw(image)

            # Load fonts
            quote_font = self._load_font(48)
            accent_font = self._load_font(120)
            badge_font = self._load_font(24)
            brand_font = self._load_font(20)

            # Draw open-quote glyph
            draw.text(
                (80, 60),
                "\u201c",
                font=accent_font,
                fill=self.accent_color,
            )

            # Word-wrap and draw quote text
            padding = 100
            max_text_width = self.width - (padding * 2)
            wrapped = self._word_wrap(quote_text, quote_font, max_text_width, draw)

            # Calculate vertical center for quote
            line_height = quote_font.size + 12 if hasattr(quote_font, "size") else 60
            try:
                bbox = draw.textbbox((0, 0), wrapped, font=quote_font)
                text_height = bbox[3] - bbox[1]
            except (AttributeError, TypeError):
                text_height = wrapped.count("\n") * line_height + line_height

            y_start = max(200, (self.height - text_height) // 2 - 40)

            # Shadow
            draw.text(
                (padding + 2, y_start + 2),
                wrapped,
                font=quote_font,
                fill="#00000066",
            )
            # Main text
            draw.text(
                (padding, y_start),
                wrapped,
                font=quote_font,
                fill=self.text_color,
            )

            # Draw closing quote
            draw.text(
                (self.width - 180, self.height - 200),
                "\u201d",
                font=accent_font,
                fill=self.accent_color,
            )

            # Episode badge (bottom-left)
            badge_text = f"EP {episode_number}"
            badge_x, badge_y = 80, self.height - 100
            try:
                draw.rounded_rectangle(
                    [badge_x, badge_y, badge_x + 100, badge_y + 40],
                    radius=8,
                    fill=self.accent_color,
                )
            except AttributeError:
                draw.rectangle(
                    [badge_x, badge_y, badge_x + 100, badge_y + 40],
                    fill=self.accent_color,
                )
            draw.text(
                (badge_x + 12, badge_y + 8),
                badge_text,
                font=badge_font,
                fill="#ffffff",
            )

            # Podcast name (bottom-right)
            draw.text(
                (self.width - 380, self.height - 80),
                Config.PODCAST_NAME,
                font=brand_font,
                fill="#888888",
            )

            # Save
            output = Path(output_path)
            output.parent.mkdir(parents=True, exist_ok=True)
            image.save(str(output), "PNG")
            logger.info("Quote card saved to %s", output)
            return output

        except Exception as e:
            logger.error("Failed to generate quote card: %s", e)
            return None

    def generate_all_quote_cards(
        self,
        analysis: dict,
        episode_number: int,
        output_dir: str,
    ) -> list:
        """Generate quote cards for all best_quotes in the analysis.

        Args:
            analysis: Episode analysis dict containing best_quotes.
            episode_number: Episode number.
            output_dir: Directory to save quote card images.

        Returns:
            List of output Path objects.
        """
        if not self.enabled:
            return []

        quotes = analysis.get("best_quotes", [])
        if not quotes:
            logger.info("No best_quotes in analysis, skipping quote cards")
            return []

        output_dir = Path(output_dir)
        paths = []
        for i, quote_data in enumerate(quotes[:5]):
            quote_text = quote_data.get("quote", "")
            if not quote_text:
                continue
            output_path = output_dir / f"quote_card_{i + 1}.png"
            result = self.generate_quote_card(
                quote_text, episode_number, str(output_path)
            )
            if result:
                paths.append(result)

        logger.info("Generated %d quote card(s)", len(paths))
        return paths

    def _load_font(self, size: int):
        """Load a font at the given size, falling back to Pillow default."""
        from PIL import ImageFont

        if self.font_path:
            try:
                return ImageFont.truetype(self.font_path, size)
            except (OSError, IOError):
                pass
        try:
            return ImageFont.truetype("arial.ttf", size)
        except (OSError, IOError):
            return ImageFont.load_default()

    def _word_wrap(self, text: str, font, max_width: int, draw) -> str:
        """Wrap text to fit within max_width pixels."""
        words = text.split()
        lines = []
        current_line = []

        for word in words:
            test_line = " ".join(current_line + [word])
            try:
                bbox = draw.textbbox((0, 0), test_line, font=font)
                line_width = bbox[2] - bbox[0]
            except (AttributeError, TypeError):
                line_width = len(test_line) * 20

            if line_width <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = [word]

        if current_line:
            lines.append(" ".join(current_line))

        return "\n".join(lines)
