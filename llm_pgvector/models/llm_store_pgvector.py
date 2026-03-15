import logging

from pgvector import Vector
from pgvector.psycopg2 import register_vector

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class LLMStorePgVector(models.Model):
    _inherit = "llm.store"
    _description = "PgVector Store Implementation"

    @api.model
    def _get_available_services(self):
        services = super()._get_available_services()
        return services + [("pgvector", "PGVector")]

    # PgVector specific configuration options
    pgvector_index_method = fields.Selection(
        [
            ("ivfflat", "IVFFlat (faster search)"),
            ("hnsw", "HNSW (balanced)"),
        ],
        string="Index Method",
        default="ivfflat",
        help="The index method to use for vector search",
    )

    # -------------------------------------------------------------------------
    # Store Interface Implementation
    # -------------------------------------------------------------------------

    # Add the specific sanitization method for pgvector compatibility
    def pgvector_sanitize_collection_name(self, name):
        """Sanitize a collection name for pgvector (uses default)."""
        # Although pgvector doesn't use collection names directly,
        # no-op for now
        return name

    def pgvector_collection_exists(self, collection_id):
        """Check if a collection exists - for pgvector, collections always 'exist'"""
        self.ensure_one()

        # For pgvector, we always return True as we're using the existing Odoo tables
        # and not creating separate collections
        return True

    def pgvector_create_collection(
        self, collection_id, dimension=None, metadata=None, **kwargs
    ):
        """Create a collection - for pgvector, this is a no-op"""
        self.ensure_one()

        # For pgvector, creating a collection is essentially a no-op
        # since we're using the existing Odoo tables
        collection = self.env["llm.knowledge.collection"].browse(collection_id)
        if not collection.exists():
            _logger.warning(f"Collection {collection_id} does not exist")
            return False

        # But we might want to create the index for the embedding model
        if collection.embedding_model_id:
            self._create_vector_index(collection.embedding_model_id.id)

        return True

    def pgvector_delete_collection(self, collection_id):
        """Delete a collection - for pgvector, we just drop indexes"""
        self.ensure_one()

        # For pgvector, deleting a collection just means dropping its indexes
        collection = self.env["llm.knowledge.collection"].browse(collection_id)
        if not collection.exists():
            return True

        # Get embedding model ID
        embedding_model_id = (
            collection.embedding_model_id.id if collection.embedding_model_id else False
        )
        if not embedding_model_id:
            return True  # Nothing to delete if no embedding model

        # Drop any vector indexes for this embedding model
        self._drop_vector_index(embedding_model_id)

        # Find chunks that belong to this collection
        chunks = self.env["llm.knowledge.chunk"].search(
            [("collection_ids", "in", [collection_id])]
        )

        # Identify chunks that don't belong to other collections with the same embedding model
        chunks_to_delete = []
        for chunk in chunks:
            other_collections = chunk.collection_ids - collection
            if not any(
                c.embedding_model_id.id == embedding_model_id for c in other_collections
            ):
                chunks_to_delete.append(chunk.id)

        # Delete embeddings in a batch
        if chunks_to_delete:
            self.env["llm.knowledge.chunk.embedding"].search(
                [
                    ("chunk_id", "in", chunks_to_delete),
                    ("embedding_model_id", "=", embedding_model_id),
                ]
            ).unlink()

        return True

    def pgvector_insert_vectors(
        self, collection_id, vectors, metadata=None, ids=None, **kwargs
    ):
        """Insert vectors into collection using batch operations"""
        self.ensure_one()

        # Check parameters
        if not ids or len(ids) != len(vectors):
            raise UserError(_("Must provide chunk IDs matching the vectors"))

        # Get the collection
        collection = self.env["llm.knowledge.collection"].browse(collection_id)
        if not collection.exists() or not collection.embedding_model_id:
            return False

        # Get the embedding model
        embedding_model_id = collection.embedding_model_id.id

        # First, delete any existing embeddings for these chunks with this embedding model
        # This handles the update case by replacing existing embeddings
        if ids:
            self.env["llm.knowledge.chunk.embedding"].search(
                [
                    ("chunk_id", "in", ids),
                    ("embedding_model_id", "=", embedding_model_id),
                ]
            ).unlink()

        # Prepare values for batch creation
        vals_list = []
        for chunk_id, vector in zip(ids, vectors):  # noqa: B905
            vals_list.append(
                {
                    "chunk_id": chunk_id,
                    "embedding_model_id": embedding_model_id,
                    "embedding": vector,
                }
            )

        # Batch create all embeddings in a single operation
        if vals_list:
            self.env["llm.knowledge.chunk.embedding"].create(vals_list)

        # Make sure the index exists
        self._create_vector_index(embedding_model_id)

    def pgvector_delete_vectors(self, collection_id, ids, **kwargs):
        """Delete vectors (embeddings) for specified chunk IDs"""
        self.ensure_one()

        if ids is None:
            return False

        # Get the collection to determine the embedding model
        collection = self.env["llm.knowledge.collection"].browse(collection_id)
        if not collection.exists() or not collection.embedding_model_id:
            return False

        embedding_model_id = collection.embedding_model_id.id
        chunks = self.env["llm.knowledge.chunk"].browse(ids)

        # Get all chunks that don't belong to any other collection with the same embedding model
        chunks_to_delete = []
        for chunk in chunks:
            # Find if this chunk belongs to other collections with the same embedding model
            other_collections = chunk.collection_ids - collection
            if not any(
                c.embedding_model_id.id == embedding_model_id for c in other_collections
            ):
                chunks_to_delete.append(chunk.id)

        # Delete embeddings in a batch if there are any to delete
        if chunks_to_delete:
            self.env["llm.knowledge.chunk.embedding"].search(
                [
                    ("chunk_id", "in", chunks_to_delete),
                    ("embedding_model_id", "=", embedding_model_id),
                ]
            ).unlink()

        return True

    def pgvector_search_vectors(
        self,
        collection_id,
        query_vector,
        limit=10,
        filter=None,
        offset=0,
        query_operator="<=>",
        min_similarity=0.5,
    ):
        """
        Search for similar vectors in the collection

        Returns:
            list of dicts with 'id', 'score', and 'metadata'
        """
        self.ensure_one()

        collection = self.env["llm.knowledge.collection"].browse(collection_id)
        if not collection.exists() or not collection.embedding_model_id:
            return []

        embedding_model_id = collection.embedding_model_id.id

        # Format the query vector using pgvector's Vector class
        register_vector(self.env.cr._cnx)
        vector_str = Vector._to_db(query_vector)

        # Build the query with proper index hints
        index_name = self._get_index_name(
            "llm_knowledge_chunk_embedding", embedding_model_id
        )
        index_hint = f"/*+ IndexScan(llm_knowledge_chunk_embedding {index_name}) */"

        # Execute the query to find similar vectors
        # Join to llm_knowledge_chunk_embedding instead of directly using chunks
        query = f"""
            WITH query_vector AS (
                SELECT '{vector_str}'::vector AS vec
            )
            SELECT {index_hint} e.chunk_id, 1 - (e.embedding {query_operator} query_vector.vec) as score
            FROM llm_knowledge_chunk_embedding e
            JOIN llm_knowledge_chunk c ON e.chunk_id = c.id
            JOIN llm_knowledge_resource_collection_rel rel ON c.resource_id = rel.resource_id
            CROSS JOIN query_vector
            WHERE rel.collection_id = %s
            AND e.embedding_model_id = %s
            AND e.embedding IS NOT NULL
            AND (1 - (e.embedding {query_operator} query_vector.vec)) >= %s
            ORDER BY score DESC
            LIMIT %s
            OFFSET %s
        """

        self.env.cr.execute(
            query, (collection_id, embedding_model_id, min_similarity, limit, offset)
        )
        results = self.env.cr.fetchall()

        # Format results with chunk IDs as the main identifiers
        formatted_results = []
        chunk_ids = []

        for chunk_id, score in results:
            chunk_ids.append(chunk_id)
            formatted_results.append(
                {
                    "id": chunk_id,
                    "score": score,
                    "metadata": {},  # We don't store additional metadata currently
                }
            )

        return formatted_results

    # -------------------------------------------------------------------------
    # Vector Index Management
    # -------------------------------------------------------------------------

    def _get_index_name(self, table_name, embedding_model_id):
        """Generate a consistent index name based on table and embedding model"""
        return f"{table_name}_emb_model_{embedding_model_id}_idx"

    def _create_vector_index(self, embedding_model_id, dimensions=None, force=False):
        """Create a vector index for the specified embedding model"""
        self.ensure_one()

        # Get the embedding model to determine dimensions if not provided
        if not dimensions and embedding_model_id:
            embedding_model = self.env["llm.model"].browse(embedding_model_id)
            if embedding_model.exists():
                # Generate a sample embedding to determine dimensions
                sample_embedding = embedding_model.embedding("")[0]
                dimensions = len(sample_embedding) if sample_embedding else None

        cr = self.env.cr
        table_name = "llm_knowledge_chunk_embedding"

        # Register vector with this cursor
        register_vector(cr._cnx)

        # Generate index name
        index_name = self._get_index_name(table_name, embedding_model_id)

        # Check if index already exists
        if force:
            # Drop existing index if force is True
            cr.execute(f"DROP INDEX IF EXISTS {index_name}")
        else:
            # Check if index exists
            cr.execute(
                """
                    SELECT 1 FROM pg_indexes
                    WHERE indexname = %s
                """,
                (index_name,),
            )

            # If index already exists, return early
            if cr.fetchone():
                _logger.info(f"Index {index_name} already exists, skipping creation")
                return True

        # Determine the dimension specification
        dim_spec = f"({dimensions})" if dimensions else ""

        # Determine index method
        index_method = self.pgvector_index_method or "ivfflat"

        try:
            # Create appropriate index for this embedding model
            if index_method == "ivfflat":
                # Create IVFFlat index
                cr.execute(
                    f"""
                    CREATE INDEX {index_name} ON {table_name}
                    USING ivfflat((embedding::vector{dim_spec}) vector_cosine_ops)
                    WHERE embedding_model_id = %s AND embedding IS NOT NULL
                """,
                    (embedding_model_id,),
                )
            elif index_method == "hnsw":
                # Try HNSW index if available in pgvector version
                try:
                    cr.execute(
                        f"""
                        CREATE INDEX {index_name} ON {table_name}
                        USING hnsw((embedding::vector{dim_spec}) vector_cosine_ops)
                        WHERE embedding_model_id = %s AND embedding IS NOT NULL
                    """,
                        (embedding_model_id,),
                    )
                except Exception as e:
                    # Fallback to IVFFlat if HNSW is not available
                    _logger.warning(
                        f"HNSW index not supported, falling back to IVFFlat: {str(e)}"
                    )
                    cr.execute(
                        f"""
                        CREATE INDEX {index_name} ON {table_name}
                        USING ivfflat((embedding::vector{dim_spec}) vector_cosine_ops)
                        WHERE embedding_model_id = %s AND embedding IS NOT NULL
                    """,
                        (embedding_model_id,),
                    )

            _logger.info(
                f"Created vector index {index_name} for embedding model {embedding_model_id}"
            )
            return True
        except Exception as e:
            _logger.error(f"Error creating vector index: {str(e)}")
            return False

    def _drop_vector_index(self, embedding_model_id=None):
        """Drop vector index for the specified embedding model"""
        self.ensure_one()
        table_name = "llm_knowledge_chunk_embedding"

        if embedding_model_id:
            # Drop specific index for this model
            index_name = self._get_index_name(table_name, embedding_model_id)
            self.env.cr.execute(f"DROP INDEX IF EXISTS {index_name}")
            _logger.info(f"Dropped vector index {index_name}")
        else:
            # Try to find all indexes for this table
            query = """
                SELECT indexname FROM pg_indexes
                WHERE tablename = %s
            """
            self.env.cr.execute(query, (table_name,))
            indexes = self.env.cr.fetchall()

            # Drop each embedding model index
            for index in indexes:
                if "emb_model_" in index[0]:
                    self.env.cr.execute(f"DROP INDEX IF EXISTS {index[0]}")
                    _logger.info(f"Dropped vector index {index[0]}")

        return True
