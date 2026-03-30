"""Tests for ollama_client module."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from ollama_client import ContentBlock, MessageResponse, Messages, Ollama, OllamaClient


class TestOllamaClientInit:
    """Tests for OllamaClient initialization."""

    def test_default_model(self):
        """Default model is qwen2.5:7b."""
        client = OllamaClient()
        assert client.model == "qwen2.5:7b"

    def test_custom_model(self):
        """Accepts custom model name."""
        client = OllamaClient(model="llama3:8b")
        assert client.model == "llama3:8b"


class TestOllamaClientChat:
    """Tests for OllamaClient.chat."""

    @patch("ollama_client.requests.post")
    def test_chat_success(self, mock_post):
        """Returns stripped response text on success."""
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"response": "  Hello world  "},
        )
        mock_post.return_value.raise_for_status = MagicMock()

        client = OllamaClient()
        result = client.chat([{"role": "user", "content": "Hi"}])

        assert result == "Hello world"
        mock_post.assert_called_once()

    @patch("ollama_client.requests.post")
    def test_chat_connection_error(self, mock_post):
        """Raises on connection error."""
        mock_post.side_effect = requests.exceptions.ConnectionError("refused")

        client = OllamaClient()
        with pytest.raises(requests.exceptions.ConnectionError):
            client.chat([{"role": "user", "content": "Hi"}])

    @patch("ollama_client.requests.post")
    def test_chat_other_error(self, mock_post):
        """Raises on other errors."""
        mock_post.side_effect = RuntimeError("timeout")

        client = OllamaClient()
        with pytest.raises(RuntimeError):
            client.chat([{"role": "user", "content": "Hi"}])

    @patch("ollama_client.requests.post")
    def test_chat_passes_params(self, mock_post):
        """Passes temperature and max_tokens to API."""
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"response": "ok"},
        )
        mock_post.return_value.raise_for_status = MagicMock()

        client = OllamaClient()
        client.chat(
            [{"role": "user", "content": "test"}],
            temperature=0.7,
            max_tokens=1000,
        )

        payload = mock_post.call_args.kwargs["json"]
        assert payload["options"]["temperature"] == 0.7
        assert payload["options"]["num_predict"] == 1000


class TestBuildPrompt:
    """Tests for _build_prompt."""

    def test_builds_prompt_from_messages(self):
        """Formats messages into prompt string."""
        client = OllamaClient()
        messages = [
            {"role": "system", "content": "Be helpful"},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]
        prompt = client._build_prompt(messages)

        assert "System: Be helpful" in prompt
        assert "User: Hello" in prompt
        assert "Assistant: Hi there" in prompt
        assert prompt.endswith("Assistant:")


class TestAnthropicCompatibility:
    """Tests for Anthropic API compatibility wrappers."""

    def test_content_block(self):
        """ContentBlock stores text."""
        block = ContentBlock("hello")
        assert block.text == "hello"

    def test_message_response(self):
        """MessageResponse wraps text in content list."""
        resp = MessageResponse("hello")
        assert len(resp.content) == 1
        assert resp.content[0].text == "hello"

    @patch("ollama_client.requests.post")
    def test_messages_create(self, mock_post):
        """Messages.create returns MessageResponse."""
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"response": "result"},
        )
        mock_post.return_value.raise_for_status = MagicMock()

        client = OllamaClient()
        messages = Messages(client)
        resp = messages.create(
            model="test",
            messages=[{"role": "user", "content": "Hi"}],
        )

        assert isinstance(resp, MessageResponse)
        assert resp.content[0].text == "result"

    @patch("ollama_client.requests.post")
    def test_ollama_drop_in(self, mock_post):
        """Ollama class works as Anthropic client drop-in."""
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"response": "test"},
        )
        mock_post.return_value.raise_for_status = MagicMock()

        ollama = Ollama()
        resp = ollama.messages.create(
            model="test",
            messages=[{"role": "user", "content": "Hi"}],
        )

        assert resp.content[0].text == "test"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
