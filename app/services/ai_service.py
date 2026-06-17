"""OpenAI service + Agent service — Chat Completions wrapper with retry + tool calling loop."""
import json
import logging
from typing import Optional, List

from openai import AsyncOpenAI, APIError, RateLimitError, APIConnectionError
from sqlmodel import Session
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from app.core.config import settings
from app.services.tool_executors import ToolExecutors
from app.services.guardrails import validate_tool_args, sanitize_for_openai
from app.tools.definitions import CLEARJOURNAL_TOOLS

logger = logging.getLogger(__name__)


class OpenAIService:
    """Thin wrapper around the OpenAI Chat Completions API."""

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.AGENT_MODEL
        self.max_response_tokens = settings.AGENT_MAX_RESPONSE_TOKENS

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((APIConnectionError, RateLimitError)),
        reraise=True,
    )
    async def chat(
        self,
        messages: List[dict],
        system: Optional[str] = None,
        tools: Optional[List[dict]] = None,
        tool_choice: str = "auto",
    ):
        """
        Send a chat completion request to OpenAI.

        Args:
            messages: Conversation history as list of role/content dicts.
            system: System prompt (injected as first message if provided).
            tools: Tool definitions for function calling.
            tool_choice: "auto", "none", or "required".

        Returns:
            OpenAI ChatCompletion response object.
        """
        # Build message list with optional system prompt
        full_messages = []
        if system:
            full_messages.append({"role": "system", "content": system})
        full_messages.extend(messages)

        kwargs = {
            "model": self.model,
            "messages": full_messages,
            "max_tokens": self.max_response_tokens,
        }

        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice

        try:
            response = await self.client.chat.completions.create(**kwargs)
            logger.debug(
                "OpenAI response: model=%s, tokens=%s",
                response.model,
                response.usage,
            )
            return response

        except RateLimitError:
            logger.warning("OpenAI rate limit hit — retrying with backoff")
            raise
        except APIConnectionError:
            logger.warning("OpenAI connection error — retrying")
            raise
        except APIError as e:
            logger.error("OpenAI API error: %s", e)
            raise

    async def chat_no_tools(
        self,
        messages: List[dict],
        system: Optional[str] = None,
    ) -> str:
        """
        Simple non-tool chat (used for auto-title generation, etc.).
        Returns just the response text.
        """
        response = await self.chat(
            messages=messages,
            system=system,
            tools=None,
            tool_choice="none",
        )
        return response.choices[0].message.content or ""


# ═══════════════════════════════════════════════════════════════════════════════
# Agent Service — Tool Calling Loop
# ═══════════════════════════════════════════════════════════════════════════════


class AgentError(Exception):
    """Base agent error."""
    pass


class AgentMaxIterationsError(AgentError):
    """Raised when agent exceeds max tool call iterations."""
    pass


class ToolExecutionError(AgentError):
    """Raised when a tool execution fails."""
    pass


class AgentService:
    """
    Tool calling loop: think → call tools → think again → respond.
    Orchestrates OpenAI calls and tool execution.
    """

    MAX_TOOL_CALLS = settings.AGENT_MAX_TOOL_CALLS

    def __init__(self, session: Session):
        self.openai = OpenAIService()
        self.executors = ToolExecutors(session=session)

    async def run(
        self,
        messages: List[dict],
        system_prompt: str,
        user_id: int,
    ) -> dict:
        """
        Run the agent loop. May make multiple OpenAI calls with tool invocations.

        Args:
            messages: Conversation history (role/content dicts).
            system_prompt: System prompt for the AI.
            user_id: Owner of the data (scoping tool calls).

        Returns:
            dict with keys: text, tool_calls, usage
        """
        tool_calls_made: List[dict] = []
        tool_results_data: List[dict] = []
        iteration = 0
        accumulated_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        while iteration < self.MAX_TOOL_CALLS:
            iteration += 1

            try:
                response = await self.openai.chat(
                    messages=messages,
                    system=system_prompt,
                    tools=CLEARJOURNAL_TOOLS,
                    tool_choice="auto",
                )
            except (RateLimitError, APIConnectionError, APIError) as e:
                raise AgentError(f"OpenAI API error: {e}") from e

            choice = response.choices[0]

            # Accumulate token usage
            if response.usage:
                accumulated_usage["prompt_tokens"] += response.usage.prompt_tokens
                accumulated_usage["completion_tokens"] += response.usage.completion_tokens
                accumulated_usage["total_tokens"] += response.usage.total_tokens

            # Case 1: Agent is done — return text response
            if choice.finish_reason == "stop":
                return {
                    "text": choice.message.content or "",
                    "tool_calls": tool_calls_made,
                    "tool_results": tool_results_data,
                    "usage": accumulated_usage,
                    "model": response.model,
                    "finish_reason": "stop",
                }

            # Case 2: Hit max_tokens — return partial response
            if choice.finish_reason == "length":
                text = (choice.message.content or "") + \
                       "\n\n*(Response truncated — try asking a more specific question.)*"
                return {
                    "text": text,
                    "tool_calls": tool_calls_made,
                    "tool_results": tool_results_data,
                    "usage": accumulated_usage,
                    "model": response.model,
                    "finish_reason": "length",
                }

            # Case 3: Agent wants to call tools
            if choice.finish_reason == "tool_calls" and choice.message.tool_calls:
                # Append the assistant's tool call message
                messages.append(choice.message)

                for tool_call in choice.message.tool_calls:
                    tool_name = tool_call.function.name
                    try:
                        tool_args = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError:
                        tool_args = {}

                    # Guardrail: validate + cap tool arguments
                    tool_args = validate_tool_args(tool_name, tool_args)

                    # Execute tool against existing services
                    tool_result = await self.executors.execute(tool_name, tool_args, user_id)

                    # Guardrail: scrub PII before sending back to OpenAI
                    tool_result = sanitize_for_openai(tool_result)

                    tool_results_data.append(tool_result)
                    tool_calls_made.append({"tool": tool_name, "args": tool_args})
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(tool_result, default=str),
                    })
                continue

            # Case 4: Unexpected finish_reason or empty tool_calls — break gracefully
            logger.warning(
                "Unexpected finish_reason='%s' with empty tool_calls at iteration %d",
                choice.finish_reason, iteration,
            )
            return {
                "text": choice.message.content or "I'm having trouble processing that. Please try rephrasing.",
                "tool_calls": tool_calls_made,
                "tool_results": tool_results_data,
                "usage": accumulated_usage,
                "model": response.model,
                "finish_reason": choice.finish_reason or "unknown",
            }

        # Exceeded max iterations
        raise AgentMaxIterationsError(
            f"Agent exceeded {self.MAX_TOOL_CALLS} tool call iterations"
        )
