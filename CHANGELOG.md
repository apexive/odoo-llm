# Changelog

All notable changes to the Odoo LLM Integration project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- **Process with AI Button Reliability**: Replaced unreliable bus notification with client action pattern (2025-12-02)

  - Bus/WebSocket notifications failed on cloud deployments with code 1006 connection issues
  - New approach uses `ir.actions.client` to navigate and open AI chat reliably
  - Added `pendingOpenInChatter` state to `llm.store` service for cross-navigation state
  - Removed redundant bus subscription code from chatter patch
  - Affected modules: `llm_assistant` (18.0.1.5.3), `llm_thread` (18.0.1.4.3)

- **Module Dependency Issue**: Fixed `prompt_id` field being referenced in `llm_thread` module without dependency on `llm_assistant` (2025-11-26)
  - Moved `prompt_id` serialization from `llm_thread/models/llm_thread.py` to `llm_assistant/models/llm_thread.py`
  - `llm_thread` can now be installed standalone without `llm_assistant`
  - `prompt_id` handling in `_thread_to_store()` now properly resides in the module that defines the field

### Added

- **Tool Event System**: Real-time tool execution tracking with streaming events (2025-01-12)
  - Added `tool_called` event when tool execution begins (`llm_tool/models/mail_message.py:120-128`)
  - Added `tool_succeeded` event when tool completes successfully (`llm_tool/models/mail_message.py:147-157`)
  - Added `tool_failed` event when tool execution fails (`llm_tool/models/mail_message.py:166-176`)
  - Events include comprehensive tool data: tool_call_id, tool_name, arguments, status, result/error
  - Events are yielded through existing generator chain for automatic propagation to Fleek platform

### Changed

- **Enhanced Tool Execution Flow**: `mail.message.execute_tool_call()` now emits real-time events (2025-01-12)
  - Tool execution status is now broadcasted in real-time for UI updates
  - Maintains backward compatibility with existing message-based status tracking
  - Events automatically flow through `yield from` chain to Fleek broadcasting system

### Technical Details

- Tool events are generated at key execution points in `execute_tool_call()` method
- Event structure follows consistent pattern with `type` and `tool_data` fields
- Integration with Fleek platform enables WebSocket broadcasting to clients
- Supports real-time tracking of image generation and other AI tool operations

## [16.0-pr] - 2025-01-04 - Major Architecture Consolidation

### Added

- **PostgreSQL Advisory Locking**: Prevents race conditions in concurrent generation scenarios
- **Unified Generation API**: New `generate()` method provides consistent interface for text, image, and other content types
- **Enhanced Message System**: Added `body_json` field to `mail.message` for structured data storage
- **Indexed Role Field**: New `llm_role` field for 10x faster message queries
- **Auto-Detection System**: Automatic prompt argument detection and schema synchronization
- **Schema Source Transparency**: Clear indication of schema sources in UI (Prompt vs Model vs None)
- **Loading State Management**: Proper async handling and loading indicators in forms
- **Comprehensive Test Coverage**: Tests for prompt arguments, thread schemas, and race condition fixes

### Changed

- **Module Consolidation**: Merged `llm_resource` functionality into `llm_knowledge` module
- **Prompt Integration**: Moved `llm_prompt` functionality into `llm_assistant` module
- **Message Subtypes**: Moved from separate module into base `llm` module
- **Tool Message Format**: All tool data now stored in `body_json` instead of separate fields
- **Assistant Management**: Enhanced with integrated prompt templates and testing capabilities
- **Generation Forms**: Improved with automatic schema detection and better error handling

### Removed

- **llm_resource module**: Consolidated into `llm_knowledge`
- **llm_prompt module**: Integrated into `llm_assistant`
- **llm_mail_message_subtypes module**: Moved to base `llm` module
- **Deprecated API methods**: Replaced with unified generation interface

### Fixed

- **Race Conditions**: Fixed async loading issues in media form components
- **Schema Computation**: Eliminated inconsistencies between template and arguments
- **Form Loading**: Prevented empty forms and incorrect field rendering
- **Context Management**: Improved handling of context changes and reloads
- **Tool Execution**: Better error handling and structured data storage
- **Performance Issues**: Optimized database queries with indexed fields

### Security

- **Enhanced Tool Consent**: Improved security framework for tool execution
- **Role-Based Access**: Strengthened permission-based tool access control

### Migration Notes

- **Automatic Migration**: All existing installations will be automatically migrated
- **Data Preservation**: No loss of existing messages and tool execution history
- **Backward Compatibility**: Maintains support for existing workflows during transition
- **Module Updates**: Dependencies automatically updated to reflect consolidations

## [Previous Releases]

### Module Version History

#### Core Modules

- **llm**: 16.0.1.3.0 (2025-01-04) - Message subtypes integration and role optimization
- **llm_assistant**: 16.0.1.4.0 (2025-01-04) - Integrated prompt templates and enhanced testing
- **llm_thread**: 16.0.1.3.0 (2025-01-04) - Role field optimization and PostgreSQL locking
- **llm_tool**: 16.0.3.0.0 (2025-01-04) - Body_json refactoring and enhanced execution
- **llm_generate**: 16.0.2.0.0 (2025-01-04) - Unified generation API and clean integration
- **llm_store**: 16.0.1.0.0 (2025-01-02) - Vector store abstraction framework

#### Provider Modules

- **llm_openai**: 16.0.1.1.3 (2025-01-04) - Enhanced tool support and API improvements
- **llm_anthropic**: 16.0.1.1.0 (2025-03-06) - Anthropic provider enhancements
- **llm_ollama**: 16.0.1.1.0 (2025-03-06) - Chat method parameter updates
- **llm_mistral**: 16.0.1.0.0 (2025-01-02) - Mistral AI integration
- **llm_litellm**: 16.0.1.1.0 (2025-03-06) - LiteLLM integration updates
- **llm_replicate**: 16.0.1.1.0 (2025-03-06) - Replicate provider improvements
- **llm_fal_ai**: 16.0.2.0.0 (2025-01-04) - Unified generate endpoint and schema storage

#### Knowledge & Vector Store Modules

- **llm_knowledge**: 16.0.1.1.0 (2025-01-04) - Consolidated resource management and RAG
- **llm_chroma**: 16.0.1.0.0 (2025-01-02) - ChromaDB vector store integration
- **llm_pgvector**: 16.0.1.0.0 (2025-01-02) - PostgreSQL vector extension
- **llm_qdrant**: 16.0.1.0.0 (2025-01-02) - Qdrant vector database integration

#### Specialized Modules

- **llm_mcp**: 16.0.1.0.0 (2025-01-02) - Model Context Protocol support
- **llm_training**: 16.0.1.0.0 (2025-01-02) - Fine-tuning capabilities
- **llm_tool_knowledge**: 16.0.1.0.0 (2025-01-02) - Knowledge base tool integration

### Historical Changes (2025)

#### January 2025

- **16.0.1.2.0** (llm_thread) - LLM base module message subtypes integration
- **16.0.1.0.1** (llm_tool) - Minor fixes and improvements

#### March 2025

- **16.0.1.1.0** (llm_thread) - Tool integration in chat interface
- **16.0.1.1.0** (multiple providers) - Chat method parameter updates

#### April 2025

- **16.0.1.1.1** (llm_thread) - Method name consistency updates
- **16.0.1.0.1** (llm_tool) - Additional fixes and improvements

## Performance Improvements

### Database Optimization

- **10x Query Performance**: Indexed `llm_role` field eliminates expensive subtype lookups
- **Reduced Complexity**: Consolidated modules reduce maintenance overhead
- **Optimized Frontend**: Direct field access instead of computed role checking

### User Experience

- **Smoother Loading**: Proper async handling prevents UI flashing
- **Real-time Updates**: Enhanced streaming generation with live feedback
- **Better Error Handling**: Comprehensive error messages and fallback handling

## Migration Guide

### From llm_resource to llm_knowledge

1. **Automatic Process**: Migration script handles module transition
2. **Data Preservation**: All resources, collections, and embeddings preserved
3. **API Compatibility**: All existing methods continue to work
4. **Dependency Updates**: Module dependencies automatically updated

### From Separate Prompt Module

1. **Seamless Integration**: Prompts now managed within assistants
2. **Enhanced Features**: Auto-detection and testing capabilities added
3. **Template Compatibility**: All existing templates continue to work
4. **Improved UI**: Integrated prompt management in assistant interface

### Tool System Migration

1. **Structured Data**: Tool results now in `body_json` format
2. **Enhanced Execution**: Better error handling and result storage
3. **MCP Compatibility**: Improved Model Context Protocol integration
4. **Provider Support**: Unified tool calling across all providers

## Compatibility Matrix

| Module Version | Odoo Version | Python Version | Dependencies |
| -------------- | ------------ | -------------- | ------------ |
| 16.0.x.x.x     | 16.0+        | 3.8+           | mail, web    |

## Support & Resources

- **Issues**: [GitHub Issues](https://github.com/apexive/odoo-llm/issues)
- **Documentation**: [GitHub Repository](https://github.com/apexive/odoo-llm)
- **Discussions**: [GitHub Discussions](https://github.com/apexive/odoo-llm/discussions)

---

_For more detailed technical information, see [OVERVIEW.md](OVERVIEW.md) for architecture details._
