"""Thumbnail generation for podcast episodes."""

import os
from pathlib import Path
from typing import Optional

from config import Config
from logger import logger


class ThumbnailGenerator:
    """Generates 1280x720 PNG thumbnails for podcast episodes."""

    def __init__(self):
        self.font_path = os.getenv("THUMBNAIL_FONT", None)  # None = use Pillow default
        self.bg_color = os.getenv("THUMBNAIL_BG_COLOR", "#1a1a2e")
        self.text_color = os.getenv("THUMBNAIL_TEXT_COLOR", "#ffffff")
        self.badge_color = os.getenv("THUMBNAIL_BADGE_COLOR", "#e94560")
        self.width = 1280
        self.height = 720
        self.logo_path = Config.ASSETS_DIR / "podcast_logo.png"

    def generate_thumbnail(
        self, episode_title: str, episode_number: int, output_path: str
    ) -> Optional[Path]:
        """Create a 1280x720 PNG thumbnail for an episode.

        Args:
            episode_title: The title text to display on the thumbnail.
            episode_number: Episode number for the badge.
            output_path: File path where the PNG will be saved.

        Returns:
            Path to the saved thumbnail, or None on failure.
        """
        try:
            image = self._create_background(self.width, self.height)
            image = self._overlay_title_text(image, episode_title)
            image = self._add_episode_badge(image, episode_number)

            output = Path(output_path)
            output.parent.mkdir(parents=True, exist_ok=True)
            image.save(str(output), "PNG")
            logger.info(f"Thumbnail saved to {output}")
            return output
        except Exception as e:
            logger.error(f"Failed to generate thumbnail: {e}")
            return None

    def _create_background(self, width: int, height: int):
        """Create the background image, using the logo if available.

        Args:
            width: Image width in pixels.
            height: Image height in pixels.

        Returns:
            PIL Image object.
        """
        from PIL import Image

        try:
            if self.logo_path.exists():
                logo = Image.open(str(self.logo_path))
                logo = logo.resize((width, height))
                # Ensure RGBA so we can composite later
                return logo.convert("RGBA")
        except Exception as e:
            logger.warning(f"Could not load logo, using solid background: {e}")

        image = Image.new("RGBA", (width, height), self.bg_color)
        return image

    def _overlay_title_text(self, image, title: str):
        """Draw word-wrapped title text with a shadow onto the image.

        Args:
            image: PIL Image to draw on.
            title: Episode title string.

        Returns:
            PIL Image with title text drawn.
        """
        from PIL import ImageDraw, ImageFont

        draw = ImageDraw.Draw(image)

        # Load font
        try:
            font = ImageFont.truetype(self.font_path, size=60)
        except Exception:
            font = ImageFont.load_default()

        padding = 80
        max_width = image.width - (padding * 2)

        # Word-wrap title to fit within max_width
        words = title.split()
        lines = []
        current_line = ""
        for word in words:
            test_line = f"{current_line} {word}".strip()
            bbox = draw.textbbox((0, 0), test_line, font=font)
            line_width = bbox[2] - bbox[0]
            if line_width <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)

        # Calculate total text block height
        line_height = (
            draw.textbbox((0, 0), "Ay", font=font)[3]
            - draw.textbbox((0, 0), "Ay", font=font)[1]
        )
        spacing = 10
        total_height = len(lines) * line_height + (len(lines) - 1) * spacing

        # Start at roughly 40% from top
        y = int(image.height * 0.4) - total_height // 2

        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            line_width = bbox[2] - bbox[0]
            x = (image.width - line_width) // 2

            # Draw shadow
            draw.text((x + 3, y + 3), line, fill="#000000", font=font)
            # Draw main text
            draw.text((x, y), line, fill=self.text_color, font=font)

            y += line_height + spacing

        return image

    def _add_episode_badge(self, image, episode_number: int):
        """Draw an episode number badge in the top-right corner.

        Args:
            image: PIL Image to draw on.
            episode_number: Episode number to display.

        Returns:
            PIL Image with badge drawn.
        """
        from PIL import ImageDraw, ImageFont

        draw = ImageDraw.Draw(image)

        # Load font for badge
        try:
            font = ImageFont.truetype(self.font_path, size=36)
        except Exception:
            font = ImageFont.load_default()

        badge_text = f"EP {episode_number}"
        badge_x = image.width - 180
        badge_y = 20
        badge_width = 160
        badge_height = 60

        # Draw rounded rectangle badge (fallback to regular rectangle)
        try:
            draw.rounded_rectangle(
                [badge_x, badge_y, badge_x + badge_width, badge_y + badge_height],
                radius=12,
                fill=self.badge_color,
            )
        except AttributeError:
            # Older Pillow versions may not have rounded_rectangle
            draw.rectangle(
                [badge_x, badge_y, badge_x + badge_width, badge_y + badge_height],
                fill=self.badge_color,
            )

        # Center text within the badge
        text_bbox = draw.textbbox((0, 0), badge_text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        text_x = badge_x + (badge_width - text_width) // 2
        text_y = badge_y + (badge_height - text_height) // 2

        draw.text((text_x, text_y), badge_text, fill="#ffffff", font=font)

        return image
