import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval

from .llm_resource_chunker import DEFAULT_CHUNK_OVERLAP, DEFAULT_CHUNK_SIZE

_logger = logging.getLogger(__name__)


class LLMKnowledgeCollection(models.Model):
    _name = "llm.knowledge.collection"
    _description = "Knowledge Collection for RAG"
    _inherit = ["llm.store.collection", "mail.thread", "mail.activity.mixin"]
    _order = "name"

    name = fields.Char(
        string="Name",
        required=True,
        tracking=True,
    )
    description = fields.Text(
        string="Description",
        tracking=True,
    )
    active = fields.Boolean(
        string="Active",
        default=True,
        tracking=True,
    )
    embedding_model_id = fields.Many2one(
        "llm.model",
        string="Embedding Model",
        domain="[('model_use', '=', 'embedding')]",
        required=True,
        tracking=True,
        help="The model used to create embeddings for documents in this collection",
    )
    resource_ids = fields.Many2many(
        "llm.resource",
        string="Resources",
        relation="llm_knowledge_resource_collection_rel",
        column1="collection_id",
        column2="resource_id",
    )
    # Domain filters for automatically adding resources
    domain_ids = fields.One2many(
        "llm.knowledge.domain",
        "collection_id",
        string="Domain Filters",
        help="Domain filters to select records for RAG document creation",
    )
    resource_count = fields.Integer(
        string="Resource Count",
        compute="_compute_resource_count",
    )
    chunk_count = fields.Integer(
        string="Chunk Count",
        compute="_compute_chunk_count",
    )
    chunk_ids = fields.Many2many(
        "llm.knowledge.chunk",
        string="Chunks (from Resources)",
        compute="_compute_chunk_ids",
        store=False,
        help="Chunks belonging to the resources included in this collection.",
    )

    # Default chunking settings for resources in this collection
    default_chunk_size = fields.Integer(
        string="Default Chunk Size",
        default=DEFAULT_CHUNK_SIZE,
        required=True,
        help="Default target size of chunks in tokens for resources in this collection",
        tracking=True,
    )
    default_chunk_overlap = fields.Integer(
        string="Default Chunk Overlap",
        default=DEFAULT_CHUNK_OVERLAP,
        required=True,
        help="Default number of tokens to overlap between chunks for resources in this collection",
        tracking=True,
    )

    default_chunker = fields.Selection(
        selection="_get_available_chunkers",
        string="Default Chunker",
        default="default",
        required=True,
        help="Default chunker to use for resources in this collection",
        tracking=True,
    )

    default_parser = fields.Selection(
        selection="_get_available_parsers",
        string="Default Parser",
        default="default",
        required=True,
        help="Default parser to use for resources in this collection",
        tracking=True,
    )

    @api.model
    def _get_available_parsers(self):
        return self.env["llm.resource"]._get_available_parsers()

    @api.model
    def _get_available_chunkers(self):
        return self.env["llm.resource"]._get_available_chunkers()

    @api.depends("resource_ids.chunk_ids")
    def _compute_chunk_ids(self):
        for collection in self:
            collection.chunk_ids = collection.resource_ids.mapped("chunk_ids")

    @api.depends("resource_ids")
    def _compute_resource_count(self):
        for record in self:
            record.resource_count = len(record.resource_ids)

    @api.depends("chunk_ids")
    def _compute_chunk_count(self):
        for record in self:
            record.chunk_count = len(record.chunk_ids)

    @api.model_create_multi
    def create(self, vals_list):
        """Extend create to initialize store collection if needed"""
        collections = super().create(vals_list)
        for collection in collections:
            # Initialize the store if one is assigned
            if collection.store_id:
                collection._initialize_store()
            # Apply default chunk settings to resources if they exist
            if collection.resource_ids:
                collection._apply_default_settings_to_resources(
                    update_size=True,
                    update_overlap=True,
                    update_chunker=True,
                    update_parser=True,
                )
        return collections

    def _handle_resource_ids_change(self, old_resources_by_collection):
        """Handle changes to resource_ids field.

        Args:
            old_resources_by_collection: Dictionary mapping collection IDs to their previous resource IDs
        """
        for collection in self:
            old_resource_ids = old_resources_by_collection.get(collection.id, [])
            current_resource_ids = collection.resource_ids.ids

            # Find resources that were removed from this collection
            removed_resource_ids = [
                rid for rid in old_resource_ids if rid not in current_resource_ids
            ]

            # Handle removed resources
            collection._handle_removed_resources(removed_resource_ids)

        return True

    def write(self, vals):
        """Override write to handle various field changes and their effects"""
        # Track embedding model and store changes
        embedding_model_changed = "embedding_model_id" in vals
        store_changed = "store_id" in vals

        # Track resources before the write if resource_ids is changing
        collections_resources = {}
        if "resource_ids" in vals:
            for collection in self:
                collections_resources[collection.id] = collection.resource_ids.ids

        # Track old embedding models and stores for cleanup
        old_embedding_models = {}
        old_stores = {}
        if embedding_model_changed or store_changed:
            for collection in self:
                old_embedding_models[collection.id] = collection.embedding_model_id.id
                old_stores[collection.id] = (
                    collection.store_id.id if collection.store_id else False
                )

        # Perform the write operation
        result = super().write(vals)

        # Handle changes to embedding model or store
        if embedding_model_changed or store_changed:
            for collection in self:
                # If store changed, initialize the new store
                if store_changed:
                    # First, clean up the old store if it existed
                    if old_stores.get(collection.id):
                        old_store = self.env["llm.store"].browse(
                            old_stores[collection.id]
                        )
                        if old_store.exists():
                            collection._cleanup_old_store(old_store)

                    if collection.store_id:
                        collection._initialize_store()

                    collection._reset_ready_resources(
                        success_message=_(
                            "Store changed. Reset {count} resources for re-embedding into the new store."
                        )
                    )
                if embedding_model_changed:
                    collection._reset_ready_resources(
                        success_message=_(
                            "Embedding model changed. Reset {count} resources for re-embedding."
                        )
                    )

        # Handle changes to chunking settings
        if (
            "default_chunk_size" in vals
            or "default_chunk_overlap" in vals
            or "default_chunker" in vals
            or "default_parser" in vals
        ):
            self._apply_default_settings_to_resources(
                update_size="default_chunk_size" in vals,
                update_overlap="default_chunk_overlap" in vals,
                update_chunker="default_chunker" in vals,
                update_parser="default_parser" in vals,
            )

        # Handle resource_ids changes
        if "resource_ids" in vals:
            self._handle_resource_ids_change(collections_resources)

        return result

    def unlink(self):
        """Extend unlink to clean up store data"""
        for collection in self:
            # Clean up store data if a store is assigned
            if collection.store_id:
                try:
                    collection.store_id.delete_collection(collection.id)
                except Exception as e:
                    _logger.warning(f"Error deleting collection from store: {str(e)}")
        return super().unlink()

    def _initialize_store(self):
        """Initialize the store for this collection"""
        if not self.store_id:
            return False

        # Create collection in store if it doesn't exist
        collection_exists = self.store_id.collection_exists(self.id)
        _logger.info(f"collection exists {collection_exists}")
        if not collection_exists:
            created = self.store_id.create_collection(self.id)
            if not created:
                raise UserError(
                    _("Failed to create collection in store for collection %s")
                    % self.name
                )

        _logger.info(f"Initialized store for collection {self.name}")

    def _cleanup_old_store(self, old_store):
        """Clean up the old store when switching to a new one"""
        try:
            # Delete the collection from the old store
            if old_store.collection_exists(self.id):
                old_store.delete_collection(self.id)
            return True
        except Exception as e:
            _logger.warning(f"Error cleaning up old store: {str(e)}")
            return False

    def _reset_ready_resources(
        self, success_message="Reset {{count}} resources for re-embedding."
    ):
        """Finds ready resources, resets their state to 'chunked', and posts a message."""
        self.ensure_one()
        ready_resources = self.resource_ids.filtered(lambda r: r.state == "ready")
        if ready_resources:
            count = len(ready_resources)
            ready_resources.write({"state": "chunked"})
            self._post_styled_message(
                success_message.format(count=count), message_type="info"
            )
            return count
        else:
            return 0

    def action_view_resources(self):
        """Open a view with all resources in this collection"""
        self.ensure_one()
        return {
            "name": _("Collection Resources"),
            "view_mode": "list,form",
            "res_model": "llm.resource",
            "domain": [("id", "in", self.resource_ids.ids)],
            "type": "ir.actions.act_window",
            "context": {"default_collection_ids": [(6, 0, [self.id])]},
        }

    def action_view_chunks(self):
        """Open a view with all chunks from resources in this collection"""
        self.ensure_one()

        return {
            "name": _("Collection Chunks"),
            "view_mode": "list,form",
            "res_model": "llm.knowledge.chunk",
            "domain": [("collection_ids", "=", self.id)],
            "type": "ir.actions.act_window",
        }

    def sync_resources(self):
        """
        Synchronize collection resources with domain filters.
        This will:
        1. Add new resources for records matching domain filters
        2. Remove resources that no longer match domain filters
        """
        for collection in self:
            if not collection.domain_ids:
                continue

            created_count = 0
            linked_count = 0
            removed_count = 0

            # Find all records that match domains across all active domain filters
            matching_records = []
            model_map = {}  # To track which model each record belongs to

            # Process each model and its domain
            for domain_filter in collection.domain_ids.filtered(lambda d: d.active):
                model_name = domain_filter.model_name
                # Validate model exists
                if model_name not in self.env:
                    collection._post_styled_message(
                        _(f"Model '{model_name}' not found. Skipping."),
                        message_type="warning",
                    )
                    continue

                # Get model and evaluate domain
                model = self.env[model_name]
                domain = safe_eval(domain_filter.domain)

                # Search records matching the domain
                records = model.search(domain)

                if not records:
                    collection._post_styled_message(
                        _(
                            f"No records found for model '{domain_filter.model_id.name}' with given domain."
                        ),
                        message_type="info",
                    )
                    continue

                # Store model_id with each record for later use
                for record in records:
                    matching_records.append((model_name, record.id))
                    model_map[(model_name, record.id)] = domain_filter.model_id

            # Get all existing resources in the collection
            existing_docs = collection.resource_ids

            # Track which existing resources should be kept
            docs_to_keep = self.env["llm.resource"]

            # Process all matching records to create/link resources
            for model_name, record_id in matching_records:
                # Get actual record
                record = self.env[model_name].browse(record_id)
                model_id = model_map[(model_name, record_id)].id

                # Check if resource already exists for this record
                existing_doc = self.env["llm.resource"].search(
                    [
                        ("model_id", "=", model_id),
                        ("res_id", "=", record_id),
                    ],
                    limit=1,
                )

                if existing_doc:
                    # Document exists - add to keep list if in our collection
                    if existing_doc in existing_docs:
                        docs_to_keep |= existing_doc
                    # Otherwise link it if not already in the collection
                    elif existing_doc.id not in collection.resource_ids.ids:
                        collection.write({"resource_ids": [(4, existing_doc.id)]})
                        linked_count += 1
                        docs_to_keep |= existing_doc
                else:
                    # Create new resource with meaningful name
                    if hasattr(record, "display_name") and record.display_name:
                        name = record.display_name
                    elif hasattr(record, "name") and record.name:
                        name = record.name
                    else:
                        model_display = self.env["ir.model"]._get(model_name).name
                        name = f"{model_display} #{record_id}"

                    new_doc = self.env["llm.resource"].create(
                        {
                            "name": name,
                            "model_id": model_id,
                            "res_id": record_id,
                            "parser": "json",
                            "collection_ids": [(4, collection.id)],
                        }
                    )
                    docs_to_keep |= new_doc
                    created_count += 1

            # Find resources to remove (those in the collection but not matching any domains)
            docs_to_remove = existing_docs - docs_to_keep

            # Remove resources that no longer match any domains
            if docs_to_remove:
                # Only remove from this collection, not delete the resources
                collection.write(
                    {"resource_ids": [(3, doc.id) for doc in docs_to_remove]}
                )
                removed_count = len(docs_to_remove)

            # Post summary message
            if created_count > 0 or linked_count > 0 or removed_count > 0:
                collection._post_styled_message(
                    _(
                        f"Synchronization complete: Created {created_count} new resources, "
                        f"linked {linked_count} existing resources, "
                        f"removed {removed_count} resources no longer matching domains."
                    ),
                    message_type="success",
                )
            else:
                collection._post_styled_message(
                    _("No changes made - collection is already in sync with domains."),
                    message_type="info",
                )

    def process_resources(self):
        """Process resources through retrieval, parsing, and chunking (up to chunked state)"""
        for collection in self:
            collection.resource_ids.process_resource()

    def reindex_collection(self):
        """
        Reindex all resources in the collection.
        This will reset resource states from 'ready' to 'chunked',
        and recreate the collection in the store if necessary.
        """
        for collection in self:
            # If we have a store, recreate the collection
            if collection.store_id:
                try:
                    # Delete and recreate the collection in the store
                    if collection.store_id.collection_exists(collection.id):
                        collection.store_id.delete_collection(collection.id)

                    # Create the collection again
                    collection.store_id.create_collection(collection.id)

                    # Mark resources for re-embedding
                    reset_count = collection._reset_ready_resources(
                        success_message=_(
                            f"Reset {{count}} resources for re-embedding with model {collection.embedding_model_id.name}."
                        )
                    )
                    if not reset_count:
                        collection._post_styled_message(
                            _("No resources found to reindex."), message_type="info"
                        )

                except Exception as e:
                    collection._post_styled_message(
                        _(f"Error reindexing collection: {str(e)}"),
                        message_type="error",
                    )
            else:
                # For collections without a store, just reset resource states
                reset_count = collection._reset_ready_resources(
                    success_message=_(
                        f"Reset {{count}} resources for re-embedding with model {collection.embedding_model_id.name}."
                    )
                )
                if not reset_count:
                    collection._post_styled_message(
                        _("No resources found to reindex."), message_type="info"
                    )
                else:
                    collection._post_styled_message(
                        message=_(
                            f"Reset {reset_count} resources for re-embedding with model {collection.embedding_model_id.name}."
                        ),
                        message_type="info",
                    )

    def action_open_upload_wizard(self):
        """Open the upload resource wizard with this collection pre-selected"""
        self.ensure_one()
        return {
            "name": "Upload Resources",
            "type": "ir.actions.act_window",
            "res_model": "llm.upload.resource.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_collection_id": self.id,
                "default_resource_name_template": "{filename}",
            },
        }

    def action_embed_resources(self, specific_resource_ids=None):
        """
        Action handler for embedding resources in the UI.
        Wraps the embed_resources method and returns a proper action dictionary.

        Args:
            specific_resource_ids: Optional list of resource IDs to process.
        """
        self.ensure_one()
        result = self.embed_resources(specific_resource_ids=specific_resource_ids)

        # Return a proper action dictionary with the result in context
        if result and result.get("success"):
            return True
        else:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Embedding Failed"),
                    "message": _(
                        "Failed to embed resources. Check the logs for details."
                    ),
                    "type": "warning",
                    "sticky": False,
                },
            }

    def embed_resources(self, specific_resource_ids=None, batch_size=50):
        """
        Embed all chunked resources using the collection's embedding model and store.

        Args:
            specific_resource_ids: Optional list of resource IDs to process.
                                If provided, only chunks from these resources will be processed.
            batch_size: Number of chunks to process in each batch
        """
        for collection in self:
            if not collection.embedding_model_id:
                collection._post_styled_message(
                    _("No embedding model configured for this collection."),
                    message_type="warning",
                )
                continue

            # Ensure we have a store to use
            if not collection.store_id:
                collection._post_styled_message(
                    _("No vector store configured for this collection."),
                    message_type="warning",
                )
                continue

            # Ensure the collection exists in the store
            collection._initialize_store()

            # Search for chunks that belong to chunked resources in this collection
            chunk_domain = [
                ("collection_ids", "=", collection.id),
            ]

            # Add specific resource filter if provided
            if specific_resource_ids:
                chunk_domain.append(("resource_id", "in", specific_resource_ids))
            else:
                chunk_domain.append(("resource_id.state", "=", "chunked"))

            # Get all relevant chunks in one query
            # Fetch chunks and build the target map simultaneously
            chunks_to_process = self.env["llm.knowledge.chunk"].search(chunk_domain)

            if not chunks_to_process:
                message = _("No chunks found for resources in chunked state")
                if specific_resource_ids:
                    message += _(" for the specified resource IDs")
                collection._post_styled_message(message, message_type="info")
                continue

            # Map resource ID to the set of its chunk IDs we intend to process
            resource_target_chunks = {}
            for chunk in chunks_to_process:
                res_id = chunk.resource_id.id
                if res_id not in resource_target_chunks:
                    resource_target_chunks[res_id] = set()
                resource_target_chunks[res_id].add(chunk.id)

            # Process chunks in batches for efficiency
            total_chunks = len(chunks_to_process)
            processed_chunks_count = 0
            # Track which resource IDs had chunks processed
            successfully_processed_chunk_ids = (
                set()
            )  # Track successfully processed chunk IDs
            if not total_chunks:
                message = _("All chunks already have embeddings for the selected model")
                collection._post_styled_message(message, message_type="info")
                continue
            _logger.info(
                f"Collection '{collection.name}': Starting embedding for {total_chunks} chunks from {len(resource_target_chunks)} resources."
            )

            # Process in batches
            for batch_num, i in enumerate(range(0, total_chunks, batch_size)):
                batch = chunks_to_process[i : i + batch_size]
                batch_start_index = i
                batch_end_index = i + len(batch) - 1
                _logger.info(
                    f"Processing batch {batch_num + 1}/{ (total_chunks + batch_size - 1)//batch_size } (chunks {batch_start_index}-{batch_end_index})..."
                )

                # Prepare chunked data for the store
                texts = []
                metadata_list = []
                chunk_ids_in_batch = []  # IDs for this specific batch
                resource_ids_in_batch = set()  # Resources touched in this batch

                for chunk in batch:
                    texts.append(chunk.content)
                    metadata = {
                        "resource_id": chunk.resource_id.id,
                        "resource_name": chunk.resource_id.name,
                        "chunk_id": chunk.id,
                        "sequence": chunk.sequence,
                    }
                    # Add custom metadata if present
                    if chunk.metadata:
                        metadata.update(chunk.metadata)

                    metadata_list.append(metadata)
                    chunk_ids_in_batch.append(chunk.id)
                    resource_ids_in_batch.add(chunk.resource_id.id)

                try:
                    # Generate embeddings using the collection's embedding model
                    embeddings = collection.embedding_model_id.embedding(texts)
                    # Insert vectors into the store
                    collection.insert_vectors(
                        vectors=embeddings,
                        metadata=metadata_list,
                        ids=chunk_ids_in_batch,
                    )

                    # Mark chunks in this batch as successfully processed
                    successfully_processed_chunk_ids.update(chunk_ids_in_batch)
                    processed_chunks_count += len(batch)

                    _logger.info(
                        f"Batch {batch_num + 1} successful. Committing transaction."
                    )
                    # Commit transaction after each successful batch
                    self.env.cr.commit()
                except Exception as e:
                    # Format resource IDs for the message
                    resource_ids_str = ", ".join(
                        map(str, sorted(list(resource_ids_in_batch)))
                    )
                    error_msg = _(
                        "Error processing batch %d (chunks %d-%d, resources [%s]): %s"
                    ) % (
                        batch_num + 1,
                        batch_start_index,
                        batch_end_index,
                        resource_ids_str,
                        str(e),
                    )
                    _logger.error(error_msg)
                    collection._post_styled_message(error_msg, message_type="error")
                    # Post messages to individual resources
                    # Batch read all resources at once
                    self._post_resources_error(resource_ids_in_batch, str(e), batch_num)
                    # Continue with the next batch

            # Update resource states to ready - only update resources that had chunks processed
            # Determine which resources are fully processed
            fully_processed_resource_ids = set()
            for res_id, target_chunks in resource_target_chunks.items():
                if target_chunks.issubset(successfully_processed_chunk_ids):
                    fully_processed_resource_ids.add(res_id)

            return collection._finalize_embedding(
                fully_processed_resource_ids, processed_chunks_count
            )

    def _post_resources_error(self, resource_ids, error_msg, batch_num):
        resources = self.env["llm.resource"].browse(list(resource_ids))
        for resource in resources:
            resource_error_msg = _(
                "Failed to process this resource in batch %d: %s"
            ) % (
                batch_num + 1,
                error_msg,
            )
            resource._post_styled_message(resource_error_msg, message_type="error")

    def _finalize_embedding(self, fully_processed_resource_ids, processed_chunks_count):
        # Update states only for fully processed resources
        if fully_processed_resource_ids:
            _logger.info(
                f"Updating state to 'ready' for {len(fully_processed_resource_ids)} fully processed resources."
            )
            self.env["llm.resource"].browse(list(fully_processed_resource_ids)).write(
                {"state": "ready"}
            )
            # Final commit after state updates
            self.env.cr.commit()

            # Prepare message with resource details for clarity
            doc_count = len(fully_processed_resource_ids)
            msg = _(
                f"Successfully embedded {processed_chunks_count} chunks from {doc_count} resources using {self.embedding_model_id.name}."
            )

            self._post_styled_message(msg, message_type="success")

            return {
                "success": True,
                "processed_chunks": processed_chunks_count,
                "processed_resources": doc_count,
            }
        else:
            # Check if any chunks were processed at all, even if no resource was fully completed
            if processed_chunks_count > 0:
                message = (
                    _(
                        "Processed %d chunks, but no resources were fully completed due to errors in some batches."
                    )
                    % processed_chunks_count
                )
            else:
                message = _(
                    "No chunks were successfully embedded. Check logs for errors."
                )

            _logger.warning(f"Collection '{self.name}': {message}")
            self._post_styled_message(message, message_type="warning")

            return {
                "success": False,
                "processed_chunks": processed_chunks_count,
                "processed_resources": 0,
            }

    def _apply_default_settings_to_resources(
        self,
        update_size=True,
        update_overlap=True,
        update_chunker=True,
        update_parser=True,
    ):
        """Apply collection chunk settings to all resources in this collection"""
        for collection in self:
            if not collection.resource_ids:
                continue

            # Only update the fields that were changed
            update_vals = {}
            if update_size:
                update_vals["target_chunk_size"] = collection.default_chunk_size
            if update_overlap:
                update_vals["target_chunk_overlap"] = collection.default_chunk_overlap
            if update_chunker:
                update_vals["chunker"] = collection.default_chunker
            if update_parser:
                update_vals["parser"] = collection.default_parser
            if update_vals:
                collection.resource_ids.write(update_vals)

    # Helper method for resource-collection relationship changes
    def _handle_removed_resources(self, removed_resource_ids):
        """Handle cleanup for resources that were removed from this collection.

        Args:
            removed_resource_ids: List of resource IDs that were removed
        """
        self.ensure_one()

        if removed_resource_ids:
            _logger.info(
                f"Resources {removed_resource_ids} were removed from collection {self.id}"
            )

            # Process each removed resource
            resources = self.env["llm.resource"].browse(removed_resource_ids)
            for resource in resources:
                # Handle resource removal (vector cleanup)
                self._handle_resource_removal(resource)

                # Reset resource state if needed
                resource._reset_state_if_needed()

        return True

    def _handle_resource_removal(self, resource):
        """Handle cleanup when a resource is removed from this collection.

        This method:
        1. Removes vectors from the collection's store
        2. Posts appropriate messages

        Args:
            resource: The resource record that was removed
        """
        self.ensure_one()

        if self.store_id and self.store_id.collection_exists(self.id):
            # Get chunks for this resource
            chunks = resource.chunk_ids
            if chunks:
                try:
                    # Delete vectors using chunk IDs directly
                    self.delete_vectors(ids=chunks.ids)
                    _logger.info(
                        f"Removed vectors for {len(chunks)} chunks from resource {resource.id} in collection {self.id}"
                    )
                    self._post_styled_message(
                        _("Vectors removed for resource %s") % resource.name,
                        "info",
                    )
                    resource._post_styled_message(
                        _("Vectors removed from collection %s") % self.name,
                        "info",
                    )
                except Exception as e:
                    _logger.warning(
                        f"Error removing vectors for resource {resource.id} from collection {self.id}: {str(e)}"
                    )
                    self._post_styled_message(
                        _("Error removing vectors for resource %s") % resource.name,
                        "warning",
                    )
                    resource._post_styled_message(
                        _("Error removing vectors from collection %s") % self.name,
                        "warning",
                    )

        return True
