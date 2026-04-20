"""AgentCore Memory setup — checkpointer (short-term) + store (long-term)."""

import os

from langgraph_checkpoint_aws import AgentCoreMemorySaver


def get_checkpointer():
    """Get the AgentCore Memory checkpointer."""
    memory_id = os.environ.get("AGENTCORE_MEMORY_ID")
    region = os.environ.get("AWS_REGION", "us-west-2")
    return AgentCoreMemorySaver(memory_id, region_name=region)


def get_store():
    """Get the AgentCore Memory long-term store."""
    memory_id = os.environ.get("AGENTCORE_MEMORY_ID")
    region = os.environ.get("AWS_REGION", "us-west-2")

    from langgraph_checkpoint_aws import AgentCoreMemoryStore

    return AgentCoreMemoryStore(memory_id, region_name=region)
