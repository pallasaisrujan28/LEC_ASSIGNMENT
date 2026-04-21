"""Executor node — dispatches tool calls, parallel when independent.

Uses topological sort on the dependency graph to determine execution order.
Independent steps within the same level run in parallel via asyncio.gather.
Failed tools are retried once, then reported as errors.
"""

import asyncio
import logging
from collections import defaultdict

from src.agent.core.state import AgentState, Observation

logger = logging.getLogger("agent.executor")
MAX_RETRIES = 2


def _build_execution_groups(steps) -> list[list]:
    """Topological sort: group steps by dependency level for parallel execution."""
    # Map step_id -> step
    step_map = {s.step_id: s for s in steps}
    # Track which steps are resolved
    resolved = set()
    groups = []

    remaining = list(steps)
    while remaining:
        # Find steps whose dependencies are all resolved
        ready = [s for s in remaining if all(d in resolved for d in s.depends_on)]
        if not ready:
            # Circular dependency or missing dep — just run remaining sequentially
            groups.append(remaining)
            break
        groups.append(ready)
        for s in ready:
            resolved.add(s.step_id)
        remaining = [s for s in remaining if s.step_id not in resolved]

    return groups


def _get_tool_map(tools: list) -> dict:
    """Build a map of tool name -> tool callable."""
    return {t.name: t for t in tools}


async def _execute_step(step, tool_map, prev_results) -> Observation:
    """Execute a single plan step with retry logic."""
    logger.info(f"[EXECUTOR] Executing step {step.step_id}: tool={step.tool}, args={step.args}")

    tool = tool_map.get(step.tool)
    if not tool:
        logger.error(f"[EXECUTOR] Unknown tool: {step.tool}")
        return Observation(
            step_id=step.step_id,
            tool=step.tool,
            success=False,
            error=f"Unknown tool: {step.tool}",
        )

    # Substitute dependency results into args
    args = dict(step.args)
    for key, val in args.items():
        if isinstance(val, str):
            for dep_id, dep_result in prev_results.items():
                placeholder = f"{{{{{dep_id}}}}}"
                if placeholder in val:
                    val = val.replace(placeholder, str(dep_result))
            args[key] = val

    # Execute with retry
    for attempt in range(MAX_RETRIES):
        try:
            result = await tool.ainvoke(args)
            logger.info(f"[EXECUTOR] Step {step.step_id} ({step.tool}) SUCCESS: {str(result)[:200]}")
            return Observation(
                step_id=step.step_id,
                tool=step.tool,
                success=True,
                result=result,
            )
        except Exception as e:
            logger.warning(f"[EXECUTOR] Step {step.step_id} ({step.tool}) attempt {attempt+1} FAILED: {e}")
            if attempt == MAX_RETRIES - 1:
                return Observation(
                    step_id=step.step_id,
                    tool=step.tool,
                    success=False,
                    error=f"Failed after {MAX_RETRIES} attempts: {e}",
                )

    # Should not reach here
    return Observation(
        step_id=step.step_id, tool=step.tool, success=False, error="Unexpected"
    )


async def _execute_plan_async(steps, tools) -> list[Observation]:
    """Execute plan steps respecting dependencies, parallel when possible."""
    tool_map = _get_tool_map(tools)
    groups = _build_execution_groups(steps)
    all_observations = []
    prev_results = {}  # step_id -> result

    for group in groups:
        # Run all steps in this group in parallel
        tasks = [_execute_step(s, tool_map, prev_results) for s in group]
        observations = await asyncio.gather(*tasks)
        for obs in observations:
            all_observations.append(obs)
            if obs.success:
                prev_results[obs.step_id] = obs.result

    return all_observations


async def executor_node(state: AgentState) -> dict:
    """Execute the current plan's steps."""
    from src.tools import get_all_tools

    plan = state["plan"]
    if not plan or not plan.steps:
        logger.info("[EXECUTOR] No plan or empty steps — skipping execution")
        return {"observations": []}

    logger.info(f"[EXECUTOR] Executing plan with {len(plan.steps)} steps")
    tools = get_all_tools()
    observations = await _execute_plan_async(plan.steps, tools)

    # Append to existing observations
    existing = list(state.get("observations", []))
    existing.extend(observations)

    return {"observations": existing}
