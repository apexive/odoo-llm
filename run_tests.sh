#!/bin/bash

# Test runner for odoo-llm modules
#
# Usage:
#   ./run_tests.sh                                    # Run all provider tests
#   ./run_tests.sh llm_replicate                      # Run specific module
#   ./run_tests.sh "llm_replicate,llm_comfyui"        # Run multiple modules
#   ./run_tests.sh llm_replicate my_test_db           # Custom database name
#   ./run_tests.sh llm_replicate my_test_db 8072      # Custom database and port
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ODOO_PATH="$(cd "$SCRIPT_DIR/../../../.." && pwd)"

# Activate venv
source "$ODOO_PATH/.venv310/bin/activate"

# Default values
MODULE="${1:-llm_replicate,llm_comfyui,llm_comfy_icu}"
TEST_DB="${2:-odoo_llm_test}"
PORT="${3:-8071}"

echo "Running tests for: $MODULE"
echo "Test database: $TEST_DB"
echo "Port: $PORT"

# Run the test directly with proper tag format
python3 "$ODOO_PATH/src/odoo/odoo-bin" \
  -d "$TEST_DB" \
  --db_host=localhost \
  --db_user=odoo \
  --db_password=odoo \
  --addons-path="$ODOO_PATH/src/odoo/addons,$ODOO_PATH/extra-addons/.src/apexive/odoo-llm" \
  -i "$MODULE" \
  --test-enable \
  --test-tags="$MODULE" \
  --stop-after-init \
  --http-port="$PORT" \
  --log-level=test
