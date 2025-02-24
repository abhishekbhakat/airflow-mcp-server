"""
Client for making API calls to various LLM providers using their official SDKs.
"""

from collections.abc import AsyncGenerator

from anthropic import AsyncAnthropic
from openai import AsyncOpenAI


class LLMClient:
    def __init__(self, api_key: str):
        """Initialize the LLM client.

        Args:
            api_key: API key for the provider
        """
        self.api_key = api_key
        self.openai_client = AsyncOpenAI(api_key=api_key)
        self.anthropic_client = AsyncAnthropic(api_key=api_key)
        self.openrouter_client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
            default_headers={
                "HTTP-Referer": "http://localhost:8080",  # Required by OpenRouter
                "X-Title": "Airflow Wingman",  # Required by OpenRouter
            },
        )

    async def chat_completion(
        self, messages: list[dict[str, str]], model: str, provider: str, temperature: float = 0.7, max_tokens: int | None = None, stream: bool = False
    ) -> AsyncGenerator[str, None] | dict:
        """Send a chat completion request to the specified provider.

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            model: Model identifier
            provider: Provider identifier (openai, anthropic, openrouter)
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response

        Returns:
            If stream=True, returns an async generator yielding response chunks
            If stream=False, returns the complete response
        """
        try:
            if provider == "openai":
                return await self._openai_chat_completion(messages, model, temperature, max_tokens, stream)
            elif provider == "anthropic":
                return await self._anthropic_chat_completion(messages, model, temperature, max_tokens, stream)
            elif provider == "openrouter":
                return await self._openrouter_chat_completion(messages, model, temperature, max_tokens, stream)
            else:
                return {"error": f"Unknown provider: {provider}"}
        except Exception as e:
            return {"error": f"API request failed: {str(e)}"}

    async def _openai_chat_completion(self, messages: list[dict[str, str]], model: str, temperature: float, max_tokens: int | None, stream: bool):
        """Handle OpenAI chat completion requests."""
        response = await self.openai_client.chat.completions.create(model=model, messages=messages, temperature=temperature, max_tokens=max_tokens, stream=stream)

        if stream:

            async def response_generator():
                async for chunk in response:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content

            return response_generator()
        else:
            return {"content": response.choices[0].message.content}

    async def _anthropic_chat_completion(self, messages: list[dict[str, str]], model: str, temperature: float, max_tokens: int | None, stream: bool):
        """Handle Anthropic chat completion requests."""
        # Convert messages to Anthropic format
        system_message = next((m["content"] for m in messages if m["role"] == "system"), None)
        conversation = []
        for m in messages:
            if m["role"] != "system":
                conversation.append({"role": "assistant" if m["role"] == "assistant" else "user", "content": m["content"]})

        response = await self.anthropic_client.messages.create(model=model, messages=conversation, system=system_message, temperature=temperature, max_tokens=max_tokens, stream=stream)

        if stream:

            async def response_generator():
                async for chunk in response:
                    if chunk.delta.text:
                        yield chunk.delta.text

            return response_generator()
        else:
            return {"content": response.content[0].text}

    async def _openrouter_chat_completion(self, messages: list[dict[str, str]], model: str, temperature: float, max_tokens: int | None, stream: bool):
        """Handle OpenRouter chat completion requests."""
        response = await self.openrouter_client.chat.completions.create(model=model, messages=messages, temperature=temperature, max_tokens=max_tokens, stream=stream)

        if stream:

            async def response_generator():
                async for chunk in response:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content

            return response_generator()
        else:
            return {"content": response.choices[0].message.content}
