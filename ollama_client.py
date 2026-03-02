"""Ollama client wrapper for local LLM inference (replaces Anthropic Claude API)."""

import requests
from typing import Dict, List
from logger import logger
from config import Config


class OllamaClient:
    """
    Local LLM client using Ollama HTTP API - completely free alternative to Claude API.

    Usage:
        client = OllamaClient()
        response = client.chat(messages=[...])
    """

    def __init__(self, model: str = "llama3.2"):
        self.model = model
        self.base_url = Config.OLLAMA_BASE_URL
        logger.info(
            "Ollama client ready (model: %s, url: %s)", self.model, self.base_url
        )

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4000,
    ) -> str:
        prompt = self._build_prompt(messages)

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }

        try:
            response = requests.post(
                f"{self.base_url}/api/generate", json=payload, timeout=300
            )
            response.raise_for_status()
            data = response.json()
            return data.get("response", "").strip()

        except requests.exceptions.ConnectionError:
            logger.error(
                "Cannot connect to Ollama at %s. Is Ollama running?", self.base_url
            )
            raise
        except Exception as e:
            logger.error("Ollama request failed: %s", e)
            raise

    def _build_prompt(self, messages: List[Dict[str, str]]) -> str:
        prompt_parts = []
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "system":
                prompt_parts.append(f"System: {content}\n")
            elif role == "user":
                prompt_parts.append(f"User: {content}\n")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}\n")
        prompt_parts.append("Assistant:")
        return "\n".join(prompt_parts)


# Compatibility wrapper to match Anthropic API interface
class Messages:
    def __init__(self, ollama_client: OllamaClient):
        self.ollama_client = ollama_client

    def create(
        self,
        model: str,
        messages: List[Dict[str, str]],
        max_tokens: int = 4000,
        temperature: float = 0.3,
        **kwargs,
    ) -> "MessageResponse":
        response_text = self.ollama_client.chat(
            messages=messages, temperature=temperature, max_tokens=max_tokens
        )
        return MessageResponse(response_text)


class MessageResponse:
    def __init__(self, text: str):
        self.content = [ContentBlock(text)]


class ContentBlock:
    def __init__(self, text: str):
        self.text = text


class Ollama:
    """Drop-in replacement for Anthropic client."""

    def __init__(self, api_key: str = None):
        self.ollama_client = OllamaClient()
        self.messages = Messages(self.ollama_client)
