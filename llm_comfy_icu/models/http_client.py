import json
import logging
import time

import requests
from requests.exceptions import RequestException

_logger = logging.getLogger(__name__)


class ComfyICUClient:
    """HTTP client for ComfyICU API"""

    def __init__(self, api_key, api_base=None):
        self.api_key = api_key
        self.api_base = api_base or "https://comfy.icu/api/v1"
        self.session = requests.Session()
        self.session.headers.update(
            {
                "accept": "application/json",
                "content-type": "application/json",
                "authorization": f"Bearer {api_key}",
            }
        )

    def _make_request(self, method, endpoint, data=None, **kwargs):
        """Make HTTP request to ComfyICU API"""
        url = f"{self.api_base}{endpoint}"
        try:
            response = self.session.request(
                method=method, url=url, json=data if data else None, **kwargs
            )
            response.raise_for_status()
            return response.json()
        except RequestException as e:
            error_msg = str(e)
            try:
                if e.response and e.response.content:
                    error_data = e.response.json()
                    if "error" in error_data:
                        error_msg = error_data["error"]
            except (AttributeError, ValueError, json.JSONDecodeError):
                pass
            _logger.error(f"ComfyICU API error: {error_msg}")
            raise Exception(f"ComfyICU API error: {error_msg}") from e

    def list_workflows(self):
        """List all workflows"""
        return self._make_request("GET", "/workflows")

    def get_workflow(self, workflow_id):
        """Get a specific workflow"""
        return self._make_request("GET", f"/workflows/{workflow_id}")

    def create_run(
        self, workflow_id, prompt, files=None, accelerator=None, webhook=None
    ):
        """Create a new workflow run"""
        data = {"workflow_id": workflow_id, "prompt": prompt}

        # Add optional parameters
        if files:
            data["files"] = files
        if accelerator:
            data["accelerator"] = accelerator
        if webhook:
            data["webhook"] = webhook

        return self._make_request("POST", f"/workflows/{workflow_id}/runs", data=data)

    def get_run_status(self, workflow_id, run_id):
        """Get the status of a workflow run"""
        return self._make_request("GET", f"/workflows/{workflow_id}/runs/{run_id}")

    def poll_run_status(self, workflow_id, run_id, max_attempts=30, delay=5):
        """Poll for run status until completion or error"""
        for attempt in range(max_attempts):
            status_data = self.get_run_status(workflow_id, run_id)
            status = status_data.get("status", "UNKNOWN")

            _logger.info(f"Attempt {attempt + 1}: Run status is {status}")

            if status in ["COMPLETED", "ERROR"]:
                return status_data

            time.sleep(delay)

        raise TimeoutError(
            f"Timeout waiting for ComfyICU workflow {workflow_id} run {run_id} to complete"
        )
