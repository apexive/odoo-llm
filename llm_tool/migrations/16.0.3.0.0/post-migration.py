import json
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):  # noqa: C901
    """
    Migration script to convert existing tool messages directly to body_json format.

    This migration handles both:
    1. Old format: separate fields (tool_call_id, tool_call_definition, tool_call_result)
    2. Intermediate format: JSON in body field

    All tool data is consolidated into the body_json field.
    """
    _logger.info("Starting migration to convert tool messages to body_json format")

    # First, handle messages with the old separate fields format
    cr.execute("""
        SELECT id, tool_call_id, tool_call_definition, tool_call_result, body, llm_role
        FROM mail_message
        WHERE tool_call_id IS NOT NULL
        ORDER BY id
    """)

    old_format_messages = cr.fetchall()
    _logger.info(
        f"Found {len(old_format_messages)} tool messages with old field format to migrate"
    )

    converted_count = 0
    error_count = 0

    for (
        msg_id,
        tool_call_id,
        tool_call_definition,
        tool_call_result,
        _body,
        _llm_role,
    ) in old_format_messages:
        try:
            # Create new tool data structure
            tool_data = {
                "type": "tool_execution",
                "tool_call_id": tool_call_id,
            }

            # Parse and add tool call definition
            if tool_call_definition:
                try:
                    tool_call = json.loads(tool_call_definition)
                    tool_data["tool_call"] = tool_call
                    # Extract tool name from definition
                    if isinstance(tool_call, dict) and "function" in tool_call:
                        function = tool_call["function"]
                        if isinstance(function, dict) and "name" in function:
                            tool_data["tool_name"] = function["name"]
                except json.JSONDecodeError:
                    _logger.warning(
                        f"Failed to parse tool_call_definition for message {msg_id}"
                    )
                    tool_data["tool_name"] = "unknown_tool"
            else:
                tool_data["tool_name"] = "unknown_tool"

            # Parse and add tool call result
            if tool_call_result:
                try:
                    result = json.loads(tool_call_result)
                    if isinstance(result, dict) and "error" in result:
                        tool_data["status"] = "error"
                        tool_data["error"] = result["error"]
                    else:
                        tool_data["status"] = "completed"
                        tool_data["result"] = result
                except json.JSONDecodeError:
                    # If result is not valid JSON, treat as plain text result
                    tool_data["status"] = "completed"
                    tool_data["result"] = tool_call_result
            else:
                # No result means it's still executing or failed without result
                tool_data["status"] = "executing"

            # Store directly in body_json field and clear body
            cr.execute(
                """
                UPDATE mail_message
                SET body_json = %s, body = NULL
                WHERE id = %s
            """,
                (json.dumps(tool_data), msg_id),
            )

            converted_count += 1

            if converted_count % 100 == 0:
                _logger.info(f"Converted {converted_count} old format tool messages...")

        except Exception as e:
            error_count += 1
            _logger.error(
                f"Error converting old format tool message {msg_id}: {str(e)}"
            )
            continue

    _logger.info(
        f"Old format migration completed: {converted_count} messages converted, {error_count} errors"
    )

    # Second, handle messages that might have JSON in the body field (intermediate format)
    cr.execute("""
        SELECT id, body, llm_role
        FROM mail_message
        WHERE llm_role = 'tool'
        AND body IS NOT NULL
        AND body_json IS NULL
        AND tool_call_id IS NULL
        ORDER BY id
    """)

    intermediate_format_messages = cr.fetchall()
    _logger.info(
        f"Found {len(intermediate_format_messages)} tool messages with intermediate JSON format"
    )

    intermediate_converted_count = 0
    intermediate_error_count = 0

    for msg_id, body, _llm_role in intermediate_format_messages:
        try:
            # Skip messages that are already HTML (wrapped in <p> tags)
            if body.strip().startswith("<p>") or not body.strip().startswith("{"):
                _logger.debug(
                    f"Skipping message {msg_id}: body appears to be HTML, not JSON"
                )
                continue

            # Try to parse the body as JSON
            try:
                tool_data = json.loads(body)
                if not isinstance(tool_data, dict) or "type" not in tool_data:
                    _logger.debug(
                        f"Skipping message {msg_id}: body is not tool data JSON"
                    )
                    continue
            except json.JSONDecodeError:
                _logger.debug(f"Skipping message {msg_id}: body is not valid JSON")
                continue

            # Move JSON data to body_json field and clear body
            cr.execute(
                """
                UPDATE mail_message
                SET body_json = %s, body = NULL
                WHERE id = %s
            """,
                (json.dumps(tool_data), msg_id),
            )

            intermediate_converted_count += 1

            if intermediate_converted_count % 100 == 0:
                _logger.info(
                    f"Converted {intermediate_converted_count} intermediate format tool messages..."
                )

        except Exception as e:
            intermediate_error_count += 1
            _logger.error(
                f"Error converting intermediate format tool message {msg_id}: {str(e)}"
            )
            continue

    _logger.info(
        f"Intermediate format migration completed: {intermediate_converted_count} messages converted, {intermediate_error_count} errors"
    )

    # Handle assistant messages that have tool_calls field (cleanup)
    cr.execute("""
        SELECT id, tool_calls, body
        FROM mail_message
        WHERE tool_calls IS NOT NULL AND llm_role = 'assistant'
        ORDER BY id
    """)

    assistant_messages = cr.fetchall()
    _logger.info(
        f"Found {len(assistant_messages)} assistant messages with tool_calls field"
    )

    # These don't need body conversion, but we should validate the tool_calls JSON
    validated_count = 0
    for msg_id, tool_calls, _body in assistant_messages:
        try:
            # Validate that tool_calls is valid JSON
            json.loads(tool_calls)
            validated_count += 1
        except json.JSONDecodeError:
            _logger.warning(
                f"Assistant message {msg_id} has invalid tool_calls JSON, clearing it"
            )
            cr.execute(
                "UPDATE mail_message SET tool_calls = NULL WHERE id = %s", (msg_id,)
            )

    _logger.info(f"Validated {validated_count} assistant messages with tool_calls")

    # Summary
    total_converted = converted_count + intermediate_converted_count
    total_errors = error_count + intermediate_error_count
    _logger.info(
        f"Migration summary: {total_converted} total messages converted, {total_errors} total errors"
    )
