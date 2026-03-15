import json
import logging
import time
import uuid

import requests
from requests.exceptions import RequestException

_logger = logging.getLogger(__name__)


class ComfyUIClient:
    """HTTP client for ComfyUI API"""

    def __init__(self, api_base, api_key=None):
        self.api_base = api_base.rstrip("/")
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update(
            {
                "accept": "application/json",
                "content-type": "application/json",
            }
        )

        # Add API key if provided
        if api_key:
            self.session.headers.update({"authorization": f"Bearer {api_key}"})

        # Generate a client ID for WebSocket communication
        self.client_id = str(uuid.uuid4())

    def _make_request(self, method, endpoint, data=None, **kwargs):
        """Make HTTP request to ComfyUI API"""
        # Add /api prefix if not already present
        if not endpoint.startswith("/api/"):
            endpoint = (
                f"/api{endpoint}" if endpoint.startswith("/") else f"/api/{endpoint}"
            )

        url = f"{self.api_base}{endpoint}"
        try:
            _logger.info(f"ComfyUI API request: {method} {url}")
            # if data:
            # _logger.info(f"Request data: {json.dumps(data, indent=2)}")

            response = self.session.request(
                method=method, url=url, json=data if data else None, **kwargs
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            error_msg = f"ComfyUI API request failed: {e}"

            # Try to extract status code and response content if available
            if hasattr(e, "response"):
                status_code = getattr(e.response, "status_code", "unknown")
                error_msg += f" (Status: {status_code})"

                # Try to get response content
                try:
                    if hasattr(e.response, "content") and e.response.content:
                        try:
                            # Try to parse as JSON
                            content = e.response.json()
                            _logger.error(
                                f"Response content: {json.dumps(content, indent=2)}"
                            )
                        except Exception:
                            # If not JSON, log as text
                            content = e.response.content.decode(
                                "utf-8", errors="replace"
                            )
                            _logger.error(f"Response content: {content}")
                except Exception as content_error:
                    _logger.error(
                        f"Could not extract response content: {content_error}"
                    )

            _logger.error(error_msg)
            raise e

    def submit_prompt(self, prompt, client_id=None, number=-1, extra_data=None):
        """Submit a workflow (prompt) for execution"""
        data = {
            "prompt": prompt,
            "number": number,
            "client_id": client_id or self.client_id,
        }

        if extra_data:
            data["extra_data"] = extra_data

        return self._make_request("POST", "/prompt", data=data)

    def get_history(self, max_items=None):
        """Get workflow execution history"""
        params = {}
        if max_items:
            params["max_items"] = max_items

        return self._make_request("GET", "/history", params=params)

    def get_prompt_history(self, prompt_id):
        """Get history for a specific prompt"""
        return self._make_request("GET", f"/history/{prompt_id}")

    def get_queue(self):
        """Get queue information"""
        return self._make_request("GET", "/queue")

    def interrupt(self):
        """Interrupt current execution"""
        return self._make_request("POST", "/interrupt")

    def clear_queue(self):
        """Clear the queue"""
        return self._make_request("POST", "/queue", data={"clear": True})

    def delete_queue_items(self, prompt_ids):
        """Delete specific items from the queue"""
        return self._make_request("POST", "/queue", data={"delete": prompt_ids})

    def clear_history(self):
        """Clear history"""
        return self._make_request("POST", "/history", data={"clear": True})

    def delete_history_items(self, prompt_ids):
        """Delete specific items from history"""
        return self._make_request("POST", "/history", data={"delete": prompt_ids})

    def upload_image(
        self, image_data, filename=None, subfolder=None, type="input", overwrite=False
    ):
        """Upload an image to ComfyUI"""
        url = f"{self.api_base}/api/upload/image"
        files = {"image": (filename or "image.png", image_data)}
        data = {"overwrite": "true" if overwrite else "false"}

        if subfolder:
            data["subfolder"] = subfolder
        if type:
            data["type"] = type

        try:
            response = self.session.post(url, files=files, data=data)
            response.raise_for_status()
            return response.json()
        except RequestException as e:
            _logger.error(f"ComfyUI image upload error: {str(e)}")
            raise Exception(f"ComfyUI image upload error: {str(e)}") from e

    # TODO: Maybe it should be configurable
    def poll_prompt_status(self, prompt_id, max_attempts=120, delay=10):
        """Poll for prompt status until completion or error

        This method checks both the queue and history to determine if a prompt
        has completed processing. It follows this logic:

        1. Check if the prompt is still in the queue (running or pending)
        2. If not in queue, check history for the prompt's results
        3. If found in history with outputs, return the results
        4. If any errors are detected, raise an exception
        5. Otherwise, wait and try again

        Args:
            prompt_id (str): The ID of the prompt to check
            max_attempts (int): Maximum number of polling attempts
            delay (int): Seconds to wait between polling attempts

        Returns:
            dict: The completed prompt data with outputs

        Raises:
            TimeoutError: If the prompt doesn't complete within max_attempts
            Exception: If an error is detected in the prompt execution
        """
        for attempt in range(max_attempts):
            # First check if the prompt is still in the queue
            queue = self.get_queue()

            # Check if prompt is in running or pending queue
            is_running = any(
                item[1] == prompt_id for item in queue.get("queue_running", [])
            )
            is_pending = any(
                item[1] == prompt_id for item in queue.get("queue_pending", [])
            )

            if not is_running and not is_pending:
                # If not in queue, check history for results
                history = self.get_prompt_history(prompt_id)
                if prompt_id in history:
                    prompt_data = history[prompt_id]
                    status = (
                        None if "status" not in prompt_data else prompt_data["status"]
                    )
                    # Check for errors in the execution
                    if "error" in prompt_data and prompt_data["error"]:
                        error_msg = prompt_data["error"]
                        _logger.error(f"ComfyUI execution error: {error_msg}")
                        raise Exception(f"ComfyUI execution error: {error_msg}")
                    # Check for errors in the execution
                    execution_error = (
                        status
                        and "status_str" in status
                        and status["status_str"] == "error"
                    )
                    if execution_error:
                        # Extract the exception_message from the execution_error entry in messages
                        error_msg = "Unknown error"
                        if "messages" in status and isinstance(
                            status["messages"], list
                        ):
                            for message in status["messages"]:
                                if (
                                    isinstance(message, list)
                                    and len(message) >= 2
                                    and message[0] == "execution_error"
                                ):
                                    error_data = message[1]
                                    if (
                                        isinstance(error_data, dict)
                                        and "exception_message" in error_data
                                    ):
                                        error_msg = error_data["exception_message"]
                                        break

                        _logger.error(f"ComfyUI execution error: {error_msg}")
                        raise Exception(f"ComfyUI execution error: {error_msg}")
                    # Check if there are outputs
                    elif "outputs" in prompt_data and prompt_data["outputs"]:
                        # Verify outputs have the expected format
                        outputs = prompt_data["outputs"]
                        if isinstance(outputs, dict) and any(
                            "images" in node_output for node_output in outputs.values()
                        ):
                            _logger.info(
                                f"Prompt {prompt_id} completed with valid image outputs"
                            )
                            return prompt_data
                        else:
                            _logger.info(
                                f"Prompt {prompt_id} completed but no image outputs found yet, waiting..."
                            )
                    else:
                        # It's possible that the prompt is marked as completed but outputs are still being processed
                        # This can happen due to file system operations or caching
                        _logger.info(
                            f"Prompt {prompt_id} found in history but no outputs yet, waiting..."
                        )

            _logger.info(
                f"Attempt {attempt + 1}/{max_attempts}: Prompt {prompt_id} still processing"
            )
            time.sleep(delay)

        raise TimeoutError(
            f"Timeout waiting for ComfyUI prompt {prompt_id} to complete after {max_attempts} attempts"
        )
