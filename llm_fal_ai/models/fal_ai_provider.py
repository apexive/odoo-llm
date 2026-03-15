import json
import logging
import os

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    import fal_client
except ImportError:
    _logger.warning(
        "Could not import fal_client. Install the package with pip: pip install fal_client"
    )
    fal_client = None


class LLMProvider(models.Model):
    _inherit = "llm.provider"

    webhook_url = fields.Char(
        string="Webhook URL", help="URL where FAL.AI will send completion notifications"
    )

    @api.model
    def _get_available_services(self):
        services = super()._get_available_services()
        services.append(("fal_ai", "Fal.ai"))
        return services

    def fal_ai_get_client(self):
        """Initializes and returns the fal.ai client."""
        if not fal_client:
            raise UserError(
                _(
                    "The fal_client package is not installed. Install it with pip: pip install fal_client"
                )
            )

        # fal.ai uses environment variables for the API_KEY, but we can also set it programmatically
        os.environ.setdefault("FAL_KEY", self.api_key)
        return fal_client

    def fal_ai_chat(self, messages, model=None, stream=False, **kwargs):
        """FAL AI doesn't support chat directly"""
        raise UserError(_("FAL AI provider does not support chat functionality"))

    def fal_ai_embedding(self, texts, model=None):
        """FAL AI doesn't support embeddings directly"""
        raise UserError(_("FAL AI provider does not support embedding functionality"))

    def fal_ai_generate(self, input_data, model=None, stream=False, **kwargs):
        """Generate content using FAL AI

        Returns:
            tuple: (output_dict, urls_list) where:
                - output_dict: Dictionary containing provider-specific output data
                - urls_list: List of dictionaries with URL metadata
        """
        self.ensure_one()
        client = self.fal_ai_get_client()

        # Get the model name
        model_name = model.name if model else None
        if not model_name:
            raise ValueError("Model name is required")

        input_data = (
            json.loads(input_data) if isinstance(input_data, str) else input_data
        )

        try:
            if stream:
                return self._fal_ai_generate_stream(client, model_name, input_data)
            else:
                return self._fal_ai_generate_sync(client, model_name, input_data)
        except Exception as e:
            _logger.error(f"Error in FAL AI generate: {e}")
            raise UserError(_(f"FAL AI generation failed: {str(e)}")) from e

    def _fal_ai_generate_sync(self, client, model_name, input_data):
        """Generate content synchronously"""
        _logger.info(f"FAL.AI SYNC GENERATION - Model: {model_name}")
        _logger.info(
            f"FAL.AI SYNC GENERATION - Input data: {json.dumps(input_data, indent=2)}"
        )

        result = client.run(model_name, arguments=input_data)

        _logger.info(f"FAL.AI SYNC GENERATION - Raw result type: {type(result)}")
        _logger.info(
            f"FAL.AI SYNC GENERATION - Raw result: {json.dumps(result, indent=2) if isinstance(result, (dict, list)) else str(result)}"
        )

        # Extract URLs with metadata from the result
        urls = self._fal_ai_extract_urls_with_metadata(result)

        _logger.info(f"FAL.AI SYNC GENERATION - Extracted URLs count: {len(urls)}")
        for i, url_data in enumerate(urls):
            _logger.info(
                f"FAL.AI SYNC GENERATION - URL {i+1}: {json.dumps(url_data, indent=2)}"
            )

        # Create output data
        output_data = {
            "raw_response": result,
            "model_name": model_name,
            "inputs": input_data,
            "provider": "fal_ai",
        }

        _logger.info(
            f"FAL.AI SYNC GENERATION - Final output data keys: {list(output_data.keys())}"
        )

        return (output_data, urls)

    def _fal_ai_generate_stream(self, client, model_name, input_data):
        """Stream generation results"""
        try:
            stream = client.stream(model_name, arguments=input_data)
            for event in stream:
                if hasattr(event, "data"):
                    urls = self._fal_ai_extract_urls_with_metadata(event.data)
                    output_data = {
                        "raw_response": event.data,
                        "model_name": model_name,
                        "inputs": input_data,
                        "provider": "fal_ai",
                    }
                    yield {"content": (output_data, urls)}
                else:
                    output_data = {
                        "raw_response": event,
                        "model_name": model_name,
                        "inputs": input_data,
                        "provider": "fal_ai",
                    }
                    yield {"content": (output_data, [])}
        except Exception as e:
            _logger.error(f"Error in FAL AI stream: {e}")
            raise UserError(_(f"FAL AI streaming failed: {str(e)}")) from e

    def fal_ai_models(self, model_id=None):
        """Retrieves the list of available models on fal.ai."""
        # Currently, fal.ai does not provide an endpoint to list models
        # Hardcoded known models with details including schemas
        models = [
            {
                "id": "fal-ai/flux/dev",
                "name": "fal-ai/flux/dev",
                "description": "FLUX.1 [dev] - High-quality image generation model",
                "capabilities": ["image_generation"],
                "details": {
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "prompt": {
                                "type": "string",
                                "description": "Description of the image to generate",
                                "title": "Prompt",
                            },
                            "negative_prompt": {
                                "type": "string",
                                "description": "Elements to avoid in the generated image",
                                "title": "Negative Prompt",
                                "default": "",
                            },
                            "image_size": {
                                "type": "string",
                                "description": "Size of the generated image",
                                "enum": [
                                    "square",
                                    "portrait",
                                    "landscape",
                                    "landscape_16_9",
                                    "landscape_4_3",
                                ],
                                "default": "square",
                                "title": "Image Size",
                            },
                            "num_images": {
                                "type": "integer",
                                "description": "Number of images to generate",
                                "minimum": 1,
                                "maximum": 4,
                                "default": 1,
                                "title": "Image Quantity",
                            },
                            "seed": {
                                "type": "integer",
                                "description": "Seed for reproducibility",
                                "default": 42,
                                "title": "Seed",
                            },
                        },
                        "required": ["prompt"],
                    },
                    "output_schema": {
                        "type": "array",
                        "items": {"type": "string", "format": "uri"},
                        "title": "Generated Images",
                    },
                },
            },
            {
                "id": "fal-ai/lcm",
                "name": "fal-ai/lcm",
                "description": "Latent Consistency Model - Fast image generation",
                "capabilities": ["image_generation"],
                "details": {
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "prompt": {
                                "type": "string",
                                "description": "Description of the image to generate",
                                "title": "Prompt",
                            },
                            "negative_prompt": {
                                "type": "string",
                                "description": "Elements to avoid in the generated image",
                                "title": "Negative Prompt",
                                "default": "",
                            },
                            "image_size": {
                                "type": "string",
                                "description": "Size of the generated image",
                                "enum": ["square", "portrait", "landscape"],
                                "default": "square",
                                "title": "Image Size",
                            },
                            "num_inference_steps": {
                                "type": "integer",
                                "description": "Number of inference steps",
                                "minimum": 1,
                                "maximum": 8,
                                "default": 4,
                                "title": "Inference Steps",
                            },
                        },
                        "required": ["prompt"],
                    },
                    "output_schema": {
                        "type": "array",
                        "items": {"type": "string", "format": "uri"},
                        "title": "Generated Images",
                    },
                },
            },
        ]

        return models

    def fal_ai_format_generation_response(self, raw_response, output_schema):
        """Format the raw generation response according to the output processing config

        Args:
            raw_response: The raw response from the provider (e.g., fal_ai client.run()).
                          Typically a list of URLs or a single URL string for images.
            output_schema (dict): Schema of the output.

        Returns:
            list: A list of strings (e.g., URLs) extracted from the raw_response.
                  Returns an empty list if no suitable strings are found or
                  if the raw_response format is unexpected.
        """
        extracted_strings = []

        if isinstance(raw_response, list):
            for item in raw_response:
                if isinstance(item, str):
                    extracted_strings.append(item)
                else:
                    _logger.warning(
                        f"FAL AI: Item in raw_response list is not a string: {item} (type: {type(item)}). Output schema: {output_schema}"
                    )
        elif isinstance(raw_response, str):
            extracted_strings.append(raw_response)
        elif raw_response is None:
            _logger.info(
                f"FAL AI: Raw response is None for schema {output_schema}. Returning empty list."
            )
        else:
            _logger.warning(
                f"FAL AI: Unexpected raw_response type: {type(raw_response)}. Full response: {raw_response}. Output schema: {output_schema}"
            )

        _logger.info(f"FAL AI: Extracted strings: {extracted_strings}")
        return extracted_strings

    def _fal_ai_extract_urls_with_metadata(self, result):
        """Extract URLs with metadata from fal_ai result"""
        urls = []

        _logger.info(f"FAL.AI URL EXTRACTION - Input result type: {type(result)}")
        _logger.info(
            f"FAL.AI URL EXTRACTION - Input result: {json.dumps(result, indent=2) if isinstance(result, (dict, list)) else str(result)}"
        )

        if result is None:
            _logger.info("FAL.AI URL EXTRACTION - Result is None, returning empty list")
            return urls

        # Handle both training outputs and standard image generation
        if isinstance(result, dict):
            # First, check if this looks like a training output
            training_file_keys = [key for key in result.keys() if key.endswith("_file")]

            _logger.info(
                f"FAL.AI URL EXTRACTION - Training file keys found: {training_file_keys}"
            )

            if training_file_keys:
                # This is a training output, extract file URLs
                for key, value in result.items():
                    if isinstance(value, dict) and "url" in value:
                        url_data = {
                            "url": value["url"],
                            "filename": key,  # Use the key as filename for attachment identification
                            "content_type": value.get(
                                "content_type", "application/octet-stream"
                            ),
                            "original_filename": value.get("file_name", "unknown"),
                            "file_type": key,
                        }

                        # Add file size if available
                        if "file_size" in value:
                            url_data["file_size"] = value["file_size"]

                        urls.append(url_data)
                        _logger.info(
                            f"FAL.AI URL EXTRACTION - Training file extracted: {json.dumps(url_data, indent=2)}"
                        )

                _logger.info(
                    f"FAL.AI URL EXTRACTION - Training output processed, total URLs: {len(urls)}"
                )
                return urls

            # If not training output, check for standard image generation patterns
            elif "images" in result:
                _logger.info(
                    "FAL.AI URL EXTRACTION - Processing standard image generation with 'images' key"
                )
                # Standard image generation with 'images' key
                for i, item in enumerate(result["images"]):
                    url_data = self._fal_ai_extract_single_url_with_metadata(item)
                    if url_data:
                        urls.append(url_data)
                        _logger.info(
                            f"FAL.AI URL EXTRACTION - Image {i+1} extracted: {json.dumps(url_data, indent=2)}"
                        )
            else:
                _logger.info(
                    "FAL.AI URL EXTRACTION - No 'images' key found, checking for other URL fields"
                )
                # Check for other potential URL fields in the dictionary
                url_data = self._fal_ai_extract_single_url_with_metadata(result)
                if url_data:
                    urls.append(url_data)
                    _logger.info(
                        f"FAL.AI URL EXTRACTION - Direct URL extracted: {json.dumps(url_data, indent=2)}"
                    )

        elif isinstance(result, list):
            _logger.info(
                f"FAL.AI URL EXTRACTION - Processing list with {len(result)} items"
            )
            # If result is a list, extract URLs from each item
            for i, item in enumerate(result):
                url_data = self._fal_ai_extract_single_url_with_metadata(item)
                if url_data:
                    urls.append(url_data)
                    _logger.info(
                        f"FAL.AI URL EXTRACTION - List item {i+1} extracted: {json.dumps(url_data, indent=2)}"
                    )

        else:
            _logger.info(
                "FAL.AI URL EXTRACTION - Processing single item (not list or dict)"
            )
            # If result is a single item (not a list or dict), extract URL directly
            url_data = self._fal_ai_extract_single_url_with_metadata(result)
            if url_data:
                urls.append(url_data)
                _logger.info(
                    f"FAL.AI URL EXTRACTION - Single item extracted: {json.dumps(url_data, indent=2)}"
                )

        _logger.info(f"FAL.AI URL EXTRACTION - Final URLs count: {len(urls)}")
        return urls

    def _fal_ai_extract_single_url_with_metadata(self, item):
        """Extract URL with metadata from a single result item"""
        if isinstance(item, dict):
            if "url" in item:
                url_data = {
                    "url": item["url"],
                    "content_type": item.get(
                        "content_type", "application/octet-stream"
                    ),
                    "filename": item["url"].split("/")[-1]
                    if item["url"]
                    else "generated_content",
                }

                # Add dimensions if available
                if "width" in item:
                    url_data["width"] = item["width"]
                if "height" in item:
                    url_data["height"] = item["height"]

                return url_data
            elif "content" in item and isinstance(item["content"], str):
                return {
                    "url": item["content"],
                    "content_type": "application/octet-stream",
                    "filename": item["content"].split("/")[-1]
                    if item["content"]
                    else "generated_content",
                }
        elif isinstance(item, str):
            return {
                "url": item,
                "content_type": "application/octet-stream",
                "filename": item.split("/")[-1] if item else "generated_content",
            }
        return None

    # ============================================================================
    # GENERATION JOB METHODS
    # ============================================================================

    def fal_ai_create_generation_job(self, job_record):
        """Submit a generation job to FAL.AI with webhook support"""
        self.ensure_one()

        _logger.info(f"FAL.AI JOB CREATION - Job ID: {job_record.id}")

        # Generate webhook URL dynamically (don't store on provider to avoid permission issues)
        webhook_url = self.webhook_url
        if not webhook_url:
            base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
            webhook_url = f"{base_url}/llm/generate_job/webhook/{job_record.id}"

        _logger.info(f"FAL.AI JOB CREATION - Webhook URL: {webhook_url}")

        fal_client = self.fal_ai_get_client()

        # Get the model name
        model_name = job_record.model_id.name
        if not model_name:
            raise UserError(_("Model name is required"))

        _logger.info(f"FAL.AI JOB CREATION - Model: {model_name}")

        # Prepare inputs at execution time (not at job creation time)
        # This ensures fresh context, proper template rendering, and matches synchronous flow
        inputs = job_record.get_prepared_inputs()
        if not inputs:
            raise UserError(_("Generation inputs are required"))

        _logger.info(
            f"FAL.AI JOB CREATION - Raw inputs: {json.dumps(inputs, indent=2) if isinstance(inputs, dict) else str(inputs)}"
        )

        try:
            # Convert inputs to dictionary if needed
            if isinstance(inputs, str):
                inputs = json.loads(inputs)

            # Extract prompt from inputs (following standard generation pattern)
            arguments = {
                "prompt": inputs.get("prompt", ""),
            }

            # Add any additional arguments from inputs
            for key, value in inputs.items():
                if key != "prompt" and key not in arguments:
                    arguments[key] = value

            _logger.info(
                f"FAL.AI JOB CREATION - Final arguments sent to FAL.AI: {json.dumps(arguments, indent=2)}"
            )

            # Submit to FAL.AI queue with webhook
            result = fal_client.submit(
                model_name, arguments=arguments, webhook_url=webhook_url
            )

            _logger.info(
                f"FAL.AI JOB CREATION - Submitted job with request_id: {result.request_id}"
            )

            return json.dumps({"request_id": result.request_id, "status": "queued"})

        except Exception as e:
            _logger.error(f"FAL.AI JOB CREATION - Error submitting job: {e}")
            raise UserError(_(f"Failed to submit job to FAL.AI: {str(e)}")) from e

    def fal_ai_check_generation_job_status(self, job_record):
        """Check the status of a generation job with FAL.AI"""
        self.ensure_one()

        if not job_record.external_job_id:
            raise UserError(_("No external job ID found"))

        try:
            # Parse external job ID
            external_data = job_record.external_job_id
            if isinstance(external_data, str):
                external_data = external_data.replace("'", '"')
                external_data = json.loads(external_data)

            request_id = external_data.get("request_id")
            if not request_id:
                raise UserError(_("No request ID found in external job data"))

            fal_client = self.fal_ai_get_client()

            # Check status with FAL.AI
            status = fal_client.status(
                job_record.model_id.name, request_id=request_id, with_logs=True
            )

            class_name = status.__class__.__name__
            _logger.info(f"FAL.AI job status for {request_id}: {class_name}")

            if class_name == "Queued":
                return {
                    "state": "queued",
                    "position": getattr(status, "position", None),
                }
            elif class_name == "InProgress":
                return {"state": "running", "logs": getattr(status, "logs", [])}
            elif class_name == "Completed":
                _logger.info(f"FAL.AI job {request_id} is completed")

                # Check if job is already completed (to avoid re-processing)
                if job_record.state == "completed":
                    _logger.info(
                        f"Job {job_record.id} already marked as completed, skipping processing"
                    )
                    return {"state": "completed"}

                # Get the result and process it
                _logger.info(f"Fetching result for completed job {request_id}")
                result = fal_client.result(
                    job_record.model_id.name,
                    request_id=request_id,
                )

                _logger.info(f"Got result for job {request_id}: {type(result)}")

                # Process as webhook data
                webhook_data = {
                    "request_id": request_id,
                    "status": "OK",
                    "payload": result,
                }
                self.process_webhook_result(webhook_data, job_record)

                return {"state": "completed"}
            else:
                _logger.error(f"Unknown FAL.AI status type: {class_name}")
                return {
                    "state": "failed",
                    "error": f"Unknown status type: {class_name}",
                }

        except Exception as e:
            _logger.error(f"Error checking FAL.AI job status: {e}", exc_info=True)
            return {"state": "failed", "error": str(e)}

    def fal_ai_cancel_generation_job(self, job_record):
        """Cancel a generation job with FAL.AI

        Note: FAL.AI doesn't provide a direct cancel API in the current client
        """
        self.ensure_one()
        _logger.warning(
            f"FAL.AI job cancellation not supported. Job ID: {job_record.external_job_id}"
        )
        return False

    def process_webhook_result(self, webhook_data, job_record):
        """Process webhook result from FAL.AI following standard generation pattern"""
        status = webhook_data.get("status")
        _logger.info(
            f"FAL.AI WEBHOOK PROCESSING - Job ID: {job_record.id}, Status: {status}"
        )
        _logger.info(
            f"FAL.AI WEBHOOK PROCESSING - Raw webhook data: {json.dumps(webhook_data, indent=2)}"
        )

        if status == "OK":
            payload = webhook_data.get("payload", {})

            _logger.info(f"FAL.AI WEBHOOK PROCESSING - Payload type: {type(payload)}")
            _logger.info(
                f"FAL.AI WEBHOOK PROCESSING - Payload content: {json.dumps(payload, indent=2) if isinstance(payload, (dict, list)) else str(payload)}"
            )

            # Extract URLs from FAL.AI response
            urls = self._fal_ai_extract_urls_from_payload(payload)

            _logger.info(
                f"FAL.AI WEBHOOK PROCESSING - Extracted URLs count: {len(urls)}"
            )
            for i, url_data in enumerate(urls):
                _logger.info(
                    f"FAL.AI WEBHOOK PROCESSING - URL {i+1}: {json.dumps(url_data, indent=2)}"
                )

            # Create output data following standard pattern
            output_data = {
                "raw_response": payload,
                "urls": urls,
                "inputs": job_record.generation_inputs,  # Use raw inputs for output data
                "provider": "fal_ai",
            }

            _logger.info(
                f"FAL.AI WEBHOOK PROCESSING - Output data keys: {list(output_data.keys())}"
            )

            # Create assistant message with structured data
            message = job_record.thread_id.message_post(
                body="",  # Will be updated with markdown content
                llm_role="assistant",
                body_json=output_data,
            )

            _logger.info(
                f"FAL.AI WEBHOOK PROCESSING - Created message ID: {message.id}"
            )

            # Process URLs and create attachments
            markdown_content, attachments = message.process_generation_urls(urls)

            _logger.info(
                f"FAL.AI WEBHOOK PROCESSING - Generated markdown length: {len(markdown_content) if markdown_content else 0}"
            )
            _logger.info(
                f"FAL.AI WEBHOOK PROCESSING - Created attachments count: {len(attachments) if attachments else 0}"
            )

            # Update message with final markdown content
            message.write({"body": markdown_content})

            # Update job record
            job_record.write(
                {
                    "state": "completed",
                    "completed_at": fields.Datetime.now(),
                    "output_message_id": message.id,
                }
            )

            _logger.info(
                f"FAL.AI WEBHOOK PROCESSING - Job {job_record.id} completed successfully"
            )

        elif status == "ERROR":
            error_msg = webhook_data.get("error", "Unknown error")

            # Create error message
            message = job_record.thread_id.message_post(
                body=_("Generation job failed: %s") % error_msg,
                llm_role="assistant",
                message_type="notification",
            )

            # Update job record
            job_record.write(
                {
                    "state": "failed",
                    "completed_at": fields.Datetime.now(),
                    "error_message": error_msg,
                    "output_message_id": message.id,
                }
            )
        else:
            _logger.warning(
                f"Unknown webhook status '{status}' for job {job_record.id}"
            )

    def _fal_ai_extract_urls_from_payload(self, payload):
        """Extract URLs from FAL.AI webhook payload"""
        # Use the main extraction method which handles all formats including training outputs
        return self._fal_ai_extract_urls_with_metadata(payload)

    def fal_ai_should_generate_io_schema(self, model_record):
        """FAL.AI models have predefined schemas, so we don't auto-generate them"""
        return False
