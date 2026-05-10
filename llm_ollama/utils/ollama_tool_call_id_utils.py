"""
Utility functions for handling tool IDs and names in the Ollama integration.
"""


class OllamaToolCallIdUtils:
    """
    Utility class for working with tool IDs and names.

    This class provides static methods for creating and parsing tool IDs
    in a consistent format across the Ollama integration.
    """

    @staticmethod
    def extract_tool_name_from_id(tool_id):
        """
        Extract tool name from a tool call ID.

        Args:
            tool_id (str): Tool call ID in the format "call_<uuid>_<tool_name>"

        Returns:
            str or None: Extracted tool name or None if not found
        """
        if not tool_id or "_" not in tool_id:
            return None

        parts = tool_id.split("_", 2)
        if len(parts) < 3:
            return None

        return parts[2]  # Get the tool name part

    @staticmethod
    def create_tool_id(tool_name, uuid_str):
        """
        Create a tool call ID from a tool name and UUID.

        Args:
            tool_name (str): Name of the tool
            uuid_str (str): UUID string for the tool call

        Returns:
            str: Tool call ID in the format "call_<uuid>_<tool_name>"
        """
        return f"call_{uuid_str}_{tool_name}"
