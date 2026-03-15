import json
import logging
import random
from urllib.parse import urlparse

from odoo import _, api, models
from odoo.exceptions import UserError

from .http_client import ComfyUIClient

_logger = logging.getLogger(__name__)


class LLMProvider(models.Model):
    _inherit = "llm.provider"

    @api.model
    def _get_available_services(self):
        services = super()._get_available_services()
        return services + [("comfyui", "ComfyUI")]

    def comfyui_get_client(self):
        """Get ComfyUI client instance"""
        if not self.api_base:
            raise UserError(
                _("Please configure the ComfyUI server URL in the provider settings.")
            )

        return ComfyUIClient(api_base=self.api_base, api_key=self.api_key)

    def comfyui_models(self, model_id=None):
        """List available ComfyUI models

        ComfyUI doesn't have a concept of models - it's a workflow execution engine
        that takes JSON input and returns outputs. Model fetching is not supported.

        Args:
            model_id (str, optional): Specific model ID to fetch. Defaults to None.

        Raises:
            UserError: Always raises an error as model fetching is not supported
        """
        self.ensure_one()

        raise UserError(
            _(
                "ComfyUI doesn't support model listing or fetching. "
                "It is a workflow execution engine that processes JSON inputs. "
                "Please create a model manually and configure it with your workflow JSON."
            )
        )

    def comfyui_should_generate_io_schema(self, model_record):
        """Check if I/O schema should be generated for this ComfyUI model.

        Schema should be generated if model doesn't already have input_schema in details.
        ComfyUI uses static schemas, so we only generate once.

        Args:
            model_record (llm.model): The model record to check

        Returns:
            bool: True if schema generation should be triggered
        """
        return not model_record.details or not model_record.details.get("input_schema")

    def comfyui_generate_io_schema(self, model_record):
        """Generate a configuration from ComfyUI model details

        Args:
            model_record (llm.model): The model record to generate config for
        """
        self.ensure_one()
        _logger.info("ComfyUI: Generating IO schema for model: %s", model_record)
        # ComfyUI uses a generic schema that accepts workflow JSON
        input_schema = {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "The ComfyUI workflow JSON. Can be obtained using 'Save (API Format)' in the ComfyUI interface.",
                },
                "client_id": {
                    "type": "string",
                    "description": "Optional client ID for tracking the execution",
                },
                "number": {
                    "type": "integer",
                    "description": "Optional execution order, negative for front of queue",
                    "default": -1,
                },
                "extra_data": {
                    "type": "string",
                    "description": "Optional JSON string with extra data for plugins or custom use",
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

    def comfyui_generate(self, inputs, model_record=None, stream=False):
        """Generate media content using ComfyUI

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

        # Parse input parameters
        prompt = self._parse_json_param(inputs.get("prompt", {}), "prompt")
        client_id = inputs.get("client_id")
        number = inputs.get("number", -1)
        extra_data = self._parse_json_param(inputs.get("extra_data"), {})
        randomise_seeds = inputs.get("randomise_seeds", False)

        try:
            if randomise_seeds:
                self.randomise_seeds(prompt)
            # Submit workflow for execution
            response = client.submit_prompt(
                prompt=prompt, client_id=client_id, number=number, extra_data=extra_data
            )

            prompt_id = response.get("prompt_id")
            if not prompt_id:
                raise UserError(
                    _(
                        "The ComfyUI server did not acknowledge the workflow submission. "
                        "Please check that the server is running and try again."
                    )
                )

            # Check for node errors
            node_errors = response.get("node_errors", {})
            if node_errors:
                error_msg = json.dumps(node_errors, indent=2)
                _logger.error("ComfyUI workflow validation failed: %s", error_msg)
                raise UserError(
                    _(
                        "The workflow contains errors and could not be executed. "
                        "Please verify your workflow configuration in ComfyUI.\n\n"
                        "Validation errors: %s"
                    )
                    % error_msg
                )

            # Poll for completion
            result = client.poll_prompt_status(prompt_id)

            # Extract output URLs with metadata
            urls = self._comfyui_extract_output_urls_with_metadata(result)

            # Create output data
            output_data = {
                "raw_response": result,
                "prompt_id": prompt_id,
                "inputs": inputs,
                "provider": "comfyui",
                "workflow_json": prompt,
            }

            # Return results based on streaming mode
            if stream:
                yield {"content": (output_data, urls)}
            else:
                return (output_data, urls)

        except UserError:
            raise
        except Exception as e:
            _logger.error("Error in ComfyUI workflow execution: %s", e)
            raise UserError(
                _(
                    "The image generation failed. This could be due to an invalid workflow "
                    "or server issues. Please check your workflow and try again.\n\n"
                    "Error: %s"
                )
                % str(e)
            ) from e

    def comfyui_format_generation_response(self, raw_response, output_schema):
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
                        f"ComfyUI: Item in raw_response list is not a string: {item} (type: {type(item)})"
                    )
        elif isinstance(raw_response, str):
            extracted_urls.append(raw_response)
        elif raw_response is None:
            _logger.info("ComfyUI: Raw response is None. Returning empty list.")
        else:
            _logger.warning(
                f"ComfyUI: Unexpected raw_response type: {type(raw_response)}. Full response: {raw_response}"
            )

        _logger.info(f"ComfyUI: Extracted URLs: {extracted_urls}")
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
                    _(
                        "The workflow configuration contains invalid JSON in the '%s' field. "
                        "Please check the format.\n\n"
                        "Details: %s"
                    )
                    % (param_name, str(e))
                ) from e
        return param

    def _comfyui_extract_output_urls_with_metadata(self, result):
        """Extract output URLs with metadata from prompt result data

        Args:
            result (dict): The prompt result data

        Returns:
            list: List of URL dictionaries with metadata
        """
        urls = []

        # Extract prompt_id and outputs
        if not result or not isinstance(result, dict):
            raise UserError(
                _(
                    "Received an unexpected response from the ComfyUI server. "
                    "The server may need to be restarted or there may be a version mismatch."
                )
            )

        # Get the outputs from the result
        outputs = result.get("outputs", {})
        if not outputs:
            raise UserError(
                _(
                    "The workflow completed but did not produce any output. "
                    "Please ensure your workflow has at least one output node configured."
                )
            )
        _logger.info(f"ComfyUI: outputs: {outputs}")

        # Process each node's outputs
        for node_id, node_output in outputs.items():
            # Check for images in the node output
            if "images" in node_output:
                for image_info in node_output["images"]:
                    filename = image_info.get("filename")
                    subfolder = image_info.get("subfolder", "")
                    type_folder = image_info.get("type", "output")

                    if filename:
                        # Construct the URL to the image
                        parsed_url = urlparse(self.api_base)
                        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

                        # Build the path
                        path_parts = ["/view"]
                        query_parts = [f"filename={filename}"]

                        if subfolder:
                            query_parts.append(f"subfolder={subfolder}")
                        if type_folder:
                            query_parts.append(f"type={type_folder}")

                        # Construct the final URL
                        image_url = f"{base_url}{path_parts[0]}?{'&'.join(query_parts)}"

                        # Create URL metadata
                        url_data = {
                            "url": image_url,
                            "filename": filename,
                            "subfolder": subfolder,
                            "type": type_folder,
                            "node_id": node_id,
                        }

                        # Try to determine content type from filename
                        if filename.lower().endswith(".png"):
                            url_data["content_type"] = "image/png"
                        elif filename.lower().endswith(
                            ".jpg"
                        ) or filename.lower().endswith(".jpeg"):
                            url_data["content_type"] = "image/jpeg"
                        elif filename.lower().endswith(".gif"):
                            url_data["content_type"] = "image/gif"
                        elif filename.lower().endswith(".webp"):
                            url_data["content_type"] = "image/webp"
                        else:
                            url_data["content_type"] = (
                                "image/png"  # Default for ComfyUI
                            )

                        urls.append(url_data)

        _logger.info("ComfyUI: Extracted %d output URLs", len(urls))
        if not urls:
            raise UserError(
                _(
                    "No images were generated. Please check that your workflow includes "
                    "a 'Save Image' or 'Preview Image' node."
                )
            )

        return urls

    @api.model
    def randomise_input_seed(self, input_key, inputs):
        if input_key in inputs and isinstance(inputs[input_key], (int, float)):
            # Use 2^31 (2147483648) as the maximum value to avoid exceeding ComfyUI's limit
            new_seed = random.randint(0, 2**31 - 1)
            _logger.info(f"Randomising {input_key} to {new_seed}")
            inputs[input_key] = new_seed

    @api.model
    def randomise_seeds(self, workflow_json):
        for _node_id, node in workflow_json.items():
            inputs = node.get("inputs", {})
            seed_keys = ["seed", "noise_seed", "rand_seed"]
            for seed_key in seed_keys:
                self.randomise_input_seed(seed_key, inputs)
