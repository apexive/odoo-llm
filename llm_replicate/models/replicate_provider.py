import logging
import base64

import jsonref
import replicate

from odoo import api, models

_logger = logging.getLogger(__name__)


class LLMProvider(models.Model):
    _inherit = "llm.provider"

    REPLICATE_TRANSCRIPTION_FIELD_CANDIDATES = (
        "audio",
        "audio_file",
        "file",
        "input_audio",
        "media",
        "audio_url",
        "file_url",
    )

    REPLICATE_PROMPT_FIELD_CANDIDATES = (
        "prompt",
        "initial_prompt",
    )

    REPLICATE_LANGUAGE_FIELD_CANDIDATES = (
        "language",
        "language_code",
    )

    @api.model
    def _get_available_services(self):
        services = super()._get_available_services()
        return services + [("replicate", "Replicate")]

    def replicate_get_client(self):
        """Get Replicate client instance"""
        return replicate.Client(api_token=self.api_key)

    def replicate_chat(self, messages, model=None, stream=False, **kwargs):
        """Send chat messages using Replicate"""
        model = self.get_model(model, "chat")

        # Format messages for Replicate
        # Most Replicate models expect a simple prompt string
        prompt = "\n".join(f"{msg['role']}: {msg['content']}" for msg in messages)

        response = self.client.run(model.name, input={"prompt": prompt})

        if not stream:
            # Replicate responses can vary by model, handle common formats
            content = (
                "".join(response)
                if isinstance(response, list) or isinstance(response, tuple)
                else str(response)
            )
            yield {"role": "assistant", "content": content}
        else:
            for chunk in response:
                yield {"role": "assistant", "content": str(chunk)}

    def replicate_embedding(self, texts, model=None):
        """Generate embeddings using Replicate"""
        model = self.get_model(model, "embedding")

        if not isinstance(texts, list):
            texts = [texts]

        response = self.client.run(model.name, input={"sentences": texts})

        # Ensure we return a list of embeddings
        if len(texts) == 1:
            return [response] if not isinstance(response, list) else response
        return response

    def replicate_models(self, model_id=None):
        self.ensure_one()
        """List available Replicate models with pagination support"""

        # If a specific model ID is requested, fetch just that model
        if model_id:
            model = self.client.models.get(model_id)
            yield self._replicate_parse_model(model)
        else:
            # If no specific model requested, fetch all models with pagination
            cursor = ...

            while cursor:
                # Get page of results
                page = self.client.models.list(cursor=cursor)

                # Process models in current page
                for model in page.results:
                    yield self._replicate_parse_model(model)

                cursor = page.next
                if cursor is None:
                    break

    def _replicate_parse_model(self, model):
        details = self.serialize_model_data(model.dict())
        capabilities = []
        model_id_lower = model.id.lower()
        if "chat" in model_id_lower or "llm" in model_id_lower:
            capabilities.append("chat")
        if "embedding" in model_id_lower:
            capabilities.append("embedding")
        if any(kw in model_id_lower for kw in ["vision", "image", "multimodal"]):
            capabilities.append("multimodal")
        if any(kw in model_id_lower for kw in ["transcribe", "transcription", "whisper"]):
            capabilities.append("transcription")
        return {
            "id": model.id,
            "name": model.id,
            "details": details,
            "capabilities": capabilities or ["image_generation"],
        }

    def replicate_should_generate_transcription_schema(self, model_record):
        return self.replicate_should_generate_io_schema(model_record)

    def replicate_generate_transcription_schema(self, model_record):
        return self.replicate_generate_io_schema(model_record)

    def replicate_transcribe_audio(
        self,
        data,
        filename,
        mimetype,
        model=None,
        prompt=None,
        language=None,
        **kwargs,
    ):
        """Transcribe audio with a Replicate transcription model."""
        model = self.get_model(model, "transcription")
        model_name = model._replicate_model_name_with_version() or model.name

        inputs = self._replicate_build_transcription_inputs(
            model=model,
            data=data,
            filename=filename,
            mimetype=mimetype,
            prompt=prompt,
            language=language,
        )
        result = self.client.run(model_name, input=inputs)
        parsed = self._replicate_parse_transcription_output(result)

        return {
            "text": parsed.get("text", ""),
            "language": parsed.get("language"),
            "duration": parsed.get("duration"),
            "model": model.name,
        }

    def replicate_should_generate_io_schema(self, model_record):
        """Check if I/O schema should be generated for this Replicate model.

        Schema should be generated if:
        1. Model has details with OpenAPI schema from the API
        2. Model doesn't already have input_schema in details (to avoid regenerating)

        Args:
            model_record (llm.model): The model record to check

        Returns:
            bool: True if schema generation should be triggered
        """
        return (
            model_record.details
            and model_record.details.get("latest_version", {}).get("openapi_schema")
            and not model_record.details.get("input_schema")
        )

    def replicate_generate_io_schema(self, model_record):
        """Generate a configuration from Replicate model details

        Args:
            model_record (llm.model): The model record to generate config for
        """
        self.ensure_one()

        # Get model details
        details = model_record.details or {}
        model_name = model_record.name

        # Extract OpenAPI schema from details
        openapi_schema = None
        if details.get("latest_version", {}).get("openapi_schema"):
            openapi_schema = details["latest_version"]["openapi_schema"]

        # Extract and process input schema
        if not openapi_schema:
            raise ValueError(f"No OpenAPI schema found for model {model_name}")

        # proxies=False returns plain dicts instead of JsonRef proxy objects
        resolved_openapi_schema = jsonref.replace_refs(openapi_schema, proxies=False)

        # Extract schemas (now plain dicts, not proxies)
        input_schema = resolved_openapi_schema["components"]["schemas"]["Input"]
        output_schema = resolved_openapi_schema["components"]["schemas"]["Output"]

        # Enforce additionalProperties: false to validate against unknown fields
        input_schema["additionalProperties"] = False
        output_schema["additionalProperties"] = False

        # Store schemas in details field
        model_details = dict(model_record.details or {})
        model_details["input_schema"] = input_schema if input_schema else None
        model_details["output_schema"] = output_schema if output_schema else None

        model_record.write({"details": model_details})

    def replicate_generate(self, inputs, model=None, stream=False, **kwargs):
        """Generate content using Replicate

        Returns:
            tuple: (output_dict, urls_list) where:
                - output_dict: Dictionary containing provider-specific output data
                - urls_list: List of dictionaries with URL metadata
        """
        # Get full model name including version if specified
        model_name = model._replicate_model_name_with_version()
        if not model_name:
            model_name = model.name

        if not model_name:
            raise ValueError("Model name is required")

        # Run the model (returns iterator in Replicate 1.0+)
        result = self.client.run(model_name, input=inputs)

        # Materialize true iterators, but preserve single file outputs. Some
        # Replicate models return a FileOutput-like object that is itself
        # iterable over bytes/chunks; blindly wrapping it in list(result)
        # explodes one media file into hundreds of bogus "outputs".
        if not stream:
            result = self._replicate_prepare_result_for_extraction(result)

        # Extract URLs with metadata from the result
        urls = self._replicate_extract_urls_with_metadata(result)

        # Create output data (exclude raw FileOutput objects - not JSON serializable)
        output_data = {
            "model_name": model_name,
            "inputs": inputs,
            "provider": "replicate",
            "num_outputs": len(urls),
        }

        if stream:
            return self._replicate_stream_media_result(output_data, urls)
        else:
            return (output_data, urls)

    def _replicate_prepare_result_for_extraction(self, result):
        """Normalize Replicate output before URL extraction.

        Keep single file output objects intact even if they are iterable, and
        only materialize genuine iterators/generators into lists.
        """
        if result is None:
            return None

        if hasattr(result, "url") or isinstance(result, (str, bytes, bytearray)):
            return result

        if isinstance(result, (list, tuple, dict)):
            return result

        try:
            iter(result)
        except TypeError:
            return result

        return list(result)

    def _replicate_build_transcription_inputs(
        self,
        model,
        data,
        filename,
        mimetype,
        prompt=None,
        language=None,
    ):
        schema = ((model.details or {}).get("input_schema") or {}).get("properties", {})
        inputs = {}
        data_uri = f"data:{mimetype or 'application/octet-stream'};base64,{base64.b64encode(data).decode()}"

        for field_name in self.REPLICATE_TRANSCRIPTION_FIELD_CANDIDATES:
            if field_name in schema:
                inputs[field_name] = data_uri
                break
        else:
            inputs["audio"] = data_uri

        if "filename" in schema:
            inputs["filename"] = filename
        elif "file_name" in schema:
            inputs["file_name"] = filename

        if prompt:
            for field_name in self.REPLICATE_PROMPT_FIELD_CANDIDATES:
                if field_name in schema:
                    inputs[field_name] = prompt
                    break
            else:
                inputs["prompt"] = prompt

        if language:
            for field_name in self.REPLICATE_LANGUAGE_FIELD_CANDIDATES:
                if field_name in schema:
                    inputs[field_name] = language
                    break
            else:
                inputs["language"] = language

        return inputs

    def _replicate_parse_transcription_output(self, result):
        result = self._replicate_prepare_result_for_extraction(result)

        if isinstance(result, str):
            return {"text": result, "language": None, "duration": None}

        if isinstance(result, (list, tuple)):
            if len(result) == 1:
                return self._replicate_parse_transcription_output(result[0])
            return {
                "text": "\n".join(str(item) for item in result if item is not None),
                "language": None,
                "duration": None,
            }

        if isinstance(result, dict):
            text = self._replicate_extract_transcription_text(result)
            return {
                "text": text or "",
                "language": result.get("language") or result.get("detected_language"),
                "duration": result.get("duration") or result.get("audio_duration"),
            }

        return {"text": str(result), "language": None, "duration": None}

    def _replicate_extract_transcription_text(self, payload):
        for key in (
            "text",
            "transcript",
            "transcription",
            "output",
            "result",
            "prediction",
        ):
            value = payload.get(key)
            if isinstance(value, str):
                return value
            if isinstance(value, dict):
                nested = self._replicate_extract_transcription_text(value)
                if nested:
                    return nested
            if isinstance(value, list):
                parts = [str(item) for item in value if isinstance(item, (str, int, float))]
                if parts:
                    return "\n".join(parts)
        return ""

    def _replicate_stream_media_result(self, output_data, urls):
        """Stream media generation results

        This is a separate generator function to avoid making the main method a generator.
        """
        yield {"content": (output_data, urls)}

    def _replicate_extract_urls_with_metadata(self, result):
        """Extract URLs with metadata from Replicate result"""
        urls = []

        if result is None:
            return urls

        # Handle list of results
        if isinstance(result, (list, tuple)):
            for item in result:
                url_data = self._replicate_extract_single_url_with_metadata(item)
                if url_data:
                    urls.append(url_data)
        else:
            # Handle single result
            url_data = self._replicate_extract_single_url_with_metadata(result)
            if url_data:
                urls.append(url_data)

        return urls

    def _replicate_extract_single_url_with_metadata(self, item):
        """Extract URL with metadata from a single result item"""
        if item is None:
            return None

        # Extract URL from different item types
        url = None
        if hasattr(item, "url"):
            url = item.url
        elif isinstance(item, str):
            url = item
        else:
            url = str(item)

        if not url:
            return None

        # Extract filename from URL
        filename = url.split("/")[-1] or "generated_content"

        # Determine content type from file extension
        extension_map = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
            ".mp4": "video/mp4",
            ".mp3": "audio/mpeg",
            ".wav": "audio/wav",
            ".flac": "audio/flac",
            ".ogg": "audio/ogg",
            ".m4a": "audio/mp4",
        }

        content_type = "application/octet-stream"
        filename_lower = filename.lower()
        for ext, mime_type in extension_map.items():
            if filename_lower.endswith(ext):
                content_type = mime_type
                break

        return {
            "url": url,
            "content_type": content_type,
            "filename": filename,
        }
