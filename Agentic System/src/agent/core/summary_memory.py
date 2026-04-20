"""Summary memory via AgentCore Memory's built-in SummaryMemoryStrategy.

AgentCore Memory automatically generates session summaries in the background
when messages are saved via the store. We retrieve these summaries before
planning to give the agent conversation context.

Flow:
1. After each agent response → save the exchange to AgentCoreMemoryStore
2. AgentCore processes it in the background → extracts summaries
3. Before next query → retrieve summaries and inject into planner prompt
"""

import os
import uuid

from langchain_core.messages import HumanMessage, AIMessage
from langgraph_checkpoint_aws import AgentCoreMemoryStore


def _get_store() -> AgentCoreMemoryStore:
    memory_id = os.environ.get("AGENTCORE_MEMORY_ID")
    region = os.environ.get("AWS_REGION", "us-west-2")
    return AgentCoreMemoryStore(memory_id, region_name=region)


def save_exchange(actor_id: str, thread_id: str, query: str, answer: str):
    """Save a human+AI exchange to AgentCore Memory for summary extraction.

    AgentCore's SummaryMemoryStrategy will process this in the background
    and generate/update session summaries automatically.
    """
    store = _get_store()
    namespace = (actor_id, thread_id)

    # Save the human message
    store.put(
        namespace,
        str(uuid.uuid4()),
        {"message": HumanMessage(content=query)},
    )
    # Save the AI response
    store.put(
        namespace,
        str(uuid.uuid4()),
        {"message": AIMessage(content=answer)},
    )


def retrieve_summary(actor_id: str, thread_id: str, query: str) -> str:
    """Retrieve relevant memories/summaries for the current query.

    Uses AgentCore's semantic search over stored memories to find
    relevant context from past exchanges in this session.
    Returns empty string if no relevant memories found.
    """
    store = _get_store()
    namespace = ("summaries", actor_id, thread_id)

    try:
        results = store.search(namespace, query=query, limit=3)
        if not results:
            return ""

        summaries = []
        for item in results:
            val = item.value
            if isinstance(val, dict) and "message" in val:
                summaries.append(str(val["message"]))
            elif isinstance(val, str):
                summaries.append(val)

        if summaries:
            return "CONVERSATION CONTEXT (from memory):\n" + "\n".join(summaries)
    except Exception:
        pass

    return ""
