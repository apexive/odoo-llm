{
    "name": "LLM Integration",
    "summary": """
        Integration with various LLM providers like Ollama, OpenAI, Replicate and Anthropic""",
    "description": """
        Provides integration with LLM (Large Language Model) providers for:
        - Chat completions
        - Text embeddings
        - Model management

        Supported providers:
        - OpenAI
        - Ollama
        - Replicate
        - Anthropic
    """,
    "author": "Apexive Solutions LLC",
    "website": "https://github.com/smartops-aero/flight",
    "category": "Technical",
    "version": "16.0.1.0.0",
    "depends": ["base"],
    "data": [
        "security/ir.model.access.csv",
        "views/llm_views.xml",
        "views/llm_thread_views.xml",
    ],
    "installable": True,
}
