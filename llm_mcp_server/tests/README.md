# MCP Server Test Scripts

Two focused test scripts for the LLM MCP Server module.

## Test Scripts

### 🔒 `test_stateful.sh`

**Tests MCP server in stateful mode with session management**

Tests:

- Health check endpoint
- Initialize method with session creation
- Session ID extraction from response headers
- notifications/initialized with session
- tools/list (authenticated discovery)
- ping method
- tools/call (authenticated with session)
- Error handling

**Usage:**

```bash
cd tests/
./test_stateful.sh
# Script will prompt for API key if MCP_API_KEY env var not set
```

### 🔓 `test_stateless.sh`

**Tests MCP server in stateless mode without sessions**

Tests:

- Health check endpoint
- Initialize method (no session)
- tools/list (direct access)
- ping method
- tools/call (authenticated, no session)
- Error handling

**Usage:**

```bash
cd tests/
./test_stateless.sh
# Script will prompt for API key if MCP_API_KEY env var not set
```

## Configuration

### API Key Input

Both scripts support interactive API key input. If the `MCP_API_KEY` environment variable is not set, the scripts will prompt you to enter your API key:

```bash
# Option 1: Set environment variable (no prompt)
export MCP_API_KEY="your_actual_api_key"
./test_stateful.sh

# Option 2: Interactive input (script will prompt)
./test_stateful.sh
# Script will ask: "🔑 Enter your Odoo API key:"
```

### Environment Variables

- `MCP_API_KEY` - Your Odoo API key (optional, will prompt if not set)
- `MCP_BASE_URL` - Server URL (default: `http://localhost:8069/mcp`)

### Getting Your API Key

1. Go to **LLM → Configuration → MCP Server** in Odoo
2. Copy the API key value
3. Or follow: https://www.odoo.com/documentation/17.0/developer/reference/external_api.html#api-keys

## Expected Results

### ✅ Success Indicators

- All tests pass with green checkmarks
- HTTP 200 responses for most endpoints
- HTTP 202 for notifications/initialized
- Valid JSON-RPC responses
- Session ID properly extracted from headers (stateful mode)
- Authenticated requests work with Bearer token

### ⚠️ Expected "Failures"

- `resources/list` and `prompts/list` return "Method not found" (this is correct)
- `tools/call` may error if no tools are configured (normal)
- Invalid methods return JSON-RPC error responses (expected behavior)

## Troubleshooting

### Common Issues

**❌ "API key is required"**

- Solution: Either set `export MCP_API_KEY="your_key_here"` or run script interactively

**❌ Connection refused**

- Check Odoo is running on port 8069
- Verify `llm_mcp_server` module is installed

**❌ 401 Unauthorized**

- Verify API key is correct
- Check API key has proper permissions

**❌ Session errors (stateful mode)**

- Check that session ID is properly extracted from headers
- Restart Odoo if session handling seems broken
- Verify Mcp-Session-Id header is sent with subsequent requests

### Debug Mode

Add `-v` to curl commands in scripts for verbose output:

```bash
curl -v -s -X POST ...
```

## Test Architecture

These tests are designed for our **simplified MCP server architecture**:

- ✅ **Stateful mode only** (no stateless/SSE complexity)
- ✅ **Standard HTTP/JSON** (no SSE streaming)
- ✅ **Bearer authentication** (no complex auth flows)
- ✅ **Session management** (create, use, cleanup)

The tests focus on **real-world usage patterns** rather than protocol edge cases.
