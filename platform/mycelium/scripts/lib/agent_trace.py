"""
Agent Trace — captures the conversation between agents and their tools.

Wraps the Agent SDK query() to log every message: tool calls, responses,
reasoning. This is how we see agents speaking to Asgard in real-time.

Usage (in any agent):
    from scripts.lib.agent_trace import traced_query

    async for message in traced_query(prompt, options, trace_name="synthesis"):
        if isinstance(message, ResultMessage):
            ...

The trace writes to knowledge/meta/traces/{trace_name}-latest.log
in real-time (each message flushed immediately).
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncIterator, Any

from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage
from claude_agent_sdk.types import (
    AssistantMessage, UserMessage, SystemMessage,
    TextBlock, ToolUseBlock, ToolResultBlock,
)

TRACE_DIR = Path(__file__).resolve().parent.parent.parent / "knowledge" / "meta" / "traces"


def _format_content_block(block) -> str:
    """Format a content block for logging."""
    if isinstance(block, TextBlock):
        text = block.text[:200] if hasattr(block, 'text') else str(block)[:200]
        return f"  [text] {text}..."
    elif isinstance(block, ToolUseBlock):
        input_str = json.dumps(block.input, default=str)[:300] if block.input else ""
        return f"  [tool_use] {block.name}: {input_str}"
    elif isinstance(block, ToolResultBlock):
        content = str(block.content)[:200] if hasattr(block, 'content') else str(block)[:200]
        return f"  [tool_result] {content}"
    else:
        return f"  [{type(block).__name__}] {str(block)[:200]}"


async def traced_query(
    prompt: str,
    options: ClaudeAgentOptions,
    trace_name: str = "agent",
) -> AsyncIterator[Any]:
    """
    Wrap Agent SDK query() with real-time trace logging.

    Yields the same messages as query(). Additionally writes each
    message to a trace log file for real-time monitoring.
    """
    TRACE_DIR.mkdir(parents=True, exist_ok=True)
    trace_file = TRACE_DIR / f"{trace_name}-latest.log"

    turn = 0
    with open(trace_file, "w") as tf:
        tf.write(f"=== {trace_name} trace started at {datetime.now(timezone.utc).isoformat()} ===\n\n")
        tf.flush()

        async for message in query(prompt=prompt, options=options):
            # Log based on message type
            if isinstance(message, AssistantMessage):
                turn += 1
                tf.write(f"--- Turn {turn} [assistant] ---\n")
                for block in (message.content or []):
                    tf.write(_format_content_block(block) + "\n")
                tf.write("\n")
                tf.flush()

            elif isinstance(message, UserMessage):
                if hasattr(message, 'tool_use_result') and message.tool_use_result:
                    result_str = str(message.tool_use_result).get('content', str(message.tool_use_result))[:500] if isinstance(message.tool_use_result, dict) else str(message.tool_use_result)[:500]
                    tf.write(f"  [tool_response] {result_str}\n\n")
                elif hasattr(message, 'content'):
                    content = message.content if isinstance(message.content, str) else str(message.content)[:300]
                    tf.write(f"  [user] {content}\n\n")
                tf.flush()

            elif isinstance(message, ResultMessage):
                tf.write(f"\n=== {trace_name} complete ===\n")
                tf.write(f"  Duration: {message.duration_ms / 1000:.1f}s\n")
                tf.write(f"  Turns: {message.num_turns}\n")
                if message.total_cost_usd:
                    tf.write(f"  Cost: ${message.total_cost_usd:.4f}\n")
                if message.is_error:
                    tf.write(f"  ERROR: {message.errors}\n")
                tf.flush()

            # Always yield the original message
            yield message
