import base64
import hashlib
import json
import logging
import os
import time

import fal_client
import requests
from odoo import models, fields, api, _
from odoo.addons.llm_mail_message_subtypes.const import (
    LLM_ASSISTANT_SUBTYPE_XMLID,
)

try:
    from nacl.signing import VerifyKey
    from nacl.exceptions import BadSignatureError
    from nacl.encoding import HexEncoder

    NACL_AVAILABLE = True
except ImportError:
    NACL_AVAILABLE = False

JWKS_CACHE_DURATION = 24 * 60 * 60  # 24 hours in seconds
_jwks_cache = None
_jwks_cache_time = 0

from odoo.exceptions import UserError

# FAL webhook verification constants
JWKS_URL = "https://rest.alpha.fal.ai/.well-known/jwks.json"

_logger = logging.getLogger(__name__)


class LLMProvider(models.Model):
    _inherit = "llm.provider"

    @api.model
    def _get_available_services(self):
        services = super()._get_available_services()
        services.append(("fal_ai", "Fal.ai"))
        return services

    def fal_ai_get_client(self):
        """Initializes and returns the fal.ai client."""
        if not fal_client:
            raise UserError(_("The fal_client package is not installed. Install it with pip: pip install fal_client"))

        # fal.ai uses environment variables for the API_KEY, but we can also set it programmatically
        os.environ.setdefault('FAL_KEY', self.api_key)
        return fal_client

    def fal_ai_chat(self, messages, model=None, stream=False):
        """FAL AI doesn't support chat directly, redirect to appropriate method"""
        raise UserError(_("FAL AI provider does not support chat functionality"))

    def fal_ai_embedding(self, texts, model=None):
        """FAL AI doesn't support embeddings directly"""
        raise UserError(_("FAL AI provider does not support embedding functionality"))

    def fal_ai_models(self, model_id=None):
        """Retrieves the list of available models on fal.ai."""
        # Currently, fal.ai does not provide an endpoint to list models
        # Hardcoded known models
        # TODO : This should be replaced with a dynamic call to the fal.ai models, but I haven't found it in the documentation.
        models = [
            {"id": "fal-ai/flux/dev", "name": "fal-ai/flux/dev", "description": "Image generation model",
             "capabilities": "multimodal"},
            {"id": "fal-ai/lcm", "name": "fal-ai/lcm", "description": "Latent Consistency Model",
             "capabilities": "multimodal"}
            # Add more models as available on fal.ai
        ]

        return models

    def fal_ai_generate_io_schema(self, model_record):
        """Generates input and output schemas for fal.ai image generation models."""
        # TODO: This should be replaced with a dynamic call to the fal.ai schema, but I haven't found it in the documentation.
        model_record.input_schema = {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Description of the image to generate",
                    "title": "Prompt"
                },
                "negative_prompt": {
                    "type": "string",
                    "description": "Elements to avoid in the generated image",
                    "title": "Negative Prompt",
                    "default": ""
                },
                "image_size": {
                    "type": "string",
                    "description": "Size of the generated image",
                    "enum": ["square", "portrait", "landscape", "landscape_16_9", "landscape_4_3"],
                    "default": "square",
                    "title": "Image Size"
                },
                "num_images": {
                    "type": "integer",
                    "description": "Number of images to generate",
                    "minimum": 1,
                    "maximum": 4,
                    "default": 1,
                    "title": "Image Quantity"
                },
                "seed": {
                    "type": "integer",
                    "description": "Seed for reproducibility",
                    "default": 42,
                    "title": "Seed"
                }
            },
            "required": ["prompt"]
        }

        model_record.output_schema = {
            "type": "array",
            "items": {
                "type": "string",
                "format": "uri"
            },
            "title": "Output"
        }

    def fal_ai_generate_media(self, inputs, model_record=None, stream=False):
        """Generate media using FAL AI"""
        self.ensure_one()
        client = self.fal_ai_get_client()

        # Get the model name
        model_name = model_record.name if model_record else None
        if not model_name:
            raise ValueError("Model name is required")

        if stream:
            ##TODO Here it should be called _fal_ai_stream_media but the call to stream images in the generate module is not yet implemented in this system.
            return self._fal_ai_generate_media_sync(client, model_name, inputs)
        else:
            # Simple synchronous call using run
            return self._fal_ai_generate_media_sync(client, model_name, inputs)

    def _fal_ai_generate_media_sync(self, client, model_name, inputs):
        """Generate media synchronously"""
        try:
            result = client.run(model_name, arguments=inputs)
            yield {"content": self._fal_ai_extract_urls_from_result(result)}
        except Exception as e:
            _logger.error(f"Error in FAL AI generate_media: {e}")
            raise UserError(_(f"FAL AI generation failed: {str(e)}"))

    def _fal_ai_stream_media(self, client, model_name, inputs):
        """Stream media generation results"""
        try:
            stream = client.stream(model_name, arguments=inputs)
            for event in stream:
                yield {"content": event}
        except Exception as e:
            _logger.error(f"Error in FAL AI stream_media: {e}")
            raise UserError(_(f"FAL AI streaming failed: {str(e)}"))

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

        # output_schema example: {"type": "array", "items": {"type": "string", "format": "uri"}}
        # This implies the raw_response should ideally be a list of strings, or a single string.

        if isinstance(raw_response, list):
            for item in raw_response:
                if isinstance(item, str):
                    extracted_strings.append(item)
                else:
                    # Log if an item in the list is not a string, but continue processing
                    _logger.warning(
                        f"Replicate: Item in raw_response list is not a string: {item} (type: {type(item)}). Output schema: {output_schema}"
                    )
        elif isinstance(raw_response, str):
            # If the raw_response is a single string, assume it's the URL/data itself.
            extracted_strings.append(raw_response)
        elif raw_response is None:
            _logger.info(
                f"Replicate: Raw response is None for schema {output_schema}. Returning empty list."
            )
        else:
            _logger.warning(
                f"Replicate: Unexpected raw_response type: {type(raw_response)}. Full response: {raw_response}. Output schema: {output_schema}"
            )
            # For now, we return an empty list. More sophisticated parsing based on
            # output_schema could be added here if needed for complex objects.

        _logger.info(f"Replicate: Extracted strings: {extracted_strings}")
        return extracted_strings

    def fal_ai_supports_async_generation(self):
        """FAL AI supports async generation with webhooks"""
        return True

    def submit_generation_job(self, job_record):
        """Submit a generation job to FAL AI with webhook support"""
        self.ensure_one()

        fal_client = self.fal_ai_get_client()

        # Get the model name
        model_name = job_record.model_id.name
        if not model_name:
            raise UserError(_("Model name is required"))

        # Prepare inputs
        inputs = job_record.generation_inputs
        if not inputs:
            raise UserError(_("Generation inputs are required"))

        try:
            # Submit to FAL AI queue with webhook
            # FAL AI uses queue.submit for async operations
            """
            arguments={
                "prompt": "Extreme close-up of a single tiger eye, direct frontal view. Detailed iris and pupil. Sharp focus on eye texture and color. Natural lighting to capture authentic eye shine and depth. The word \"FLUX\" is painted over it in big, white brush strokes with visible texture."
            },
            """
            # convertir inputs to a dictionary if it's a string
            if isinstance(inputs, str):
                inputs = json.loads(inputs)
            arguments = {
                "prompt": inputs.get('prompt', ''),
            }

            result = fal_client.submit(
                model_name,
                arguments=arguments,
                webhook_url=job_record.webhook_url
            )
            _logger.info(f"Submitted FAL AI job: {result}")

            return {
                'request_id': result.request_id,
                'gateway_request_id': result.request_id,
                'status': 'queued'
            }

        except Exception as e:
            _logger.error(f"Error submitting FAL AI generation job: {e}")
            raise UserError(_(f"Failed to submit job to FAL AI: {str(e)}"))

    def fal_ai_check_generation_job_status(self, job_record):
        """Check the status of a generation job with FAL AI"""
        self.ensure_one()
        fal_client = self.fal_ai_get_client()

        if not job_record.external_job_id:
            raise UserError(_("No external job ID found"))

        try:
            # Check status with FAL AI
            status = fal_client.status(
                job_record.model_id.name,
                request_id=job_record.external_job_id,
                with_logs=True
            )

            _logger.info(f"FAL AI job status: {status}")
            class_name = status.__class__.__name__

            # Manejar los diferentes tipos de estado
            if class_name == "Queued":
                # Trabajo en cola
                webhook_data = {
                    'request_id': job_record.external_job_id,
                    'gateway_request_id': job_record.gateway_request_id,
                    'status': 'QUEUED',
                    'position': status.position,
                    'payload': None
                }
                job_record.write({'state': 'queued'})
                return status

            elif class_name == "InProgress":
                # Trabajo en procesamiento
                webhook_data = {
                    'request_id': job_record.external_job_id,
                    'gateway_request_id': job_record.gateway_request_id,
                    'status': 'PROCESSING',
                    'logs': status.logs if hasattr(status, 'logs') and status.logs else [],
                    'payload': None
                }
                job_record.write({'state': 'processing'})
                return status

            elif class_name == "Completed":
                # Trabajo completado, obtener resultado
                result = fal_client.result(
                    job_record.model_id.name,
                    request_id=job_record.external_job_id,
                )

                webhook_data = {
                    'request_id': job_record.external_job_id,
                    'gateway_request_id': job_record.gateway_request_id,
                    'status': 'OK',
                    'logs': status.logs if hasattr(status, 'logs') and status.logs else [],
                    'metrics': status.metrics if hasattr(status, 'metrics') else {},
                    'payload': result
                }
                job_record.process_webhook_result(webhook_data)
                return status

            else:
                # Estado desconocido o error
                _logger.error(f"Tipo de estado desconocido devuelto por FAL AI: {class_name}")
                webhook_data = {
                    'request_id': job_record.external_job_id,
                    'gateway_request_id': job_record.gateway_request_id,
                    'status': 'ERROR',
                    'error': f"Tipo de estado desconocido: {class_name}",
                    'payload': None
                }
                job_record.write({'state': 'error', 'result': json.dumps(webhook_data)})
                return status

        except Exception as e:
            job_record.write({'state': 'failed', 'error_message': str(e)})
            _logger.error(f"Error al comprobar el estado del trabajo en FAL AI: {str(e)} ")

    def fal_ai_cancel_generation_job(self, external_job_id):
        """Cancel a generation job with FAL AI"""
        self.ensure_one()

        # FAL AI doesn't provide a direct cancel API in the current client
        # This is a placeholder implementation
        _logger.warning(f"FAL AI job cancellation not supported by API. Job ID: {external_job_id}")

        # In a real implementation, you would make an API call to cancel the job
        # For now, we just log the attempt
        return {"status": "cancel_not_supported"}

    def _fal_ai_extract_urls_from_result(self, result):
        """Extract URLs from fal_ai result, handling FileOutput objects and other formats"""
        urls = []

        if result is None:
            return urls
        # Example of fal_ai result: {'has_nsfw_concepts': [False], 'images': [{'content_type': 'image/png', 'height': 768, 'url': 'https://v3.fal.media/files/zebra/3Sa_l4tFKlX4-bai5Z0ST.png', 'width': 1024}], 'prompt': 'a blue cat', 'seed': 6252023, 'timings': {'inference': 2.1407407799270004}}
        if isinstance(result, list):
            # If result is a list, extract URLs from each item
            for item in result:
                url = self._fal_ai_extract_single_url(item)
                if url:
                    urls.append(url)

        elif isinstance(result, dict):
            # If result is a dictionary, check for 'images' key or other URL fields
            if "images" in result:
                for item in result["images"]:
                    url = self._fal_ai_extract_single_url(item)
                    if url:
                        urls.append(url)
            else:
                # Check for other potential URL fields in the dictionary
                url = self._fal_ai_extract_single_url(result)
                if url:
                    urls.append(url)

        else:
            # If result is a single item (not a list or dict), extract URL directly
            url = self._fal_ai_extract_single_url(result)
            if url:
                urls.append(url)

        return urls

    def _fal_ai_extract_single_url(self, item):
        """Extract URL from a single result item"""
        if isinstance(item, dict):
            if "url" in item:
                return item["url"]
            elif "content" in item and isinstance(item["content"], str):
                return item["content"]

    ###############WEBHOOKS####################
    def _is_fal_webhook(self, request):
        """Check if this is a FAL webhook by looking for signature headers"""
        required_headers = [
            'X-Fal-Webhook-Request-Id',
            'X-Fal-Webhook-User-Id',
            'X-Fal-Webhook-Timestamp',
            'X-Fal-Webhook-Signature'
        ]
        return all(request.httprequest.headers.get(header) for header in required_headers)

    def _verify_fal_webhook(self, request, webhook_data):
        """Verify FAL webhook signature"""
        if not NACL_AVAILABLE:
            _logger.warning("PyNaCl not available, skipping webhook verification")
            return True  # Skip verification if PyNaCl is not available

        try:
            # Extract headers
            request_id = request.httprequest.headers.get('X-Fal-Webhook-Request-Id')
            user_id = request.httprequest.headers.get('X-Fal-Webhook-User-Id')
            timestamp = request.httprequest.headers.get('X-Fal-Webhook-Timestamp')
            signature_hex = request.httprequest.headers.get('X-Fal-Webhook-Signature')

            if not all([request_id, user_id, timestamp, signature_hex]):
                _logger.error("Missing required webhook headers")
                return False

            # Get raw body
            body = request.httprequest.get_data()

            return self._verify_webhook_signature(
                request_id, user_id, timestamp, signature_hex, body
            )

        except Exception as e:
            _logger.error(f"Error verifying webhook signature: {e}")
            return False

    def _verify_webhook_signature(self, request_id: str, user_id: str, timestamp: str,
                                  signature_hex: str, body: bytes) -> bool:
        """Verify webhook signature using FAL's method"""
        try:
            # Validate timestamp (within ±5 minutes)
            timestamp_int = int(timestamp)
            current_time = int(time.time())
            if abs(current_time - timestamp_int) > 300:
                _logger.error("Timestamp is too old or in the future")
                return False
        except ValueError:
            _logger.error("Invalid timestamp format")
            return False

        try:
            # Construct the message to verify
            message_parts = [
                request_id,
                user_id,
                timestamp,
                hashlib.sha256(body).hexdigest()
            ]

            if any(part is None for part in message_parts):
                _logger.error("Missing required header value")
                return False

            message_to_verify = "\n".join(message_parts).encode("utf-8")
        except Exception as e:
            _logger.error(f"Error constructing message: {e}")
            return False

        try:
            # Decode signature
            signature_bytes = bytes.fromhex(signature_hex)
        except ValueError:
            _logger.error("Invalid signature format (not hexadecimal)")
            return False

        # Fetch and verify with public keys
        try:
            public_keys_info = self._fetch_jwks()
            if not public_keys_info:
                _logger.error("No public keys found in JWKS")
                return False
        except Exception as e:
            _logger.error(f"Error fetching JWKS: {e}")
            return False

        # Verify signature with each public key
        for key_info in public_keys_info:
            try:
                public_key_b64url = key_info.get("x")
                if not isinstance(public_key_b64url, str):
                    continue

                public_key_bytes = base64.urlsafe_b64decode(public_key_b64url)
                verify_key = VerifyKey(public_key_bytes.hex(), encoder=HexEncoder)
                verify_key.verify(message_to_verify, signature_bytes)
                return True

            except (BadSignatureError, Exception) as e:
                _logger.debug(f"Verification failed with a key: {e}")
                continue

        _logger.error("Signature verification failed with all keys")
        return False

    def _fetch_jwks(self) -> list:
        """Fetch and cache JWKS, refreshing after 24 hours"""
        global _jwks_cache, _jwks_cache_time

        current_time = time.time()
        if _jwks_cache is None or (current_time - _jwks_cache_time) > JWKS_CACHE_DURATION:
            try:
                response = requests.get(JWKS_URL, timeout=10)
                response.raise_for_status()
                _jwks_cache = response.json().get("keys", [])
                _jwks_cache_time = current_time
            except Exception as e:
                _logger.error(f"Failed to fetch JWKS: {e}")
                return _jwks_cache or []

        return _jwks_cache
