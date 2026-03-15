import io
import json
import logging
import uuid

from openai import OpenAI

from odoo import api, models
from odoo.exceptions import UserError

from ..utils.openai_message_validator import OpenAIMessageValidator

_logger = logging.getLogger(__name__)

OPENAI_TO_ODOO_STATE_MAPPING = {
    "validating_files": "validating",
    "preparing": "preparing",
    "queued": "queued",
    "running": "training",
    "succeeded": "completed",
    "failed": "failed",
    "cancelled": "cancelled",
}


class LLMProvider(models.Model):
    _inherit = "llm.provider"

    @api.model
    def _get_available_services(self):
        services = super()._get_available_services()
        return services + [("openai", "OpenAI")]

    def openai_get_client(self):
        """Get OpenAI client instance"""
        return OpenAI(api_key=self.api_key, base_url=self.api_base or None)

    def openai_normalize_prepend_messages(self, prepend_messages):
        """Normalize prepend_messages for OpenAI format.

        OpenAI accepts both string and list content formats,
        so no transformation needed.

        Args:
            prepend_messages: List of message dicts to normalize

        Returns:
            List of message dicts (unchanged)
        """
        return prepend_messages or []

    # OpenAI specific implementation
    def openai_format_tools(self, tools):
        """Format tools for OpenAI"""
        return [self._openai_format_tool(tool) for tool in tools]

    def _openai_format_tool(self, tool):
        """Convert a tool to OpenAI format

        Args:
            tool: llm.tool record to convert

        Returns:
            Dictionary in OpenAI tool format
        """
        try:
            if tool.input_schema:
                try:
                    schema = json.loads(tool.input_schema)
                    return self._create_openai_tool_from_schema(schema, tool)
                except json.JSONDecodeError:
                    _logger.error(f"Invalid JSON schema for tool {tool.name}")

            schema = tool.get_input_schema()
            if schema:
                return self._create_openai_tool_from_schema(schema, tool)

            _logger.warning(
                f"Could not get schema for tool {tool.name}, using fallback",
            )
            schema = {"type": "object", "properties": {}, "required": []}
            return self._create_openai_tool_from_schema(schema, tool)

        except Exception as e:
            _logger.error(f"Error formatting tool {tool.name}: {e!s}", exc_info=True)
            schema = {
                "title": tool.name,
                "description": tool.description,
                "properties": {},
                "required": [],
            }
            return self._create_openai_tool_from_schema(schema, tool)

    def _recursively_patch_schema_items(self, schema_node):
        """Recursively ensure 'items' dictionaries have a 'type' defined."""
        if not isinstance(schema_node, dict):
            return

        if "items" in schema_node and isinstance(schema_node["items"], dict):
            items_dict = schema_node["items"]
            if "type" not in items_dict:
                items_dict["type"] = "string"
            self._recursively_patch_schema_items(items_dict)

        if "properties" in schema_node and isinstance(schema_node["properties"], dict):
            for prop_schema in schema_node["properties"].values():
                self._recursively_patch_schema_items(prop_schema)

        for combiner in ["anyOf", "allOf", "oneOf"]:
            if combiner in schema_node and isinstance(schema_node[combiner], list):
                for sub_schema in schema_node[combiner]:
                    self._recursively_patch_schema_items(sub_schema)

    def _create_openai_tool_from_schema(self, schema, tool):
        """Convert a JSON schema dictionary to an OpenAI tool format,
        patching missing item types recursively.
        Args:
            schema: JSON schema dictionary
            tool: llm.tool record

        Returns:
            Dictionary in OpenAI tool format
        """
        if not schema:
            _logger.warning(
                f"Could not generate schema for tool {tool.name}, skipping.",
            )
            return None

        # Ensure all nested 'items' have a 'type' for broader compatibility
        parameters_schema = schema  # Modify the schema directly before formatting
        self._recursively_patch_schema_items(parameters_schema)

        # Format according to OpenAI requirements
        formatted_tool = {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": {
                    "type": "object",
                    "properties": parameters_schema.get("properties", {}),
                    "required": parameters_schema.get("required", []),
                },
            },
        }

        return formatted_tool

    def openai_chat(
        self,
        messages,
        model=None,
        stream=False,
        tools=None,
        prepend_messages=None,
        **kwargs,
    ):
        """Send chat messages using OpenAI with tools support.

        Args:
            messages: mail.message recordset to send
            model: Optional specific model to use
            stream: Whether to stream the response
            tools: llm.tool recordset of available tools
            prepend_messages: List of pre-formatted message dicts to prepend
            **kwargs: Additional OpenAI-specific parameters (e.g., tool_choice)

        Returns:
            Generator yielding response chunks if streaming, else complete response
        """
        model = self.get_model(model, "chat")

        formatted_messages = self.format_messages(messages, model=model)

        # Prepend messages (system prompts, etc.) if provided
        if prepend_messages:
            formatted_messages = prepend_messages + formatted_messages

        # Build params
        params = {
            "model": model.name,
            "stream": stream,
            "messages": formatted_messages,
        }

        # Add tools if provided (OpenAI-specific formatting)
        if tools:
            formatted_tools = self.format_tools(tools)
            if formatted_tools:
                params["tools"] = formatted_tools
                # OpenAI-specific: tool_choice param (Ollama doesn't support this)
                params["tool_choice"] = kwargs.get("tool_choice", "auto")

        # Make the API call
        response = self.client.chat.completions.create(**params)

        # Process the response based on streaming mode
        if not stream:
            return self._openai_process_non_streaming_response(response)
        return self._openai_process_streaming_response(response)

    def _openai_process_non_streaming_response(self, response):
        """Processes OpenAI non-streamed response and returns ONE standardized dict."""
        _logger.info("Processing non-streaming OpenAI response.")
        try:
            choice = response.choices[0]
            message = choice.message
            result = {}

            if message.content:
                result["content"] = message.content

            if message.tool_calls:
                result["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in message.tool_calls
                ]

            if "content" in result or "tool_calls" in result:
                return result
            _logger.warning(
                "OpenAI non-streaming response had no content or tool calls.",
            )
            return {}  # Return empty dict if nothing to process

        except (AttributeError, IndexError, Exception) as e:
            _logger.exception("Error processing OpenAI non-streaming response")
            return {"error": f"Error processing response: {e}"}

    def _openai_process_streaming_response(self, response_stream):
        """
        Processes OpenAI stream and yields standardized dicts for start_thread_loop.
        Yields: {'content': str} OR {'tool_calls': list} OR {'error': str}
        """
        assembled_tool_calls = {}
        final_tool_calls_list = []
        stream_has_tools = False
        finish_reason = None

        try:
            for chunk in response_stream:
                choice = chunk.choices[0] if chunk.choices else None
                delta = choice.delta if choice else None
                chunk_finish_reason = choice.finish_reason if choice else None
                if chunk_finish_reason:
                    finish_reason = chunk_finish_reason

                if not delta:
                    continue

                if delta.content:
                    yield {"content": delta.content}

                if delta.tool_calls:
                    stream_has_tools = True
                    # index can be null, so we use a counter as fallback
                    call_counter = 0
                    for tool_call_chunk in delta.tool_calls:
                        index = tool_call_chunk.index or call_counter
                        assembled_tool_calls = self._update_openai_tool_call_chunk(
                            assembled_tool_calls,
                            tool_call_chunk,
                            index,
                        )
                        call_counter += 1
            if stream_has_tools:
                if finish_reason == "tool_calls" or (
                    finish_reason != "error" and assembled_tool_calls
                ):
                    for index, call_data in sorted(assembled_tool_calls.items()):
                        if call_data.get("_complete"):
                            tool_call_id = call_data.get("id").strip() or str(
                                uuid.uuid4(),
                            )
                            final_tool_calls_list.append(
                                {
                                    # Generate a UUID for id if it's empty, google apis don't give tool call id for example
                                    "id": tool_call_id,
                                    "type": call_data.get(
                                        "type",
                                        "function",
                                    ),  # Default type
                                    "function": {
                                        "name": call_data["function"]["name"],
                                        "arguments": call_data["function"]["arguments"],
                                    },
                                },
                            )
                        else:
                            yield {
                                "error": f"Received incomplete tool call data from provider for tool index {index}.",
                            }

                    if final_tool_calls_list:
                        yield {"tool_calls": final_tool_calls_list}
                    elif assembled_tool_calls:
                        _logger.warning(
                            "Stream indicated tool calls, but none were successfully assembled.",
                        )

                elif finish_reason != "error":
                    _logger.warning(
                        f"OpenAI stream had tool chunks but finished with reason '{finish_reason}'. Not yielding tool calls.",
                    )

        except Exception as e:
            yield {"error": f"Internal error processing stream: {e}"}

    def _update_openai_tool_call_chunk(self, tool_call_chunks, tool_call_chunk, index):
        """
        Helper to assemble fragmented tool calls from OpenAI stream chunks.
        (Keep this helper as it's essential for stream processing)
        """
        if index not in tool_call_chunks:
            tool_call_chunks[index] = {
                "id": tool_call_chunk.id,
                "type": tool_call_chunk.type,
                "function": {"name": "", "arguments": ""},
                "_complete": False,
            }

        current_call = tool_call_chunks[index]

        if tool_call_chunk.id:
            current_call["id"] = tool_call_chunk.id
        if tool_call_chunk.type:
            current_call["type"] = tool_call_chunk.type

        func_chunk = tool_call_chunk.function
        if func_chunk:
            if func_chunk.name:
                current_call["function"]["name"] = func_chunk.name
            if func_chunk.arguments:
                current_call["function"]["arguments"] += func_chunk.arguments

        # Use the common helper to determine completeness for OpenAI
        current_call["_complete"] = self._is_tool_call_complete(
            current_call["function"],
            expected_endings=("]", "}"),
        )

        return tool_call_chunks

    def openai_embedding(self, texts, model=None):
        """Generate embeddings using OpenAI"""
        model = self.get_model(model, "embedding")

        response = self.client.embeddings.create(model=model.name, input=texts)
        return [r.embedding for r in response.data]

    def openai_models(self, model_id=None):
        """List available OpenAI models"""
        if model_id:
            model = self.client.models.retrieve(model_id)
            yield self._openai_parse_model(model)
        else:
            models = self.client.models.list()
            for model in models.data:
                yield self._openai_parse_model(model)

    # OpenAI API doesn't expose capabilities - use pattern matching
    OPENAI_VISION_PATTERNS = (
        "gpt-4o",
        "gpt-4-turbo",
        "gpt-4.1",
        "gpt-4-vision",
        "gpt-5",
        "o1",
        "o3",
    )

    def _openai_parse_model(self, model):
        capabilities = ["chat"]
        model_id_lower = model.id.lower()

        if "text-embedding" in model_id_lower or "embedding" in model_id_lower:
            capabilities = ["embedding"]
        elif any(p in model_id_lower for p in self.OPENAI_VISION_PATTERNS):
            capabilities = ["chat", "multimodal"]

        return {
            "name": model.id,
            "details": {
                "id": model.id,
                "capabilities": capabilities,
                **model.model_dump(),
            },
        }

    def _validate_and_clean_messages(self, messages):
        """
        Validate and clean messages to ensure proper tool message structure for OpenAI.

        This method uses the OpenAIMessageValidator class to check that all tool messages
        have a preceding assistant message with matching tool_calls, and removes any
        tool messages that don't meet this requirement to avoid API errors.

        Args:
            messages (list): List of messages to validate and clean

        Returns:
            list: Cleaned list of messages
        """
        # Hardcoded value for verbose logging
        verbose_logging = False

        validator = OpenAIMessageValidator(
            messages,
            logger=_logger,
            verbose_logging=verbose_logging,
        )
        return validator.validate_and_clean()

    def openai_format_messages(self, messages, system_prompt=None, model=None):
        """Format messages for OpenAI API

        Args:
            messages: mail.message recordset to format
            system_prompt: Optional system prompt (deprecated, use prepend_messages)
            model: llm.model record (to determine if multimodal)

        Returns:
            List of formatted messages in OpenAI-compatible format
        """
        is_multimodal = model and model.model_use == "multimodal"
        formatted_messages = []

        if system_prompt:
            formatted_messages.append({"role": "system", "content": system_prompt})

        for message in messages:
            formatted_message = self._dispatch(
                "format_message",
                record=message,
                is_multimodal=is_multimodal,
            )
            if formatted_message:
                formatted_messages.append(formatted_message)

        result_messages = self._validate_and_clean_messages(formatted_messages)

        return result_messages

    def openai_upload_file(self, file_tuple, purpose="fine-tune"):
        """Upload a file to OpenAI"""
        response = self.client.files.create(file=file_tuple, purpose=purpose)
        return response

    def openai_create_training_job(
        self,
        training_file_id,
        model_name,
        hyperparameters=None,
    ):
        """Create an OpenAI fine-tuning job."""
        self.ensure_one()

        hyperparameters = hyperparameters or {}
        hyperparams_cleaned = {
            k: v for k, v in hyperparameters.items() if v is not None
        }

        response = self.client.fine_tuning.jobs.create(
            training_file=training_file_id,
            model=model_name,
            # Pass None if cleaned dict is empty, otherwise pass the dict
            hyperparameters=hyperparams_cleaned if hyperparams_cleaned else None,
        )
        _logger.info(
            f"Fine-tuning job created successfully for provider '{self.name}'. Job ID: {response.id}",
        )
        return response

    def openai_retrieve_training_job(self, job_id):
        """Retrieve an OpenAI fine-tuning job."""
        self.ensure_one()
        response = self.client.fine_tuning.jobs.retrieve(job_id)
        return response

    def openai_cancel_training_job(self, job_id):
        """Cancel an OpenAI fine-tuning job."""
        self.ensure_one()
        response = self.client.fine_tuning.jobs.cancel(job_id)
        return response

    def openai_validate_datasets(self, job):
        """Validate datasets for training"""
        if not job.dataset_ids:
            raise UserError(
                f"Job '{job.name}': Please select at least one dataset before validating.",
            )

        for dataset in job.dataset_ids:
            result = dataset.validate_dataset()
            if not result["valid"]:
                raise UserError(
                    f"Validation failed for job '{job.name}':\nDataset '{dataset.name}': {result['message']}",
                )

        return True

    def openai_start_training_job(self, job):
        """Start a training job with the provider."""
        self.ensure_one()

        if not job.dataset_ids:
            raise UserError(f"Job '{self.name}': No datasets linked for preparation.")

        final_combined_bytes = self._openai_get_combined_content_bytes(job)

        if not final_combined_bytes:
            raise UserError(
                f"Job '{job.name}': Combined content from all datasets is empty after processing.",
            )

        # Create a filename for the upload (e.g., based on job name or dataset name)
        upload_filename = f"{job.name or 'job'}_combined_datasets.jsonl"

        file_obj = io.BytesIO(final_combined_bytes)
        file_tuple = (upload_filename, file_obj)

        file_upload_response = job.provider_id.upload_file(
            file_tuple,
            purpose="fine-tune",
        )
        training_file_id = file_upload_response.id

        # hyperparameters is a Json field, already a dict
        hyperparameters = job.hyperparameters or {}

        training_job_response = job.provider_id.create_training_job(
            training_file_id=training_file_id,
            model_name=job.base_model_id.name,
            hyperparameters=hyperparameters,
        )

        return {
            "training_job_id": training_job_response.id,
        }

    @api.model
    def _openai_get_combined_content_bytes(self, job):
        """Get combined content bytes for OpenAI"""
        all_datasets_bytes = []
        dataset_names = []
        for dataset in job.dataset_ids:
            content_bytes = dataset._get_combined_content_bytes()
            if content_bytes:
                all_datasets_bytes.append(content_bytes)
                dataset_names.append(dataset.name)
            else:
                _logger.warning(
                    f"Dataset '{dataset.name}' for job '{job.name}' resulted in empty content, skipping.",
                )

        if not all_datasets_bytes:
            raise UserError(
                f"Job '{job.name}': No valid content found in any linked dataset.",
            )

        final_combined_bytes = b"".join(all_datasets_bytes)

        if not final_combined_bytes:
            raise UserError(
                f"Job '{self.name}': Combined content from all datasets is empty after processing.",
            )

        return final_combined_bytes

    def openai_check_training_job_status(self, job):
        """Check the status of a training job with the provider."""
        self.ensure_one()
        response = job.provider_id.retrieve_training_job(job_id=job.external_job_id)
        state_to_return = OPENAI_TO_ODOO_STATE_MAPPING.get(response.status)
        model_dump = response.model_dump()
        if response.status == "succeeded":
            models_data = job.provider_id.list_models(
                model_id=response.fine_tuned_model,
            )
            for model_data in models_data:
                details = model_data.get("details", {})
                name = model_data.get("name") or details.get("id")

                if not name:
                    continue

                # Determine model use and capabilities
                capabilities = details.get("capabilities", ["chat"])
                model_use = job.provider_id._determine_model_use(name, capabilities)

                vals = {
                    "name": name,
                    "model_use": model_use,
                    "details": details,
                    "provider_id": job.provider_id.id,
                    "active": True,
                }
                model_exists = self.env["llm.model"].search([("name", "=", name)])
                if not model_exists:
                    result = self.env["llm.model"].create(vals)
                else:
                    result = model_exists

                return {
                    "state": state_to_return,
                    "result_model_id": result.id,
                    "trained_model_name": response.fine_tuned_model,
                    "response": model_dump,
                }

        return {
            "state": state_to_return,
            "response": model_dump,
        }
