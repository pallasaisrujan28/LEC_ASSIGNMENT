"""Memory — checkpointer, store, and conversation summary.

Handles:
1. Short-term: AgentCoreMemorySaver checkpointer (persists graph state per thread)
2. Messages: LangGraph add_messages accumulates HumanMessage/AIMessage across turns
3. Summary: After 7+ message pairs, older messages are summarized by the LLM
   and replaced with a single SystemMessage summary to save tokens.

The summary is stored in the messages list itself — old messages get replaced
with a compact summary, keeping only the last few turns verbatim.
"""

import os

from langchain_aws import ChatBedrockConverse
from langchain_core.messages import AnyMessage, HumanMessage, AIMessage, SystemMessage
from langgraph_checkpoint_aws import AgentCoreMemorySaver

SUMMARY_THRESHOLD = 5  # Summarize after this many human+AI pairs
KEEP_RECENT = 2  # Keep this many recent pairs unsummarized

SUMMARIZE_PROMPT = """Summarize this conversation concisely. Capture:
- Key facts, numbers, and data mentioned
- Questions asked and answers given
- Decisions made or conclusions reached
Keep it short but preserve all important details."""


def get_checkpointer():
    """Get the AgentCore Memory checkpointer."""
    memory_id = os.environ.get("AGENTCORE_MEMORY_ID")
    region = os.environ.get("AWS_REGION", "us-west-2")
    return AgentCoreMemorySaver(memory_id, region_name=region)


def _get_llm():
    return ChatBedrockConverse(
        model=os.environ.get("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-6"),
        region_name=os.environ.get("AWS_REGION", "us-west-2"),
    )


def _count_pairs(messages: list[AnyMessage]) -> int:
    """Count human+AI message pairs (ignoring system messages)."""
    human_count = sum(1 for m in messages if isinstance(m, HumanMessage))
    return human_count


def _summarize_messages(messages: list[AnyMessage]) -> str:
    """Use the LLM to summarize a list of messages."""
    llm = _get_llm()
    history = "\n".join(
        f"{'User' if isinstance(m, HumanMessage) else 'Agent'}: {m.content}"
        for m in messages
        if isinstance(m, (HumanMessage, AIMessage))
    )
    response = llm.invoke([
        SystemMessage(content=SUMMARIZE_PROMPT),
        HumanMessage(content=history),
    ])
    return response.content


def maybe_summarize(messages: list[AnyMessage]) -> list[AnyMessage]:
    """If messages exceed the threshold, summarize older ones.

    Returns a new messages list with:
    - A SystemMessage containing the summary of older turns
    - The most recent KEEP_RECENT pairs kept verbatim

    If under threshold, returns messages unchanged.
    """
    pairs = _count_pairs(messages)
    if pairs < SUMMARY_THRESHOLD:
        return messages

    # Find existing summary (if any)
    existing_summary = ""
    non_system = []
    for m in messages:
        if isinstance(m, SystemMessage) and m.content.startswith("CONVERSATION SUMMARY:"):
            existing_summary = m.content
        else:
            non_system.append(m)

    # Split into old (to summarize) and recent (to keep)
    # Count from the end to find the last KEEP_RECENT pairs
    keep_count = KEEP_RECENT * 2  # each pair = human + AI
    if len(non_system) <= keep_count:
        return messages

    to_summarize = non_system[:-keep_count]
    to_keep = non_system[-keep_count:]

    # Build summary
    summary_input = []
    if existing_summary:
        summary_input.append(SystemMessage(content=existing_summary))
    summary_input.extend(to_summarize)

    try:
        summary_text = _summarize_messages(summary_input)
    except Exception:
        return messages  # If summarization fails, keep messages as-is

    # Return: summary + recent messages
    return [
        SystemMessage(content=f"CONVERSATION SUMMARY:\n{summary_text}"),
        *to_keep,
    ]


def get_conversation_context(messages: list[AnyMessage]) -> str:
    """Extract conversation context string from messages for the planner.

    Returns a formatted string of previous turns, or empty string if no history.
    """
    if not messages or len(messages) <= 1:
        return ""

    parts = []
    for msg in messages[:-1]:  # Exclude current query (last message)
        if isinstance(msg, SystemMessage) and msg.content.startswith("CONVERSATION SUMMARY:"):
            parts.append(msg.content)
        elif isinstance(msg, HumanMessage):
            parts.append(f"User: {msg.content}")
        elif isinstance(msg, AIMessage):
            parts.append(f"Agent: {msg.content}")

    if not parts:
        return ""

    return "\n".join(parts[-20:])  # Last 20 entries max
