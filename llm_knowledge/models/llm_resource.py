import logging
from datetime import timedelta

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class LLMResource(models.Model):
    _name = "llm.resource"
    _description = "LLM Resource for Document Management"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"
    _sql_constraints = [
        (
            "unique_resource_reference",
            "UNIQUE(model_id, res_id)",
            "A resource already exists for this record. Please use the existing resource.",
        ),
    ]

    name = fields.Char(
        string="Name",
        required=True,
        tracking=True,
    )
    model_id = fields.Many2one(
        "ir.model",
        string="Related Model",
        required=True,
        tracking=True,
        ondelete="cascade",
        help="The model of the referenced document",
    )
    res_model = fields.Char(
        string="Model Name",
        related="model_id.model",
        store=True,
        readonly=True,
        help="Technical name of the related model",
    )
    res_id = fields.Integer(
        string="Record ID",
        required=True,
        tracking=True,
        help="The ID of the referenced record",
    )
    content = fields.Text(
        string="Content",
        help="Markdown representation of the resource content",
    )
    external_url = fields.Char(
        string="External URL",
        compute="_compute_external_url",
        store=True,
        help="External URL from the related record if available",
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("retrieved", "Retrieved"),
            ("parsed", "Parsed"),
            ("chunked", "Chunked"),
            ("ready", "Ready"),
        ],
        string="State",
        default="draft",
        tracking=True,
    )
    lock_date = fields.Datetime(
        string="Lock Date",
        tracking=True,
        help="Date when the resource was locked for processing",
    )
    kanban_state = fields.Selection(
        [
            ("normal", "Ready"),
            ("blocked", "Blocked"),
            ("done", "Done"),
        ],
        string="Kanban State",
        compute="_compute_kanban_state",
        store=True,
    )

    collection_ids = fields.Many2many(
        "llm.knowledge.collection",
        relation="llm_knowledge_resource_collection_rel",
        column1="resource_id",
        column2="collection_id",
        string="Collections",
    )

    @api.depends("res_model", "res_id")
    def _compute_external_url(self):
        for resource in self:
            resource.external_url = False
            if not resource.res_model or not resource.res_id:
                continue

            resource.external_url = self._get_record_external_url(
                resource.res_model, resource.res_id
            )

    def _get_record_external_url(self, res_model, res_id):
        """
        Get the external URL for a record based on its model and ID.

        This method can be extended by other modules to support additional models.

        :param res_model: The model name
        :param res_id: The record ID
        :return: The external URL or False
        """
        try:
            # Get the related record
            if res_model in self.env:
                record = self.env[res_model].browse(res_id)
                if not record.exists():
                    return False

                # Case 1: Handle ir.attachment with type 'url'
                if res_model == "ir.attachment" and hasattr(record, "type"):
                    if record.type == "url" and hasattr(record, "url"):
                        return record.url

                # Case 2: Check if record has an external_url field
                elif hasattr(record, "external_url"):
                    return record.external_url

        except Exception as e:
            _logger.warning(
                "Error computing external URL for resource model %s, id %s: %s",
                res_model,
                res_id,
                str(e),
            )

        return False

    @api.depends("lock_date")
    def _compute_kanban_state(self):
        for record in self:
            record.kanban_state = "blocked" if record.lock_date else "normal"

    def _lock(self, state_filter=None, stale_lock_minutes=10):
        """Lock resources for processing and return the ones successfully locked"""
        now = fields.Datetime.now()
        stale_lock_threshold = now - timedelta(minutes=stale_lock_minutes)

        # Find resources that are not locked or have stale locks
        domain = [
            ("id", "in", self.ids),
            "|",
            ("lock_date", "=", False),
            ("lock_date", "<", stale_lock_threshold),
        ]
        if state_filter:
            domain.append(("state", "=", state_filter))

        unlocked_docs = self.env["llm.resource"].search(domain)

        if unlocked_docs:
            unlocked_docs.write({"lock_date": now})

        return unlocked_docs

    def _unlock(self):
        """Unlock resources after processing"""
        return self.write({"lock_date": False})

    def process_resource(self):
        """
        Process resources through retrieval, parsing, chunking and embedding.
        Can handle multiple resources at once, processing them through
        as many pipeline stages as possible based on their current states.
        """
        # Stage 1: Retrieve content for draft resources
        draft_docs = self.filtered(lambda d: d.state == "draft")
        if draft_docs:
            draft_docs.retrieve()

        # Stage 2: Parse retrieved resources
        retrieved_docs = self.filtered(lambda d: d.state == "retrieved")
        if retrieved_docs:
            retrieved_docs.parse()

        # Process chunking and embedding
        inconsistent_docs = self.filtered(
            lambda d: d.state in ["chunked", "ready"] and not d.chunk_ids
        )

        if inconsistent_docs:
            inconsistent_docs.write({"state": "parsed"})

        # Process chunks for parsed documents
        parsed_docs = self.filtered(lambda d: d.state == "parsed")
        if parsed_docs:
            parsed_docs.chunk()

        # Embed chunked documents
        chunked_docs = self.filtered(lambda d: d.state == "chunked")
        if chunked_docs:
            chunked_docs.embed()

        return True

    def action_open_resource(self):
        """Open the resource in form view."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "llm.resource",
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
        }

    @api.model
    def action_mass_process_resources(self):
        """
        Server action handler for mass processing resources.
        This will be triggered from the server action in the UI.
        """
        active_ids = self.env.context.get("active_ids", [])
        if not active_ids:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("No Resources Selected"),
                    "message": _("Please select resources to process."),
                    "type": "warning",
                    "sticky": False,
                },
            }

        resources = self.browse(active_ids)
        # Process all selected resources
        result = resources.process_resource()

        if result:
            return {
                "type": "ir.actions.client",
                "tag": "reload",
            }

        else:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Processing Failed"),
                    "message": _("Mass processing resources failed"),
                    "sticky": False,
                    "type": "danger",
                },
            }

    def action_mass_unlock(self):
        """
        Mass unlock action for the server action.
        """
        # Unlock the resources
        self._unlock()

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Resources Unlocked"),
                "message": _("%(count)s resources have been unlocked", count=len(self)),
                "sticky": False,
                "type": "success",
            },
        }

    def action_mass_reset(self):
        """
        Mass reset action for the server action.
        Resets all non-draft resources back to draft state.
        """
        # Get active IDs from context
        active_ids = self.env.context.get("active_ids", [])
        if not active_ids:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("No Resources Selected"),
                    "message": _("Please select resources to reset."),
                    "type": "warning",
                    "sticky": False,
                },
            }

        resources = self.browse(active_ids)
        # Filter resources that are not in draft state
        non_draft_resources = resources.filtered(lambda r: r.state != "draft")

        if not non_draft_resources:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("No Resources Reset"),
                    "message": _("No resources found that need resetting."),
                    "type": "warning",
                    "sticky": False,
                },
            }

        # Reset resources to draft state and unlock them
        non_draft_resources.write(
            {
                "state": "draft",
                "lock_date": False,
            }
        )

        # Reload the view to reflect changes
        return {
            "type": "ir.actions.client",
            "tag": "reload",
            "params": {
                "menu_id": self.env.context.get("menu_id"),
                "action": self.env.context.get("action"),
            },
        }

    def action_embed(self):
        """Action handler for embedding document chunks"""
        result = self.embed()
        # Return appropriate notification
        if result:
            self._post_styled_message(
                _("Document embedding process completed successfully."),
                "success",
            )
            return True
        else:
            message = (
                _(
                    "Document embedding process did not complete properly, check logs on resources."
                ),
            )

            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Embedding"),
                    "message": message,
                    "type": "warning",
                    "sticky": False,
                },
            }

    def action_reindex(self):
        """Reindex a single resource's chunks"""
        self.ensure_one()

        # Get all collections this resource belongs to
        collections = self.collection_ids
        if not collections:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Reindexing"),
                    "message": _("Resource does not belong to any collections."),
                    "type": "warning",
                },
            }

        # Get all chunks for this resource
        chunks = self.chunk_ids
        if not chunks:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Reindexing"),
                    "message": _("No chunks found for this resource."),
                    "type": "warning",
                },
            }

        # Set resource back to chunked state to trigger re-embedding
        self.write({"state": "chunked"})

        # Delete chunks from each collection's store
        for collection in collections:
            if collection.store_id:
                # Remove chunks from this resource from the store
                try:
                    collection.delete_vectors(ids=chunks.ids)
                except Exception as e:
                    _logger.warning(
                        f"Error removing vectors for chunks from collection {collection.id}: {str(e)}"
                    )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Reindexing"),
                "message": _(
                    f"Reset resource for re-embedding in {len(collections)} collections."
                ),
                "type": "success",
            },
        }

    def action_mass_reindex(self):
        """Reindex multiple resources at once"""
        collections = self.env["llm.knowledge.collection"]
        for resource in self:
            # Add to collections set
            collections |= resource.collection_ids

        # Reindex each affected collection
        for collection in collections:
            collection.reindex_collection()

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Reindexing"),
                "message": _(
                    f"Reindexing request submitted for {len(collections)} collections."
                ),
                "type": "success",
                "sticky": False,
            },
        }

    def embed(self):
        """
        Embed resource chunks in collections by calling the collection's embed_resources method.
        Called after chunking to create vector representations.

        Returns:
            bool: True if any resources were successfully embedded, False otherwise
        """
        # Filter to only get resources in chunked state
        chunked_docs = self.filtered(lambda d: d.state == "chunked")

        if not chunked_docs:
            self._post_styled_message(
                _("No resources in 'chunked' state to embed."),
                "warning",
            )
            return False

        # Get all collections for these resources
        collections = self.env["llm.knowledge.collection"]
        for doc in chunked_docs:
            collections |= doc.collection_ids

        # If no collections, resources can't be embedded
        if not collections:
            self._post_styled_message(
                _("No collections found for the selected resources."),
                "warning",
            )
            return False

        # Track if any resources were embedded
        any_embedded = False

        # Let each collection handle the embedding
        for collection in collections:
            result = collection.embed_resources(specific_resource_ids=chunked_docs.ids)
            # Check if result is not None before trying to access .get()
            if (
                result
                and result.get("success")
                and result.get("processed_resources", 0) > 0
            ):
                any_embedded = True

        if not any_embedded:
            self._post_styled_message(
                _(
                    "No resources could be embedded. Check that resources have correct collections and collections have valid embedding models and stores."
                ),
                "warning",
            )
        # Return True only if resources were actually embedded
        return any_embedded

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to handle collection_ids and apply chunking settings"""
        # Create the resources first
        resources = super().create(vals_list)

        # Process each resource that has collections
        for resource in resources:
            if resource.collection_ids and resource.state not in ["chunked", "ready"]:
                # Get the first collection's settings
                collection = resource.collection_ids[0]
                # Update the resource with the collection's settings
                update_vals = {
                    "target_chunk_size": collection.default_chunk_size,
                    "target_chunk_overlap": collection.default_chunk_overlap,
                    "chunker": collection.default_chunker,
                    "parser": collection.default_parser,
                }
                resource.write(update_vals)

        return resources

    def _reset_state_if_needed(self):
        """Reset resource state to 'chunked' if it's in 'ready' state and not in any collection."""
        self.ensure_one()
        if self.state == "ready" and not self.collection_ids:
            self.write({"state": "chunked"})
            _logger.info(
                f"Reset resource {self.id} to 'chunked' state after removal from all collections"
            )
            self._post_styled_message(
                _("Reset to 'chunked' state after removal from all collections"),
                "info",
            )
        return True

    def _handle_collection_ids_change(self, old_collections_by_resource):
        """Handle changes to collection_ids field.

        Args:
            old_collections_by_resource: Dictionary mapping resource IDs to their previous collection IDs
        """
        for resource in self:
            old_collection_ids = old_collections_by_resource.get(resource.id, [])
            current_collection_ids = resource.collection_ids.ids

            # Find collections that the resource was removed from
            removed_collection_ids = [
                cid for cid in old_collection_ids if cid not in current_collection_ids
            ]

            # Clean up vectors in those collections' stores
            if removed_collection_ids:
                collections = self.env["llm.knowledge.collection"].browse(
                    removed_collection_ids
                )
                for collection in collections:
                    # Use the collection's method to handle resource removal
                    collection._handle_removed_resources([resource.id])

        return True

    def write(self, vals):
        """Override write to handle collection_ids changes and cleanup vectors if needed"""
        # Track collections before the write
        resources_collections = {}
        if "collection_ids" in vals:
            for resource in self:
                resources_collections[resource.id] = resource.collection_ids.ids

        # Perform the write operation
        result = super().write(vals)

        # Handle collection changes
        if "collection_ids" in vals:
            self._handle_collection_ids_change(resources_collections)

        return result
