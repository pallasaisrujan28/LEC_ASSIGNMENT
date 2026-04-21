"""Knowledge Base Lookup tool — Bedrock Knowledge Base with S3 Vectors.

Searches a pre-built, curated knowledge base for relevant information.
Uses Bedrock's Retrieve API to find matching passages from indexed documents.
"""

import os

from langchain_core.tools import tool


@tool
def knowledge_base_lookup(query: str, max_results: int = 5) -> list[dict]:
    """Search the knowledge base for information relevant to the query.

    Searches a curated, pre-indexed knowledge base backed by Bedrock
    with S3 Vectors. Returns matching passages with source references.
    """
    import boto3

    kb_id = os.environ.get("BEDROCK_KB_ID")
    region = os.environ.get("AWS_REGION", "us-west-2")

    if not kb_id:
        return [{"content": "Knowledge base not configured (BEDROCK_KB_ID not set)", "source": ""}]

    try:
        client = boto3.client("bedrock-agent-runtime", region_name=region)
        response = client.retrieve(
            knowledgeBaseId=kb_id,
            retrievalQuery={"text": query},
            retrievalConfiguration={
                "vectorSearchConfiguration": {
                    "numberOfResults": max_results,
                }
            },
        )

        results = []
        for r in response.get("retrievalResults", []):
            content = r.get("content", {}).get("text", "")
            source = r.get("location", {}).get("s3Location", {}).get("uri", "")
            score = r.get("score", 0)
            results.append({
                "content": content,
                "source": source,
                "score": round(score, 4) if score else 0,
            })

        if not results:
            return [{"content": f"No results found in knowledge base for: {query}", "source": "", "score": 0}]

        return results

    except Exception as e:
        return [{"content": f"Knowledge base search failed: {str(e)}", "source": "", "score": 0}]
