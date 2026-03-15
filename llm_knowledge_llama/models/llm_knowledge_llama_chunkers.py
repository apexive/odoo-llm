import logging

from odoo import _, api, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    from llama_index.core import Document as LlamaDocument
    from llama_index.core.node_parser import (
        HierarchicalNodeParser,
        MarkdownNodeParser,
        SentenceSplitter,
        TokenTextSplitter,
    )

    HAS_LLAMA_INDEX = True
except ImportError:
    _logger.warning("Could not import llama_index, make sure it is installed.")
    HAS_LLAMA_INDEX = False


class LLMResourceLlamaChunker(models.Model):
    _inherit = "llm.resource"

    @api.model
    def _get_available_chunkers(self):
        """
        Extend the available chunkers to include LlamaIndex's chunkers.
        """
        chunkers = super()._get_available_chunkers()
        chunkers.extend(
            [
                ("llama_markdown", "LlamaIndex Markdown Chunker"),
                ("llama_sentence", "LlamaIndex Sentence Splitter"),
                ("llama_token", "LlamaIndex Token Splitter"),
                ("llama_hierarchical", "LlamaIndex Hierarchical Chunker"),
            ]
        )
        return chunkers

    @api.model
    def default_get(self, fields_list):
        """
        Override default_get to set the default chunker to llama_markdown if LlamaIndex is installed.
        """
        res = super().default_get(fields_list)

        if "chunker" in fields_list and HAS_LLAMA_INDEX:
            res["chunker"] = "llama_markdown"

        return res

    def _create_chunks_from_nodes(self, nodes, get_extra_metadata=None):
        """Create chunks from LlamaIndex nodes"""
        created_chunks = []
        for idx, node in enumerate(nodes, 1):
            metadata = (
                {
                    **node.metadata,
                    "start_char_idx": getattr(node, "start_char_idx", None),
                    "end_char_idx": getattr(node, "end_char_idx", None),
                }
                if hasattr(node, "metadata")
                else {}
            )

            # Add extra metadata if provided
            if get_extra_metadata:
                extra_metadata = get_extra_metadata(node)
                if extra_metadata:
                    metadata.update(extra_metadata)

            chunk = self.env["llm.knowledge.chunk"].create(
                {
                    "resource_id": self.id,
                    "sequence": idx,
                    "content": node.text,
                    "metadata": metadata,
                }
            )
            created_chunks.append(chunk)

        return created_chunks

    def _finalize_chunking(self, created_chunks, chunker_name, extra_info=""):
        """Finalize chunking process with success message"""
        message = (
            f"Created {len(created_chunks)} chunks using LlamaIndex {chunker_name}"
        )
        if extra_info:
            message += f" {extra_info}"

        self._post_styled_message(message, "success")
        return len(created_chunks) > 0

    def _chunk_llama_markdown(self):
        """
        LlamaIndex Markdown-aware chunker that respects markdown structure.
        This is particularly useful since llm.document content is always in markdown format.
        """

        llama_doc = self._prepare_llama_chunking()

        # Use the MarkdownNodeParser
        parser = MarkdownNodeParser()
        nodes = parser.get_nodes_from_documents([llama_doc])

        # Create chunks from the parsed nodes
        created_chunks = self._create_chunks_from_nodes(nodes)

        # Post success message
        return self._finalize_chunking(created_chunks, "MarkdownNodeParser")

    def _chunk_llama_sentence(self):
        """
        LlamaIndex sentence-based chunker with customizable chunk size and overlap.
        """

        llama_doc = self._prepare_llama_chunking()

        # Use SentenceSplitter with the configured chunk sizes
        splitter = SentenceSplitter(
            chunk_size=self.target_chunk_size,
            chunk_overlap=self.target_chunk_overlap,
        )
        nodes = splitter.get_nodes_from_documents([llama_doc])

        # Create chunks
        created_chunks = self._create_chunks_from_nodes(nodes)

        # Post success message
        return self._finalize_chunking(
            created_chunks,
            "SentenceSplitter",
            f"(size: {self.target_chunk_size}, overlap: {self.target_chunk_overlap})",
        )

    def _chunk_llama_token(self):
        """
        LlamaIndex token-based chunker for precise token-count chunking.
        """

        llama_doc = self._prepare_llama_chunking()

        # Use TokenTextSplitter with the configured chunk sizes
        splitter = TokenTextSplitter(
            chunk_size=self.target_chunk_size,
            chunk_overlap=self.target_chunk_overlap,
        )
        nodes = splitter.get_nodes_from_documents([llama_doc])

        # Create chunks
        created_chunks = self._create_chunks_from_nodes(nodes)

        # Post success message
        return self._finalize_chunking(
            created_chunks,
            "TokenTextSplitter",
            f"(size: {self.target_chunk_size}, overlap: {self.target_chunk_overlap})",
        )

    def _chunk_llama_hierarchical(self):
        """
        LlamaIndex hierarchical chunker that creates nested chunks at multiple levels of granularity.
        """

        llama_doc = self._prepare_llama_chunking()
        # Use HierarchicalNodeParser
        # We'll use chunk sizes of 2048, 512, and 128 tokens
        chunk_sizes = [2048, 512, 128]
        parser = HierarchicalNodeParser.from_defaults(chunk_sizes=chunk_sizes)
        nodes = parser.get_nodes_from_documents([llama_doc])

        # Create chunks with hierarchical level metadata
        created_chunks = self._create_chunks_from_nodes(
            nodes, lambda node: {"hierarchical_level": getattr(node, "level", 0)}
        )

        # Post success message
        return self._finalize_chunking(
            created_chunks, "HierarchicalNodeParser", f"with sizes {chunk_sizes}"
        )

    def _prepare_llama_chunking(self):
        """Common preparation for LlamaIndex chunking"""
        self.ensure_one()

        if not HAS_LLAMA_INDEX:
            raise UserError(
                _(
                    "LlamaIndex is not installed. Please install it with pip: pip install llama_index"
                )
            )

        if not self.content:
            raise UserError(_("No content to chunk"))

        # Delete existing chunks
        self.chunk_ids.unlink()

        # Create a LlamaIndex document
        return LlamaDocument(
            text=self.content,
            metadata={
                "name": self.name,
                "res_model": self.res_model,
                "res_id": self.res_id,
            },
        )

    def chunk(self):
        """Override to add LlamaIndex chunking methods"""
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
                    success = False

                    # Use the appropriate chunker based on selection
                    if resource.chunker == "llama_markdown":
                        success = resource._chunk_llama_markdown()
                    elif resource.chunker == "llama_sentence":
                        success = resource._chunk_llama_sentence()
                    elif resource.chunker == "llama_token":
                        success = resource._chunk_llama_token()
                    elif resource.chunker == "llama_hierarchical":
                        success = resource._chunk_llama_hierarchical()
                    else:
                        # Fall back to original chunking methods
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
