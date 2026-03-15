import logging
import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Define default values as constants
DEFAULT_CHUNK_SIZE = 200
DEFAULT_CHUNK_OVERLAP = 20


class LLMKnowledgeChunker(models.Model):
    _inherit = "llm.resource"

    # Chunking configuration fields
    chunker = fields.Selection(
        selection="_get_available_chunkers",
        string="Chunker",
        default="default",
        required=True,
        help="Method used to chunk resource content",
        tracking=True,
    )
    target_chunk_size = fields.Integer(
        string="Target Chunk Size",
        default=200,
        required=True,
        help="Target size of chunks in tokens",
        tracking=True,
    )
    target_chunk_overlap = fields.Integer(
        string="Chunk Overlap",
        default=20,
        required=True,
        help="Number of tokens to overlap between chunks",
        tracking=True,
    )

    chunk_ids = fields.One2many(
        "llm.knowledge.chunk",
        "resource_id",
        string="Chunks",
    )
    chunk_count = fields.Integer(
        string="Chunk Count",
        compute="_compute_chunk_count",
        store=True,
    )

    @api.model
    def _get_available_chunkers(self):
        """Get all available chunker methods"""
        return [("default", "Default Chunker")]

    @api.depends("chunk_ids")
    def _compute_chunk_count(self):
        for record in self:
            record.chunk_count = len(record.chunk_ids)

    def action_view_chunks(self):
        """Open a view with all chunks for this resource"""
        self.ensure_one()
        return {
            "name": _("Resource Chunks"),
            "view_mode": "list,form",
            "res_model": "llm.knowledge.chunk",
            "domain": [("resource_id", "=", self.id)],
            "type": "ir.actions.act_window",
            "context": {"default_resource_id": self.id},
        }

    def chunk(self):
        """Split the document into chunks"""
        for resource in self:
            if resource.state != "parsed":
                _logger.warning(
                    "Resource %s must be in parsed state to create chunks", resource.id
                )
                continue

        # Lock resources and process only the successfully locked ones
        resources = self._lock()
        if not resources:
            return False

        try:
            # Process each resource
            for resource in resources:
                try:
                    # Use appropriate chunker based on selection
                    success = False
                    if resource.chunker == "default":
                        success = resource._chunk_default()
                    else:
                        _logger.warning(
                            "Unknown chunker %s, falling back to default",
                            resource.chunker,
                        )
                        success = resource._chunk_default()

                    if success:
                        # Mark as chunked
                        resource.write({"state": "chunked"})
                    else:
                        resource._post_styled_message(
                            "Failed to create chunks - no content or empty result",
                            "warning",
                        )

                except Exception as e:
                    resource._post_styled_message(
                        f"Error chunking resource: {str(e)}", "error"
                    )
                    resource._unlock()

            # Unlock all successfully processed resources
            resources._unlock()
            return True

        except Exception as e:
            resources._unlock()
            raise UserError(_("Error in batch chunking: %s") % str(e)) from e

    def _chunk_default(self):
        """
        Default implementation for splitting document into chunks.
        Uses a simple sentence-based splitting approach.
        """
        self.ensure_one()

        if not self.content:
            raise UserError(_("No content to chunk"))

        # Delete existing chunks
        self.chunk_ids.unlink()

        # Get chunking parameters
        chunk_size = self.target_chunk_size
        chunk_overlap = min(
            self.target_chunk_overlap, chunk_size // 2
        )  # Ensure overlap is not too large

        # Split content into sentences (simple regex-based approach)
        # Note: for a more sophisticated approach, consider using a NLP library
        sentences = re.split(r"(?<=[.!?])\s+", self.content)

        # Function to estimate token count (approximation)
        def estimate_tokens(text):
            # Simple approximation: 1 token ≈ 4 characters for English text
            return len(text) // 4

        # Create chunks using a sliding window approach
        chunks = []
        current_chunk = []
        current_size = 0

        for _i, sentence in enumerate(sentences):
            sentence_tokens = estimate_tokens(sentence)

            # If a single sentence exceeds chunk size, we have to include it anyway
            if current_size + sentence_tokens > chunk_size and current_chunk:
                # Create a chunk from accumulated sentences
                chunk_text = " ".join(current_chunk)
                chunk_seq = len(chunks) + 1

                # Create chunk record
                chunk = self.env["llm.knowledge.chunk"].create(
                    {
                        "resource_id": self.id,
                        "sequence": chunk_seq,
                        "content": chunk_text,
                        # Note: No need to set collection_ids as it's a related field
                    }
                )
                chunks.append(chunk)

                # Handle overlap: keep some sentences for the next chunk
                overlap_tokens = 0
                overlap_sentences = []

                # Work backwards through current_chunk to build overlap
                for sent in reversed(current_chunk):
                    sent_tokens = estimate_tokens(sent)
                    if overlap_tokens + sent_tokens <= chunk_overlap:
                        overlap_sentences.insert(0, sent)
                        overlap_tokens += sent_tokens
                    else:
                        break

                # Start new chunk with overlap sentences
                current_chunk = overlap_sentences
                current_size = overlap_tokens

            # Add current sentence to the chunk
            current_chunk.append(sentence)
            current_size += sentence_tokens

        # Don't forget the last chunk if there's anything left
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            chunk_seq = len(chunks) + 1

            # Create chunk record
            chunk = self.env["llm.knowledge.chunk"].create(
                {
                    "resource_id": self.id,
                    "sequence": chunk_seq,
                    "content": chunk_text,
                    # Note: No need to set collection_ids as it's a related field
                }
            )
            chunks.append(chunk)

        # Post success message
        self._post_styled_message(
            f"Created {len(chunks)} chunks (target size: {chunk_size}, overlap: {chunk_overlap})",
            "success",
        )

        return len(chunks) > 0

    def action_reset_chunk_settings(self):
        """Reset chunk settings to system defaults"""

        # Reset all selected resources to default values
        self.write(
            {
                "target_chunk_size": DEFAULT_CHUNK_SIZE,
                "target_chunk_overlap": DEFAULT_CHUNK_OVERLAP,
                "chunker": "default",
            }
        )

        # Return action to reload the form view
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id if len(self) == 1 else False,
            "view_mode": "form" if len(self) == 1 else "list,form",
            "target": "current",
        }
