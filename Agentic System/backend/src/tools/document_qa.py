"""Document Q&A tool — Bedrock RetrieveAndGenerate with inline documents.

Answers questions about user-provided text content using Bedrock's
RetrieveAndGenerate API with ExternalSourcesConfiguration.
No pre-built knowledge base needed — the document is passed inline.
"""

import os

from langchain_core.tools import tool


@tool
def document_qa(question: str, document_text: str) -> str:
    """Answer a question based on the provided document text.

    Takes a question and document content, uses Bedrock to find
    relevant passages and generate an answer grounded in the document.
    Use when the user provides text and asks questions about it.
    """
    import boto3

    region = os.environ.get("AWS_REGION", "us-west-2")
    model_id = os.environ.get("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-6")

    if not document_text or not document_text.strip():
        return "No document text provided. Please provide the document content to search."

    # Truncate very long documents to avoid token limits
    max_chars = 50000
    if len(document_text) > max_chars:
        document_text = document_text[:max_chars] + "\n\n[Document truncated]"

    try:
        client = boto3.client("bedrock-agent-runtime", region_name=region)
        response = client.retrieve_and_generate(
            input={"text": question},
            retrieveAndGenerateConfiguration={
                "type": "EXTERNAL_SOURCES",
                "externalSourcesConfiguration": {
                    "modelArn": f"arn:aws:bedrock:{region}::foundation-model/{model_id}",
                    "sources": [
                        {
                            "sourceType": "BYTE_CONTENT",
                            "byteContent": {
                                "contentType": "text/plain",
                                "data": document_text.encode("utf-8"),
                                "identifier": "user-document",
                            },
                        }
                    ],
                },
            },
        )

        output = response.get("output", {}).get("text", "")
        if not output:
            return f"Could not find an answer to '{question}' in the provided document."

        return output

    except Exception as e:
        return f"Document Q&A failed: {str(e)}"
