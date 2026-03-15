import json
import logging

from odoo import _, api, models
from odoo.exceptions import UserError

from .http_client import ComfyICUClient

_logger = logging.getLogger(__name__)


class LLMProvider(models.Model):
    _inherit = "llm.provider"

    @api.model
    def _get_available_services(self):
        services = super()._get_available_services()
        return services + [("comfy_icu", "ComfyICU")]

    def comfy_icu_get_client(self):
        """Get ComfyICU client instance"""
        if not self.api_key:
            raise UserError(_("ComfyICU API key is required"))

        return ComfyICUClient(api_key=self.api_key, api_base=self.api_base)

    def comfy_icu_models(self, model_id=None):
        """List available ComfyICU models

        For ComfyICU, models are workflows that users have created.
        Fetches workflows from the ComfyICU API.

        Args:
            model_id (str, optional): Specific model ID to fetch. Defaults to None.

        Yields:
            dict: Model information with workflow details
        """
        self.ensure_one()
        client = self.client

        # If a specific model ID is requested, fetch just that workflow
        if model_id:
            try:
                workflow = client.get_workflow(model_id)
                yield self._comfy_icu_parse_workflow(workflow)
            except Exception as e:
                _logger.error(f"Error fetching ComfyICU workflow {model_id}: {e}")
                # Return a basic model if we can't fetch the details
                yield {
                    "id": model_id,
                    "name": model_id,
                    "details": {},
                    "capabilities": ["image_generation"],
                }
        else:
            # Fetch all workflows
            try:
                workflows = client.list_workflows()
                for workflow in workflows:
                    yield self._comfy_icu_parse_workflow(workflow)
            except Exception as e:
                _logger.error(f"Error fetching ComfyICU workflows: {e}")

    def _comfy_icu_parse_workflow(self, workflow):
        """Parse workflow data into model format

        Args:
            workflow (dict): Workflow data from ComfyICU API

        Returns:
            dict: Model information
        """
        # Extract relevant details from the workflow
        details = {
            "name": workflow.get("name"),
            "description": workflow.get("description"),
            "created_at": workflow.get("created_at"),
            "updated_at": workflow.get("updated_at"),
            "tags": workflow.get("tags"),
            "is_nsfw": workflow.get("is_nsfw"),
            "visibility": workflow.get("visibility"),
            "accelerator": workflow.get("accelerator"),
            "featuredImages": workflow.get("featuredImages"),
        }

        # Create model information
        return {
            "id": workflow.get("id"),
            "name": workflow.get("id"),
            "details": self.serialize_model_data(details),
            "capabilities": ["image_generation"],
        }

    def comfy_icu_should_generate_io_schema(self, model_record):
        """Check if I/O schema should be generated for this ComfyICU model.

        Schema should be generated if model doesn't already have input_schema in details.
        ComfyICU uses static schemas, so we only generate once.

        Args:
            model_record (llm.model): The model record to check

        Returns:
            bool: True if schema generation should be triggered
        """
        return not model_record.details or not model_record.details.get("input_schema")

    def comfy_icu_generate_io_schema(self, model_record):
        """Generate a configuration from ComfyICU model details

        Args:
            model_record (llm.model): The model record to generate config for
        """
        self.ensure_one()

        # ComfyICU doesn't provide a schema API, so we'll use a generic schema
        # that accepts workflow_id, prompt, files, and accelerator
        input_schema = {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "The ComfyUI API JSON prompt",
                },
                "files": {
                    "type": "string",
                    "description": 'Map of file paths to URLs for input files. Example: {"/models/loras/thickline_fp16.safetensors": "https://civitai.com/api/download/models/16368?type=Model&format=SafeTensor&size=full&fp=fp16"}',
                },
                "accelerator": {
                    "type": "string",
                    "enum": ["T4", "L4", "A10", "A100_40GB", "A100_80GB", "H100"],
                    "description": "GPU accelerator to use",
                },
                "webhook": {
                    "type": "string",
                    "description": "Webhook URL for status updates",
                },
            },
            "required": ["prompt"],
        }

        output_schema = {
            "type": "array",
            "items": {"type": "string", "format": "uri"},
            "description": "List of URLs to generated media files",
        }

        # Store schemas in details field
        model_details = model_record.details or {}
        model_details.update(
            {
                "input_schema": input_schema,
                "output_schema": output_schema,
            }
        )

        model_record.write({"details": model_details})

    def comfy_icu_generate(self, inputs, model_record=None, stream=False):
        """Generate media content using ComfyICU

        Args:
            inputs (dict): Input parameters for the generation
            model_record (llm.model, optional): Model record. Defaults to None.
            stream (bool, optional): Whether to stream the response. Defaults to False.

        Returns:
            tuple: (output_dict, urls_list) where:
                - output_dict: Dictionary containing provider-specific output data
                - urls_list: List of dictionaries with URL metadata
        """
        self.ensure_one()
        client = self.client

        # Get workflow_id from inputs or model name
        workflow_id = inputs.get(
            "workflow_id", model_record.name if model_record else None
        )
        if not workflow_id:
            raise UserError(_("Workflow ID is required"))

        # Parse input parameters
        prompt = self._parse_json_param(inputs.get("prompt", {}), "prompt")
        files = self._parse_json_param(inputs.get("files"), "files")

        accelerator = inputs.get("accelerator")
        webhook = inputs.get("webhook")

        try:
            # Submit workflow run
            run = client.create_run(
                workflow_id=workflow_id,
                prompt=prompt,
                files=files,
                accelerator=accelerator,
                webhook=webhook,
            )

            run_id = run.get("id")
            if not run_id:
                raise UserError(_("No run ID returned from ComfyICU"))

            # Poll for completion
            result = client.poll_run_status(workflow_id, run_id)
            _logger.info(f"ComfyICU: result: {result}")
            # Check for errors
            if result.get("status") == "ERROR":
                error_msg = self._comfy_icu_extract_error_message(result)
                _logger.error(f"ComfyICU workflow failed: {error_msg}")
                raise UserError(_("ComfyICU workflow failed: %s") % error_msg)

            # Extract output URLs with metadata
            urls = self._comfy_icu_extract_output_urls_with_metadata(result)

            # Create output data
            output_data = {
                "raw_response": result,
                "run_id": run_id,
                "workflow_id": workflow_id,
                "inputs": inputs,
                "provider": "comfy_icu",
            }

            # Return results based on streaming mode
            if stream:
                yield {"content": (output_data, urls)}
            else:
                return (output_data, urls)

        except Exception as e:
            _logger.error(f"Error in ComfyICU workflow execution: {e}")
            raise UserError(_("ComfyICU workflow execution failed: %s") % str(e)) from e

    def comfy_icu_format_generation_response(self, raw_response, output_schema):
        """Format the raw generation response

        Args:
            raw_response: The raw response from the provider
            output_schema (dict): Schema of the output

        Returns:
            list: A list of URLs extracted from the raw_response
        """
        extracted_urls = []

        if isinstance(raw_response, list):
            for item in raw_response:
                if isinstance(item, str):
                    extracted_urls.append(item)
                else:
                    _logger.warning(
                        f"ComfyICU: Item in raw_response list is not a string: {item} (type: {type(item)})"
                    )
        elif isinstance(raw_response, str):
            extracted_urls.append(raw_response)
        elif raw_response is None:
            _logger.info("ComfyICU: Raw response is None. Returning empty list.")
        else:
            _logger.warning(
                f"ComfyICU: Unexpected raw_response type: {type(raw_response)}. Full response: {raw_response}"
            )

        _logger.info(f"ComfyICU: Extracted URLs: {extracted_urls}")
        return extracted_urls

    def _parse_json_param(self, param, param_name):
        """Parse a parameter as JSON if it's a string

        Args:
            param: The parameter to parse
            param_name: The name of the parameter (for error messages)

        Returns:
            The parsed parameter (dict or original value if not a string)

        Raises:
            UserError: If the parameter is a string but not valid JSON
        """
        if isinstance(param, str) and param.strip():
            try:
                return json.loads(param)
            except json.JSONDecodeError as e:
                raise UserError(
                    _("Invalid JSON in %s: %s") % (param_name, str(e))
                ) from e
        return param

    def _comfy_icu_extract_error_message(self, result):
        """Extract error message from ComfyICU API response

        Args:
            result (dict): The API response containing error information

        Returns:
            str: The extracted error message
        """
        error_msg = "Unknown error"

        # Try to extract error from different possible locations in the response
        if "error" in result and result["error"]:
            error_msg = result["error"]
        elif "output" in result and isinstance(result["output"], dict):
            output = result["output"]
            if "error" in output and isinstance(output["error"], dict):
                error_data = output["error"]
                if "exception_message" in error_data:
                    error_msg = error_data["exception_message"]
                elif "details" in error_data and isinstance(
                    error_data["details"], dict
                ):
                    details = error_data["details"]
                    if "error" in details and isinstance(details["error"], dict):
                        error_details = details["error"]
                        if "message" in error_details:
                            error_msg = error_details["message"]

        return error_msg

    def _comfy_icu_extract_output_urls_with_metadata(self, status_data):
        """Extract output URLs with metadata from run status data

        The ComfyICU API returns output URLs in different formats depending on the endpoint:
        1. In the 'outputs' field as a dict of path -> url (older format)
        2. In the 'output' field as a list of objects with 'url' field (newer format)

        This method handles both formats.
        """
        urls = []

        # Try the newer format first (output as a list of objects)
        output_list = status_data.get("output", [])
        if output_list and isinstance(output_list, list):
            for item in output_list:
                if isinstance(item, dict) and "url" in item:
                    url_data = {
                        "url": item["url"],
                        "content_type": "image/png",  # Default for ComfyICU
                        "filename": item["url"].split("/")[-1]
                        if item["url"]
                        else "generated_content",
                    }
                    urls.append(url_data)

        # If no URLs found, try the older format (outputs as a dict)
        if not urls:
            outputs = status_data.get("outputs", {})
            if outputs and isinstance(outputs, dict):
                for path, url in outputs.items():
                    if path.startswith("/output/"):
                        url_data = {
                            "url": url,
                            "content_type": "image/png",  # Default for ComfyICU
                            "filename": url.split("/")[-1]
                            if url
                            else "generated_content",
                            "path": path,
                        }
                        urls.append(url_data)

        _logger.info(f"ComfyICU: Extracted {len(urls)} output URLs")
        if not urls:
            raise UserError(_("No outputs found, try with different seed"))
        return urls
