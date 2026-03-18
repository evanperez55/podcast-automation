"""Tests for EpisodeWebpageGenerator — WEB-01 through WEB-05 coverage."""

# WEB-01: HTML generation with transcript text, HTML-escaping
# WEB-02: JSON-LD structured data (PodcastEpisode)
# WEB-03: Open Graph + Twitter Card meta tags, YAKE keyword extraction
# WEB-04: Chapter anchor links + transcript segment anchors
# WEB-05: Sitemap XML generation and URL merging

import json
import unittest
import xml.etree.ElementTree as ET
from unittest.mock import patch

from episode_webpage_generator import EpisodeWebpageGenerator

SAMPLE_ANALYSIS = {
    "episode_title": "Lobsters Live Forever (Probably)",
    "episode_summary": "Two guys discuss whether lobsters are immortal and why that's unfair.",
    "show_notes": (
        "In this episode we dive deep into lobster biology, "
        "the science of biological aging, and whether immortality is even desirable. "
        "Key topics: telomere biology, crustacean lifespan, existential dread, "
        "and the funniest arguments about death you'll ever hear."
    ),
    "chapters": [
        {"start_seconds": 0, "start_timestamp": "00:00:00", "title": "Intro"},
        {
            "start_seconds": 300,
            "start_timestamp": "00:05:00",
            "title": "Lobster Biology",
        },
        {
            "start_seconds": 900,
            "start_timestamp": "00:15:00",
            "title": "Why This Is Unfair",
        },
    ],
}

SAMPLE_TRANSCRIPT = {
    "segments": [
        {"text": "Welcome to Fake Problems.", "start": 0.0, "end": 3.5},
        {"text": "Today we talk about lobsters.", "start": 3.5, "end": 7.0},
        {"text": "Lobsters don't age like we do.", "start": 300.0, "end": 305.0},
        {"text": "It's deeply unfair.", "start": 900.0, "end": 903.0},
    ]
}

XSS_TRANSCRIPT = {
    "segments": [
        {"text": "<script>alert('xss')</script>", "start": 0.0, "end": 2.0},
        {"text": "Normal text & more <stuff>.", "start": 2.0, "end": 5.0},
    ]
}

EXISTING_SITEMAP_XML = """<?xml version='1.0' encoding='utf-8'?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com/episodes/ep1.html</loc></url>
  <url><loc>https://example.com/episodes/ep2.html</loc></url>
</urlset>"""


class TestGenerateHtml(unittest.TestCase):
    """WEB-01: HTML generation from transcript data."""

    def setUp(self):
        with patch.dict("os.environ", {"SITE_BASE_URL": "https://example.com"}):
            self.gen = EpisodeWebpageGenerator()

    def test_transcript_segments_in_html(self):
        """All transcript segment texts appear in rendered HTML.

        Jinja2 autoescaping converts apostrophes to &#39; — we check for the
        escaped form of segments containing apostrophes, and plain form for others.
        """
        html = self.gen.generate_html(
            episode_number=42,
            analysis=SAMPLE_ANALYSIS,
            transcript_data=SAMPLE_TRANSCRIPT,
        )
        self.assertIn("Welcome to Fake Problems.", html)
        self.assertIn("Today we talk about lobsters.", html)
        # Jinja2 autoescape converts ' -> &#39;
        self.assertIn("Lobsters don&#39;t age like we do.", html)
        self.assertIn("It&#39;s deeply unfair.", html)

    def test_html_escaping_xss_prevention(self):
        """Dangerous HTML in transcript text is escaped, not rendered raw."""
        html = self.gen.generate_html(
            episode_number=42,
            analysis=SAMPLE_ANALYSIS,
            transcript_data=XSS_TRANSCRIPT,
        )
        # The raw script tag must NOT appear verbatim
        self.assertNotIn("<script>alert('xss')</script>", html)
        # Escaped versions of < > & must appear
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("&amp;", html)

    def test_episode_title_in_html(self):
        """Episode title appears in the HTML page."""
        html = self.gen.generate_html(
            episode_number=42,
            analysis=SAMPLE_ANALYSIS,
            transcript_data=SAMPLE_TRANSCRIPT,
        )
        self.assertIn("Lobsters Live Forever (Probably)", html)

    def test_html_starts_with_doctype(self):
        """Output is a complete HTML page."""
        html = self.gen.generate_html(
            episode_number=42,
            analysis=SAMPLE_ANALYSIS,
            transcript_data=SAMPLE_TRANSCRIPT,
        )
        self.assertIn("<!DOCTYPE html>", html)


class TestJsonLd(unittest.TestCase):
    """WEB-02: JSON-LD PodcastEpisode structured data."""

    def setUp(self):
        with patch.dict("os.environ", {"SITE_BASE_URL": "https://example.com"}):
            self.gen = EpisodeWebpageGenerator()

    def _extract_jsonld(self, html: str) -> dict:
        """Extract and parse the first application/ld+json script block."""
        import re

        match = re.search(
            r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            html,
            re.DOTALL,
        )
        self.assertIsNotNone(match, "No JSON-LD script tag found in HTML")
        return json.loads(match.group(1))

    def test_jsonld_type_and_fields(self):
        """JSON-LD contains @type PodcastEpisode with required fields."""
        html = self.gen.generate_html(
            episode_number=42,
            analysis=SAMPLE_ANALYSIS,
            transcript_data=SAMPLE_TRANSCRIPT,
        )
        data = self._extract_jsonld(html)
        self.assertEqual(data.get("@type"), "PodcastEpisode")
        self.assertIn("name", data)
        self.assertIn("description", data)
        self.assertIn("episodeNumber", data)
        self.assertEqual(data["episodeNumber"], 42)

    def test_jsonld_part_of_series(self):
        """JSON-LD contains partOfSeries with PodcastSeries type."""
        html = self.gen.generate_html(
            episode_number=42,
            analysis=SAMPLE_ANALYSIS,
            transcript_data=SAMPLE_TRANSCRIPT,
        )
        data = self._extract_jsonld(html)
        self.assertIn("partOfSeries", data)
        series = data["partOfSeries"]
        self.assertEqual(series.get("@type"), "PodcastSeries")

    def test_jsonld_episode_name_matches_title(self):
        """JSON-LD name field matches the episode title from analysis."""
        html = self.gen.generate_html(
            episode_number=42,
            analysis=SAMPLE_ANALYSIS,
            transcript_data=SAMPLE_TRANSCRIPT,
        )
        data = self._extract_jsonld(html)
        self.assertIn("Lobsters Live Forever", data.get("name", ""))


class TestMetaTags(unittest.TestCase):
    """WEB-03: Open Graph and Twitter Card meta tags."""

    def setUp(self):
        with patch.dict("os.environ", {"SITE_BASE_URL": "https://example.com"}):
            self.gen = EpisodeWebpageGenerator()

    def test_og_tags_present(self):
        """Open Graph og:title and og:description meta tags are in HTML."""
        html = self.gen.generate_html(
            episode_number=42,
            analysis=SAMPLE_ANALYSIS,
            transcript_data=SAMPLE_TRANSCRIPT,
        )
        self.assertIn('property="og:title"', html)
        self.assertIn('property="og:description"', html)
        self.assertIn('property="og:url"', html)

    def test_twitter_tags_present(self):
        """Twitter Card meta tags are in HTML."""
        html = self.gen.generate_html(
            episode_number=42,
            analysis=SAMPLE_ANALYSIS,
            transcript_data=SAMPLE_TRANSCRIPT,
        )
        self.assertIn('name="twitter:card"', html)
        self.assertIn('name="twitter:title"', html)

    def test_keywords_meta_tag_present(self):
        """meta name='keywords' tag appears in HTML."""
        html = self.gen.generate_html(
            episode_number=42,
            analysis=SAMPLE_ANALYSIS,
            transcript_data=SAMPLE_TRANSCRIPT,
        )
        self.assertIn('name="keywords"', html)


class TestKeywordExtraction(unittest.TestCase):
    """WEB-03: YAKE keyword extraction."""

    def setUp(self):
        with patch.dict("os.environ", {"SITE_BASE_URL": "https://example.com"}):
            self.gen = EpisodeWebpageGenerator()

    def test_keywords_nonempty_from_real_text(self):
        """extract_keywords returns non-empty list from sample show notes text."""
        keywords = self.gen.extract_keywords(SAMPLE_ANALYSIS["show_notes"])
        self.assertIsInstance(keywords, list)
        self.assertGreater(len(keywords), 0)
        # All items should be strings
        for kw in keywords:
            self.assertIsInstance(kw, str)

    def test_empty_text_returns_empty_list(self):
        """extract_keywords returns empty list when given empty string."""
        keywords = self.gen.extract_keywords("")
        self.assertEqual(keywords, [])

    def test_none_text_returns_empty_list(self):
        """extract_keywords returns empty list when given None."""
        keywords = self.gen.extract_keywords(None)
        self.assertEqual(keywords, [])

    def test_keyword_count_bounded(self):
        """extract_keywords returns at most n keywords."""
        keywords = self.gen.extract_keywords(SAMPLE_ANALYSIS["show_notes"], n=3)
        self.assertLessEqual(len(keywords), 3)


class TestChapterNav(unittest.TestCase):
    """WEB-04: Chapter navigation links and transcript segment anchors."""

    def setUp(self):
        with patch.dict("os.environ", {"SITE_BASE_URL": "https://example.com"}):
            self.gen = EpisodeWebpageGenerator()

    def test_chapter_anchor_links(self):
        """Chapter titles render as anchor links with #t-{seconds} hrefs."""
        html = self.gen.generate_html(
            episode_number=42,
            analysis=SAMPLE_ANALYSIS,
            transcript_data=SAMPLE_TRANSCRIPT,
        )
        self.assertIn('href="#t-0"', html)
        self.assertIn('href="#t-300"', html)
        self.assertIn('href="#t-900"', html)

    def test_chapter_titles_in_nav(self):
        """Chapter titles appear in the HTML."""
        html = self.gen.generate_html(
            episode_number=42,
            analysis=SAMPLE_ANALYSIS,
            transcript_data=SAMPLE_TRANSCRIPT,
        )
        self.assertIn("Lobster Biology", html)
        self.assertIn("Why This Is Unfair", html)

    def test_transcript_segment_id_anchors(self):
        """Transcript segments have id='t-{seconds}' anchors."""
        html = self.gen.generate_html(
            episode_number=42,
            analysis=SAMPLE_ANALYSIS,
            transcript_data=SAMPLE_TRANSCRIPT,
        )
        self.assertIn('id="t-0"', html)
        self.assertIn('id="t-300"', html)
        self.assertIn('id="t-900"', html)


class TestSitemap(unittest.TestCase):
    """WEB-05: Sitemap XML generation and URL merging."""

    def setUp(self):
        with patch.dict("os.environ", {"SITE_BASE_URL": "https://example.com"}):
            self.gen = EpisodeWebpageGenerator()

    def test_sitemap_generates_valid_xml(self):
        """generate_sitemap produces well-formed XML with sitemaps.org namespace."""
        xml_str = self.gen.generate_sitemap(
            existing_xml=None,
            new_url="https://example.com/episodes/ep42.html",
        )
        # Must parse without error
        root = ET.fromstring(xml_str)
        self.assertIn("sitemaps.org", root.tag)

    def test_sitemap_contains_new_url(self):
        """generate_sitemap output contains the new URL."""
        new_url = "https://example.com/episodes/ep42.html"
        xml_str = self.gen.generate_sitemap(existing_xml=None, new_url=new_url)
        self.assertIn(new_url, xml_str)

    def test_sitemap_merges_existing_urls(self):
        """Adding a 3rd URL to an existing 2-URL sitemap produces 3 URLs."""
        new_url = "https://example.com/episodes/ep42.html"
        xml_str = self.gen.generate_sitemap(
            existing_xml=EXISTING_SITEMAP_XML,
            new_url=new_url,
        )
        self.assertIn("ep1.html", xml_str)
        self.assertIn("ep2.html", xml_str)
        self.assertIn("ep42.html", xml_str)

    def test_sitemap_no_duplicate_url(self):
        """Adding a URL already present in the sitemap does not create a duplicate."""
        existing_url = "https://example.com/episodes/ep1.html"
        xml_str = self.gen.generate_sitemap(
            existing_xml=EXISTING_SITEMAP_XML,
            new_url=existing_url,
        )
        # Count occurrences of the URL
        count = xml_str.count(existing_url)
        self.assertEqual(count, 1, f"Expected 1 occurrence, got {count}")

    def test_sitemap_xml_has_namespace(self):
        """Sitemap XML root has the correct sitemaps.org namespace."""
        xml_str = self.gen.generate_sitemap(
            existing_xml=None,
            new_url="https://example.com/episodes/ep42.html",
        )
        self.assertIn("http://www.sitemaps.org/schemas/sitemap/0.9", xml_str)


class TestBuildEpisodeUrl(unittest.TestCase):
    """Tests for _build_episode_url helper."""

    def test_episode_url_format(self):
        """URL follows expected pattern: {SITE_BASE_URL}/episodes/ep{N}.html."""
        with patch.dict("os.environ", {"SITE_BASE_URL": "https://example.com"}):
            gen = EpisodeWebpageGenerator()
        url = gen._build_episode_url(42)
        self.assertEqual(url, "https://example.com/episodes/ep42.html")


if __name__ == "__main__":
    unittest.main()
