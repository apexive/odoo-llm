import logging

from odoo import api, fields, models

from ..fields import PgVector

_logger = logging.getLogger(__name__)


class LLMKnowledgeChunkEmbedding(models.Model):
    _name = "llm.knowledge.chunk.embedding"
    _description = "Vector Embedding for Knowledge Chunks"
    _rec_name = "chunk_id"  # Use chunk name as display name

    chunk_id = fields.Many2one(
        "llm.knowledge.chunk",
        string="Chunk",
        required=True,
        ondelete="cascade",
        index=True,
    )
    # Related field to get collections from chunk's resource
    collection_ids = fields.Many2many(
        "llm.knowledge.collection",
        string="Collections",
        related="chunk_id.collection_ids",
        store=False,
        readonly=True,
    )
    embedding_model_id = fields.Many2one(
        "llm.model",
        string="Embedding Model",
        domain="[('model_use', '=', 'embedding')]",
        required=True,
        ondelete="restrict",
        index=True,
    )
    embedding = PgVector(
        string="Vector Embedding",
        help="Vector embedding for similarity search",
    )

    resource_id = fields.Many2one(
        related="chunk_id.resource_id",
        store=True,
        readonly=True,
        index=True,
    )

    _sql_constraints = [
        (
            "unique_chunk_embedding_model",
            "UNIQUE(chunk_id, embedding_model_id)",
            "A chunk can only have one embedding per embedding model",
        ),
    ]

    def name_get(self):
        """Override to provide a better display name"""
        result = []
        for record in self:
            name = f"{record.chunk_id.name or 'Chunk'} [{record.embedding_model_id.name or 'Model'}]"
            result.append((record.id, name))
        return result

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to handle special cases"""
        for vals in vals_list:
            # If embedding_model_id not provided, try to get from collection
            if not vals.get("embedding_model_id") and vals.get("chunk_id"):
                chunk = self.env["llm.knowledge.chunk"].browse(vals["chunk_id"])
                # Get first collection's embedding model
                if chunk.collection_ids and chunk.collection_ids[0].embedding_model_id:
                    vals["embedding_model_id"] = chunk.collection_ids[
                        0
                    ].embedding_model_id.id

        return super().create(vals_list)
