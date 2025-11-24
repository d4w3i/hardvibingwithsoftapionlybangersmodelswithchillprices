"""AI service with agent factory pattern"""
from typing import AsyncGenerator, Optional
from abc import ABC, abstractmethod

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langgraph.prebuilt import create_react_agent
from langchain.schema import HumanMessage, AIMessage, SystemMessage


class BaseAIService(ABC):
    """Base class for AI services"""

    @abstractmethod
    async def chat(self, message: str, history: list = None) -> AsyncGenerator[str, None]:
        """
        Send a message and stream the response.

        Args:
            message: User message
            history: Optional conversation history

        Yields:
            Response chunks as they arrive
        """
        pass


class LangGraphService(BaseAIService):
    """LangGraph agent service"""

    def __init__(self, api_key: str, provider: str = "openai", model: str = None):
        """
        Initialize LangGraph agent.

        Args:
            api_key: API key for the provider
            provider: "openai" or "anthropic"
            model: Optional model name override
        """
        if provider == "openai":
            llm = ChatOpenAI(
                api_key=api_key,
                model=model or "gpt-4-turbo-preview",
                streaming=True
            )
        else:  # anthropic
            llm = ChatAnthropic(
                api_key=api_key,
                model=model or "claude-3-5-sonnet-20241022",
                streaming=True
            )

        # Create a simple agent (can be extended with tools)
        self.agent = create_react_agent(llm, tools=[])

    async def chat(self, message: str, history: list = None) -> AsyncGenerator[str, None]:
        """Stream chat response"""
        messages = []
        if history:
            for msg in history:
                if msg["role"] == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    messages.append(AIMessage(content=msg["content"]))
                elif msg["role"] == "system":
                    messages.append(SystemMessage(content=msg["content"]))

        messages.append(HumanMessage(content=message))

        async for event in self.agent.astream({"messages": messages}):
            # Extract content from agent events
            if "agent" in event and "messages" in event["agent"]:
                for msg in event["agent"]["messages"]:
                    if hasattr(msg, "content") and msg.content:
                        yield msg.content


class OpenAIDirectService(BaseAIService):
    """Direct OpenAI API service"""

    def __init__(self, api_key: str, model: str = "gpt-4-turbo-preview"):
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def chat(self, message: str, history: list = None) -> AsyncGenerator[str, None]:
        """Stream chat response"""
        messages = history or []
        messages.append({"role": "user", "content": message})

        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=True
        )

        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


class AnthropicDirectService(BaseAIService):
    """Direct Anthropic API service"""

    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
        from anthropic import AsyncAnthropic
        self.client = AsyncAnthropic(api_key=api_key)
        self.model = model

    async def chat(self, message: str, history: list = None) -> AsyncGenerator[str, None]:
        """Stream chat response"""
        # Convert history to Anthropic format
        messages = []
        if history:
            for msg in history:
                if msg["role"] in ["user", "assistant"]:
                    messages.append({"role": msg["role"], "content": msg["content"]})

        messages.append({"role": "user", "content": message})

        async with self.client.messages.stream(
            model=self.model,
            max_tokens=4096,
            messages=messages
        ) as stream:
            async for text in stream.text_stream:
                yield text


class AgentFactory:
    """Factory to create AI service instances based on agent type and provider"""

    @staticmethod
    def create(
        agent_type: str,
        provider: str,
        api_key: str,
        model: Optional[str] = None
    ) -> BaseAIService:
        """
        Create an AI service instance.

        Args:
            agent_type: Type of agent ("langgraph", "openai_direct", "anthropic_direct")
            provider: Provider ("openai" or "anthropic")
            api_key: Decrypted API key
            model: Optional model override

        Returns:
            AI service instance

        Raises:
            ValueError: If agent_type is not supported
        """
        if agent_type == "langgraph":
            return LangGraphService(api_key, provider, model)

        elif agent_type == "openai_direct":
            if provider != "openai":
                raise ValueError("openai_direct agent requires openai provider")
            return OpenAIDirectService(api_key, model or "gpt-4-turbo-preview")

        elif agent_type == "anthropic_direct":
            if provider != "anthropic":
                raise ValueError("anthropic_direct agent requires anthropic provider")
            return AnthropicDirectService(api_key, model or "claude-3-5-sonnet-20241022")

        else:
            raise ValueError(
                f"Unknown agent_type: {agent_type}. "
                f"Supported: langgraph, openai_direct, anthropic_direct"
            )
