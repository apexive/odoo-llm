#!/bin/bash

# Stateless MCP Server Test
# Tests MCP server in stateless mode without sessions

set -e

# Configuration
BASE_URL="${MCP_BASE_URL:-http://localhost:8069/mcp}"
HEALTH_URL="${MCP_BASE_URL:-http://localhost:8069/mcp/health}"

# Colors
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
    echo "║                  MCP SERVER STATELESS TEST                    ║"
    echo "║                    No Session Management                       ║"
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
    local max_length=150
    if [ ${#response} -gt $max_length ]; then
        echo -e "${CYAN}Response: ${response:0:$max_length}...${NC}"
    else
        echo -e "${CYAN}Response: $response${NC}"
    fi
}

run_test() {
    local test_name="$1"
    local expected_status="$2"
    shift 2
    local curl_command=("$@")

    print_test "$test_name"

    response=$(curl -s -w "\n%{http_code}" --max-time 10 "${curl_command[@]}" 2>/dev/null)

    if [ $? -eq 0 ]; then
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
echo -e "${YELLOW}ℹ️  Stateless mode: No session management, direct method calls${NC}"

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

# Test 2: Initialize (Stateless)
print_header "STATELESS INITIALIZATION"
run_test "Initialize (No Session)" "200" \
    -X POST "$BASE_URL" \
    -H "Content-Type: application/json" \
    -d '{
        "jsonrpc": "2.0",
        "method": "initialize",
        "id": 1,
        "params": {
            "protocolVersion": "2025-06-18",
            "clientInfo": {"name": "stateless-test", "version": "1.0.0"},
            "capabilities": {}
        }
    }'

# Test 3: Tools List (No Session)
print_header "TOOL DISCOVERY"
run_test "List Tools (No Session)" "200" \
    -X POST "$BASE_URL" \
    -H "Content-Type: application/json" \
    -d '{
        "jsonrpc": "2.0",
        "method": "tools/list",
        "id": 2,
        "params": {}
    }'

# Test 4: Ping (No Session)
print_header "CONNECTIVITY"
run_test "Ping (No Session)" "200" \
    -X POST "$BASE_URL" \
    -H "Content-Type: application/json" \
    -d '{
        "jsonrpc": "2.0",
        "method": "ping",
        "id": 3,
        "params": {}
    }'

# Test 5: Tools Call (Authenticated, No Session)
print_header "AUTHENTICATED OPERATIONS"
run_test "Call Tool (No Session)" "200" \
    -X POST "$BASE_URL" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $API_KEY" \
    -d '{
        "jsonrpc": "2.0",
        "method": "tools/call",
        "id": 4,
        "params": {
            "name": "test_tool",
            "arguments": {}
        }
    }'

# Test 6: Invalid Method
print_header "ERROR HANDLING"
run_test "Invalid Method" "200" \
    -X POST "$BASE_URL" \
    -H "Content-Type: application/json" \
    -d '{
        "jsonrpc": "2.0",
        "method": "nonexistent/method",
        "id": 5,
        "params": {}
    }'

# Test Summary
print_header "TEST SUMMARY"
echo -e "${BLUE}Total Tests: $TOTAL_TESTS${NC}"
echo -e "${GREEN}Passed: $PASSED_TESTS${NC}"
echo -e "${RED}Failed: $FAILED_TESTS${NC}"

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "\n${GREEN}🎉 All stateless tests passed!${NC}"
    exit 0
else
    echo -e "\n${RED}❌ Some tests failed. Check server configuration.${NC}"
    exit 1
fi
