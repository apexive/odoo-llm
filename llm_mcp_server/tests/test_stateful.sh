#!/bin/bash

# Stateful MCP Server Test
# Tests MCP server in stateful mode with sessions

set -e

# Configuration
BASE_URL="${MCP_BASE_URL:-http://localhost:8069/mcp}"
HEALTH_URL="${MCP_BASE_URL:-http://localhost:8069/mcp/health}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Test counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

print_banner() {
    echo -e "${CYAN}"
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║                    MCP SERVER BASIC TESTS                     ║"
    echo "║                   Production-Ready Testing                     ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_header() {
    echo -e "\n${BLUE}=== $1 ===${NC}\n"
}

print_test() {
    echo -e "${YELLOW}🧪 Testing: $1${NC}"
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
}

print_success() {
    echo -e "${GREEN}✅ PASS${NC}"
    PASSED_TESTS=$((PASSED_TESTS + 1))
}

print_failure() {
    echo -e "${RED}❌ FAIL: $1${NC}"
    FAILED_TESTS=$((FAILED_TESTS + 1))
}

print_response() {
    local response="$1"
    local max_length=200
    if [ ${#response} -gt $max_length ]; then
        echo -e "${CYAN}Response: ${response:0:$max_length}...${NC}"
    else
        echo -e "${CYAN}Response: $response${NC}"
    fi
}

# Test function with better error handling
run_test() {
    local test_name="$1"
    local expected_status="$2"
    shift 2
    local curl_command=("$@")

    print_test "$test_name"

    # Run curl and capture both status and response
    response=$(curl -s -w "\n%{http_code}" --max-time 10 "${curl_command[@]}" 2>/dev/null)

    if [ $? -eq 0 ]; then
        # Extract status code and response body
        status_code=$(echo "$response" | tail -n1)
        response_body=$(echo "$response" | sed '$d')

        print_response "$response_body"

        if [ "$status_code" = "$expected_status" ]; then
            print_success
        else
            print_failure "Expected status $expected_status, got $status_code"
        fi
    else
        print_failure "Request failed or timed out"
    fi
}

# Get API key from user
print_banner

if [ -n "$MCP_API_KEY" ]; then
    API_KEY="$MCP_API_KEY"
    echo -e "${GREEN}✅ Using API key from environment variable${NC}"
else
    echo -e "${YELLOW}🔑 Enter your Odoo API key:${NC}"
    echo -e "${CYAN}💡 Get it from: LLM → Configuration → MCP Server${NC}"
    echo -e "${CYAN}💡 Or follow: https://www.odoo.com/documentation/17.0/developer/reference/external_api.html#api-keys${NC}"
    echo -n "API Key: "
    read -r API_KEY

    if [ -z "$API_KEY" ]; then
        echo -e "${RED}❌ ERROR: API key is required${NC}"
        exit 1
    fi
fi

# Test 1: Health Check
print_header "HEALTH CHECK"
run_test "Health Check" "200" \
    -X GET "$HEALTH_URL"

# Test 2: Initialize (Stateful Mode)
print_header "INITIALIZATION"
run_test "Initialize - Get Session ID" "200" \
    -X POST "$BASE_URL" \
    -H "Content-Type: application/json" \
    -H "Accept: application/json" \
    -d '{
        "jsonrpc": "2.0",
        "method": "initialize",
        "id": 1,
        "params": {
            "protocolVersion": "2025-06-18",
            "clientInfo": {"name": "test-client", "version": "1.0.0"},
            "capabilities": {}
        }
    }'

# Test 3: Initialize and extract session ID for subsequent tests
print_header "SESSION TESTING"
echo -e "${YELLOW}🔧 Extracting session ID for authenticated tests...${NC}"

session_response=$(curl -s -D /tmp/mcp_headers.txt --max-time 10 \
    -X POST "$BASE_URL" \
    -H "Content-Type: application/json" \
    -H "Accept: application/json" \
    -d '{
        "jsonrpc": "2.0",
        "method": "initialize",
        "id": 2,
        "params": {
            "protocolVersion": "2025-06-18",
            "clientInfo": {"name": "test-session", "version": "1.0.0"}
        }
    }' 2>/dev/null)

# Extract session ID from response headers
SESSION_ID=$(grep -i "mcp-session-id" /tmp/mcp_headers.txt | cut -d: -f2 | tr -d ' \r\n' 2>/dev/null)

if [ -z "$SESSION_ID" ]; then
    echo -e "${RED}❌ Failed to extract session ID from headers${NC}"
    echo -e "${YELLOW}⚠️  Using mock session ID for remaining tests${NC}"
    SESSION_ID="test-session-$(date +%s)"
fi

echo -e "${CYAN}Using session ID: $SESSION_ID${NC}"
rm -f /tmp/mcp_headers.txt

# Test 4: Notifications/Initialized
run_test "Send notifications/initialized" "202" \
    -X POST "$BASE_URL" \
    -H "Content-Type: application/json" \
    -H "Mcp-Session-Id: $SESSION_ID" \
    -d '{
        "jsonrpc": "2.0",
        "method": "notifications/initialized"
    }'

# Test 5: Tools List (No Auth Required)
print_header "TOOL DISCOVERY"
run_test "List Available Tools" "200" \
    -X POST "$BASE_URL" \
    -H "Content-Type: application/json" \
    -H "Mcp-Session-Id: $SESSION_ID" \
    -d '{
        "jsonrpc": "2.0",
        "method": "tools/list",
        "id": 3,
        "params": {}
    }'

# Test 6: Ping
run_test "Ping Server" "200" \
    -X POST "$BASE_URL" \
    -H "Content-Type: application/json" \
    -d '{
        "jsonrpc": "2.0",
        "method": "ping",
        "id": 4,
        "params": {}
    }'

# Test 7: Tools Call (Requires Authentication)
print_header "AUTHENTICATED TOOL EXECUTION"
run_test "Call Tool (Authenticated)" "200" \
    -X POST "$BASE_URL" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $API_KEY" \
    -H "Mcp-Session-Id: $SESSION_ID" \
    -d '{
        "jsonrpc": "2.0",
        "method": "tools/call",
        "id": 5,
        "params": {
            "name": "test_tool",
            "arguments": {}
        }
    }'

# Test 8: Invalid Method
print_header "ERROR HANDLING"
run_test "Invalid Method" "200" \
    -X POST "$BASE_URL" \
    -H "Content-Type: application/json" \
    -d '{
        "jsonrpc": "2.0",
        "method": "invalid/method",
        "id": 6,
        "params": {}
    }'

# Test Summary
print_header "TEST SUMMARY"
echo -e "${BLUE}Total Tests: $TOTAL_TESTS${NC}"
echo -e "${GREEN}Passed: $PASSED_TESTS${NC}"
echo -e "${RED}Failed: $FAILED_TESTS${NC}"

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "\n${GREEN}🎉 All tests passed! MCP server is working correctly.${NC}"
    exit 0
else
    echo -e "\n${RED}❌ Some tests failed. Please check your server configuration.${NC}"
    exit 1
fi
