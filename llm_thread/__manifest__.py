{
    "name": "Easy AI Chat",
    "summary": "Simple AI Chat for Odoo",
    "description": """
Easy AI Chat for Odoo
=====================
A user-friendly module that brings AI-powered chat to your Odoo environment. Integrate with multiple AI providers, manage real-time conversations, and enhance workflows with multimodal support.

Key Features:
- Multiple AI Providers: OpenAI, Anthropic, Grok, Ollama, DeepSeek, and more
- Real-Time Chat: Instant AI conversations integrated with Odoo's mail system
- Multimodal Support: Go beyond text with advanced AI models
- Full Odoo Integration: Link chats to any Odoo record for context
- Tool Integration: Enable AI to execute custom tools and functions
- Function Calling: Select specific tools for each thread to enhance AI capabilities
- Optimized Performance: Efficient role-based message handling for better performance

Recent Updates:
- Refactored to use stored llm_role field for maximum efficiency
- Improved performance with direct field filtering and comparison
- Better integration with LLM base module's stored role field
- Enhanced database performance with proper indexing on llm_role field

Getting Started:
1. Install this module and the "LLM Integration Base" dependency
2. Configure your AI provider API keys
3. Fetch available models with one click
4. Start chatting from anywhere in Odoo

Use cases include customer support automation, data analysis, training assistance, custom AI workflows, and automated tool execution for your business.

Contact: support@apexive.com
    """,
    "category": "Productivity, Discuss",
    "version": "17.0.1.4.5",
    "depends": ["base", "mail", "web", "llm", "llm_tool"],
    "author": "Apexive Solutions LLC",
    "website": "https://github.com/apexive/odoo-llm",
    "external_dependencies": {"python": ["emoji", "markdown2"]},
    "data": [
        "security/llm_thread_security.xml",
        "security/ir.model.access.csv",
        "views/llm_thread_views.xml",
        "views/menu.xml",
    ],
    "assets": {
        "web.assets_backend": [
            # Services - LLM store service for integration with mail.store
            "llm_thread/static/src/services/llm_store_service.js",
            # Components - LLM Chat Container using existing mail components
            "llm_thread/static/src/components/llm_chat_container/llm_chat_container.js",
            "llm_thread/static/src/components/llm_chat_container/llm_chat_container.xml",
            "llm_thread/static/src/components/llm_chat_container/llm_chat_container.scss",
            # Thread Header component with provider/model/tool selections
            "llm_thread/static/src/components/llm_thread_header/llm_thread_header.js",
            "llm_thread/static/src/components/llm_thread_header/llm_thread_header.xml",
            "llm_thread/static/src/components/llm_thread_header/llm_thread_header.scss",
            # Related Record component for linking threads to Odoo records
            "llm_thread/static/src/components/llm_related_record/llm_related_record.js",
            "llm_thread/static/src/components/llm_related_record/llm_related_record.xml",
            "llm_thread/static/src/components/llm_related_record/llm_related_record.scss",
            "llm_thread/static/src/components/llm_related_record/llm_record_picker_dialog.js",
            "llm_thread/static/src/components/llm_related_record/llm_record_picker_dialog.xml",
            # Tool Message component for displaying tool results
            "llm_thread/static/src/components/llm_tool_message/llm_tool_message.js",
            "llm_thread/static/src/components/llm_tool_message/llm_tool_message.xml",
            "llm_thread/static/src/components/llm_tool_message/llm_tool_message.scss",
            # Patches - Safe extensions of mail components with conditional LLM logic
            "llm_thread/static/src/patches/composer_patch.js",
            "llm_thread/static/src/patches/composer_patch.xml",
            "llm_thread/static/src/patches/thread_patch.js",
            "llm_thread/static/src/patches/thread_model_patch.js",
            "llm_thread/static/src/patches/chatter_patch.js",
            "llm_thread/static/src/patches/message_patch.js",
            "llm_thread/static/src/patches/message_patch.xml",
            # Templates - Extensions of existing mail templates
            "llm_thread/static/src/templates/chatter_ai_button.xml",
            "llm_thread/static/src/templates/llm_chat_client_action.xml",
            # Client Actions - Following Odoo 18.0 patterns
            "llm_thread/static/src/client_actions/llm_chat_client_action.js",
            "llm_thread/static/src/client_actions/open_chatter_action.js",
        ],
    },
    "images": [
        "static/description/banner.jpeg",
    ],
    "license": "LGPL-3",
    "installable": True,
    "application": True,
    "auto_install": False,
}
