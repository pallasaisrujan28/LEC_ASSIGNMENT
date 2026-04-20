"""Evaluation: ≥10 multi-step queries with graded success criteria.

Each query requires the agent to use 2+ tools (sequential or parallel).
Graded on: answer relevancy, factual correctness, and tool selection.
Success-rate = % of queries scoring above threshold.

Run with: deepeval test run tests/test_agent_eval.py
"""

import os
import sys
import time

import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase, LLMTestCaseParams, ToolCall
from deepeval.metrics import AnswerRelevancyMetric, ToolCorrectnessMetric, GEval
from deepeval.models import AmazonBedrockModel

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.agent.core.graph import run_agent

# ── Judge model (Bedrock, not OpenAI) ───────────────────────────────────

judge = AmazonBedrockModel(
    model="us.anthropic.claude-sonnet-4-6",
    region=os.environ.get("AWS_REGION", "us-west-2"),
)

# ── Grading criteria ────────────────────────────────────────────────────

answer_relevancy = AnswerRelevancyMetric(model=judge, threshold=0.7)
tool_correctness = ToolCorrectnessMetric(model=judge, threshold=0.5)

correctness = GEval(
    name="Correctness",
    model=judge,
    criteria="The actual output is factually correct and directly answers the query.",
    evaluation_params=[
        LLMTestCaseParams.INPUT,
        LLMTestCaseParams.ACTUAL_OUTPUT,
        LLMTestCaseParams.EXPECTED_OUTPUT,
    ],
    threshold=0.7,
)


# ── Helper ──────────────────────────────────────────────────────────────

def _evaluate(query, expected, expected_tools):
    import uuid
    start = time.time()
    thread_id = f"eval-{uuid.uuid4().hex[:8]}"
    result = run_agent(query, thread_id=thread_id)
    elapsed = time.time() - start

    tools_called = [
        ToolCall(name=o["tool"], output=o.get("result"))
        for o in result.get("observations", [])
    ]

    actual = result.get("final_answer") or "No answer produced."

    tc = LLMTestCase(
        input=query,
        actual_output=actual,
        expected_output=expected,
        tools_called=tools_called,
        expected_tools=[ToolCall(name=t) for t in expected_tools],
        token_cost=result.get("budget", {}).get("total_cost_usd", 0),
        completion_time=elapsed,
    )
    assert_test(tc, [answer_relevancy, tool_correctness, correctness])


# ── 12 multi-step queries ───────────────────────────────────────────────


def test_01_population_plus_percentage():
    _evaluate(
        "What is the population of Japan and what is 3% of it?",
        "Japan's population is approximately 124 million. 3% is about 3.72 million.",
        ["wiki_summary", "calculator"],
    )


def test_02_crypto_price_calculation():
    _evaluate(
        "Search for the current price of Bitcoin and calculate what 0.5 BTC is worth.",
        "Current Bitcoin price multiplied by 0.5.",
        ["web_search", "calculator"],
    )


def test_03_company_background_plus_news():
    _evaluate(
        "What is SpaceX according to Wikipedia, and what was their most recent launch?",
        "SpaceX is an American spacecraft manufacturer. Latest launch details.",
        ["wiki_summary", "web_search"],
    )


def test_04_gdp_percentage_and_news():
    _evaluate(
        "What is the GDP of Germany, what is 5% of it, and what are the latest economic headlines about Germany?",
        "Germany's GDP, 5% of it, and recent economic news.",
        ["wiki_summary", "calculator", "web_search"],
    )


def test_05_population_comparison():
    _evaluate(
        "What are the populations of France and the UK, and what is the difference?",
        "France ~69M, UK ~69M, difference is small.",
        ["wiki_summary", "calculator"],
    )


def test_06_ai_news_plus_background():
    _evaluate(
        "What are the latest AI breakthroughs in 2026, and give me a Wikipedia summary of the Transformer architecture?",
        "Latest AI news. Transformer is a deep learning architecture using self-attention.",
        ["web_search", "wiki_summary"],
    )


def test_07_chained_calculations():
    _evaluate(
        "What is 1500 * 12, then take 20% of that, then add 500?",
        "1500*12=18000, 20%=3600, +500=4100.",
        ["calculator"],
    )


def test_08_wiki_search_then_summary():
    _evaluate(
        "Search Wikipedia for articles about quantum computing, then summarize the main one.",
        "Quantum computing uses quantum mechanics for computation.",
        ["wiki_search", "wiki_summary"],
    )


def test_09_water_usage_calculation():
    _evaluate(
        "How many people live in Tokyo, and if each uses 250 liters of water per day, how many total liters is that?",
        "Tokyo ~14M people. 14M * 250 = 3.5 billion liters per day.",
        ["wiki_summary", "calculator"],
    )


def test_10_climate_plus_agreement():
    _evaluate(
        "What is the latest news about climate change, and what does Wikipedia say about the Paris Agreement?",
        "Latest climate news. The Paris Agreement is an international treaty on climate change.",
        ["web_search", "wiki_summary"],
    )


def test_11_area_comparison():
    _evaluate(
        "What is the area of Australia and the area of India? How many times bigger is Australia than India?",
        "Australia ~7.7M km², India ~3.3M km². Australia is about 2.3 times bigger.",
        ["wiki_summary", "calculator"],
    )


def test_12_tech_research():
    _evaluate(
        "Search the web for the latest Python release and get a Wikipedia summary of the Python programming language.",
        "Latest Python release info. Python is a high-level programming language.",
        ["web_search", "wiki_summary"],
    )
