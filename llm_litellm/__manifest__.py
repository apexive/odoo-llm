{
    "name": "LiteLLM Proxy Integration",
    "summary": "LiteLLM proxy integration for LLM module",
    "description": """
        Implements LiteLLM proxy service for the LLM integration module.
        Supports proxying requests to various LLM providers through a central LiteLLM proxy server.
        
        Features:
        - Chat completions with streaming support
        - Text embeddings 
        - Model listing
        - Rate limiting and cost tracking through proxy
    """,
    "category": "Technical",
    "version": "16.0.1.0.0",
    "depends": ["llm"],
    "external_dependencies": {
        "python": ["requests"],
    },
    "data": [
        "data/llm_publisher.xml",
    ],
    "license": "LGPL-3",
    "installable": True,
}