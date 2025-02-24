"""
Client for making API calls to various LLM providers using their official SDKs.
"""

from collections.abc import Generator

from anthropic import Anthropic
from openai import OpenAI


class LLMClient:
    def __init__(self, api_key: str):
        """Initialize the LLM client.

        Args:
            api_key: API key for the provider
        """
        self.api_key = api_key
        self.openai_client = OpenAI(api_key=api_key)
        self.anthropic_client = Anthropic(api_key=api_key)
        self.openrouter_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
            default_headers={
                "HTTP-Referer": "http://localhost:8080",  # Required by OpenRouter
                "X-Title": "Airflow Wingman",  # Required by OpenRouter
            },
        )

    def chat_completion(
        self, messages: list[dict[str, str]], model: str, provider: str, temperature: float = 0.7, max_tokens: int | None = None, stream: bool = False
    ) -> Generator[str, None, None] | dict:
        """Send a chat completion request to the specified provider.

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            model: Model identifier
            provider: Provider identifier (openai, anthropic, openrouter)
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response

        Returns:
            If stream=True, returns a generator yielding response chunks
            If stream=False, returns the complete response
        """
        try:
            if provider == "openai":
                return self._openai_chat_completion(messages, model, temperature, max_tokens, stream)
            elif provider == "anthropic":
                return self._anthropic_chat_completion(messages, model, temperature, max_tokens, stream)
            elif provider == "openrouter":
                return self._openrouter_chat_completion(messages, model, temperature, max_tokens, stream)
            else:
                return {"error": f"Unknown provider: {provider}"}
        except Exception as e:
            return {"error": f"API request failed: {str(e)}"}

    def _openai_chat_completion(self, messages: list[dict[str, str]], model: str, temperature: float, max_tokens: int | None, stream: bool):
        """Handle OpenAI chat completion requests."""
        response = self.openai_client.chat.completions.create(model=model, messages=messages, temperature=temperature, max_tokens=max_tokens, stream=stream)

        if stream:

            def response_generator():
                for chunk in response:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content

            return response_generator()
        else:
            return {"content": response.choices[0].message.content}

    def _anthropic_chat_completion(self, messages: list[dict[str, str]], model: str, temperature: float, max_tokens: int | None, stream: bool):
        """Handle Anthropic chat completion requests."""
        # Convert messages to Anthropic format
        system_message = next((m["content"] for m in messages if m["role"] == "system"), None)
        conversation = []
        for m in messages:
            if m["role"] != "system":
                conversation.append({"role": "assistant" if m["role"] == "assistant" else "user", "content": m["content"]})

        response = self.anthropic_client.messages.create(model=model, messages=conversation, system=system_message, temperature=temperature, max_tokens=max_tokens, stream=stream)

        if stream:

            def response_generator():
                for chunk in response:
                    if chunk.delta.text:
                        yield chunk.delta.text

            return response_generator()
        else:
            return {"content": response.content[0].text}

    def _openrouter_chat_completion(self, messages: list[dict[str, str]], model: str, temperature: float, max_tokens: int | None, stream: bool):
        """Handle OpenRouter chat completion requests."""
        response = self.openrouter_client.chat.completions.create(model=model, messages=messages, temperature=temperature, max_tokens=max_tokens, stream=stream)

        if stream:

            def response_generator():
                for chunk in response:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content

            return response_generator()
        else:
            return {"content": response.choices[0].message.content}
