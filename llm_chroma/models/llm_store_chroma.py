import logging
from urllib.parse import urlparse

import chromadb

from odoo import _, api, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class LLMStoreChroma(models.Model):
    _inherit = "llm.store"
    _description = "Chroma Vector Store Implementation"

    @api.model
    def _get_available_services(self):
        services = super()._get_available_services()
        return services + [("chroma", "Chroma")]

    # Add the specific sanitization method for Chroma
    def chroma_sanitize_collection_name(self, name):
        """Sanitize a collection name for Chroma.
        Chroma's rules match the default sanitizer.
        """
        return self._default_sanitize_collection_name(name)

    # -------------------------------------------------------------------------
    # Chroma Client Management
    # -------------------------------------------------------------------------

    def _get_chroma_client(self):
        """Get a Chroma client for the current store configuration"""
        self.ensure_one()
        if self.service != "chroma":
            return None

        parsed_uri = urlparse(self.connection_uri or "")

        # Determine if SSL is needed
        ssl = parsed_uri.scheme == "https"

        # Extract host and port
        host = parsed_uri.hostname or "localhost"
        port = parsed_uri.port or 8000

        # Create and return the HTTP client
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else None

        try:
            client = chromadb.HttpClient(host=host, port=port, ssl=ssl, headers=headers)
            # Test connection
            client.heartbeat()
            return client
        except Exception as err:
            _logger.error("Failed to connect to Chroma server: %s", err)
            raise UserError(
                _(
                    "Could not connect to the Chroma vector database server.\n\n"
                    "Please check:\n"
                    "• The server is running\n"
                    "• The connection URL is correct in provider settings\n"
                    "• Network/firewall allows the connection\n\n"
                    "Technical details: %s"
                )
                % str(err)
            ) from err

    # -------------------------------------------------------------------------
    # Collection Management
    # -------------------------------------------------------------------------

    def chroma_collection_exists(self, collection_id, **kwargs):
        """Check if a collection exists in Chroma"""
        self.ensure_one()

        client = self._get_chroma_client()

        # Get collection from Odoo to retrieve the name
        collection = self.env["llm.knowledge.collection"].browse(collection_id)
        if not collection.exists():
            return False

        collection_name = self.get_santized_collection_name(collection_id)

        # Check if collection exists in Chroma
        collections = client.list_collections()
        return any(c.name == collection_name for c in collections)

    def chroma_create_collection(
        self, collection_id, dimension=None, metadata=None, **kwargs
    ):
        """Create a collection in Chroma"""
        self.ensure_one()

        client = self._get_chroma_client()
        if not client:
            raise UserError(_("Failed to connect to Chroma server"))

        collection = self.env["llm.knowledge.collection"].browse(collection_id)
        if not collection.exists():
            raise UserError(
                _(
                    "The knowledge collection could not be found. "
                    "It may have been deleted or you may not have access to it."
                )
            )

        # Check if collection already exists in Chroma
        if self.chroma_collection_exists(collection_id):
            _logger.info(f"Collection {collection_id} already exists in Chroma")
            return True

        # Create collection in Chroma
        metadata = {
            "source": "odoo",
            "collection_id": str(collection_id),
            "description": collection.description or "",
        }
        # Use the default embedding function
        try:
            collection_name = self.get_santized_collection_name(collection_id)
            _logger.info(f"Creating collection {collection_name} in Chroma")
            client.create_collection(name=collection_name, metadata=metadata)

            return True
        except Exception as err:
            _logger.error("Could not create collection %s: %s", collection_name, err)
            raise UserError(
                _("Could not create collection %s: %s") % (collection_name, err)
            ) from err

    def chroma_delete_collection(self, collection_id, **kwargs):
        """Delete a collection from Chroma"""
        self.ensure_one()

        client = self._get_chroma_client()
        if not client:
            return False

        try:
            # Check if collection exists in Chroma
            if not self.chroma_collection_exists(collection_id):
                _logger.info(f"Collection {collection_id} does not exist in Chroma")
                return True  # Nothing to delete

            # Delete collection in Chroma
            collection_name = self.get_santized_collection_name(collection_id)
            client.delete_collection(name=collection_name)
            _logger.info(f"Deleted collection {collection_name} from Chroma")
            return True
        except Exception as err:
            _logger.error(f"Error deleting collection: {str(err)}")
            return False

    def chroma_list_collections(self, **kwargs):
        """List all collections in Chroma"""
        self.ensure_one()

        client = self._get_chroma_client()
        if not client:
            return []

        try:
            # Get collections from Chroma
            collections = client.list_collections()
            return [c.name for c in collections]
        except Exception as e:
            _logger.error(f"Error listing collections: {str(e)}")
            return []

    # -------------------------------------------------------------------------
    # Vector Management
    # -------------------------------------------------------------------------

    def _get_chroma_collection(self, collection_id):
        """Get a Chroma collection by ID or name"""
        self.ensure_one()

        client = self._get_chroma_client()
        if not client:
            return None

        collection_name = self.get_santized_collection_name(collection_id)

        try:
            # Get collection from Chroma
            return client.get_collection(name=collection_name)
        except Exception as e:
            _logger.error(f"Error getting collection {collection_name}: {str(e)}")
            return None

    def chroma_insert_vectors(
        self, collection_id, vectors, metadata=None, ids=None, **kwargs
    ):
        """Insert vectors into a Chroma collection"""
        self.ensure_one()

        collection = self._get_chroma_collection(collection_id)
        if not collection:
            return False

        if not ids or len(ids) != len(vectors):
            raise UserError(_("Must provide IDs matching the vectors"))

        # Convert IDs to strings (Chroma requirement)
        string_ids = [str(id) for id in ids]

        # Handle metadata
        if metadata is None:
            metadatas = [{} for _ in range(len(vectors))]
        else:
            # Ensure metadata is serializable
            metadatas = []
            for meta in metadata:
                clean_meta = {}
                for key, value in meta.items():
                    if isinstance(value, (str, int, float, bool)) or value is None:
                        clean_meta[key] = value
                    else:
                        clean_meta[key] = str(value)
                metadatas.append(clean_meta)

        # Add vectors to collection
        collection.add(embeddings=vectors, metadatas=metadatas, ids=string_ids)

    def chroma_delete_vectors(self, collection_id, ids, **kwargs):
        """Delete vectors from a Chroma collection"""
        self.ensure_one()

        collection = self._get_chroma_collection(collection_id)
        if not collection:
            return False

        if ids is None:
            return False

        try:
            # Convert IDs to strings if needed
            string_ids = [str(id) for id in ids]

            # Delete vectors from collection
            collection.delete(ids=string_ids)
            return True
        except Exception as e:
            _logger.error(f"Error deleting vectors: {str(e)}")
            return False

    def chroma_search_vectors(
        self,
        collection_id,
        query_vector,
        limit=10,
        filter=None,
        min_similarity=0.5,
        **kwargs,
    ):
        """Search for similar vectors in a Chroma collection"""
        self.ensure_one()
        collection = self._get_chroma_collection(collection_id)
        if not collection:
            return []

        try:
            # Convert filter to Chroma format if needed
            chroma_filter = (
                self._convert_odoo_filter_to_chroma(filter) if filter else None
            )

            # Query collection
            results = collection.query(
                query_embeddings=[query_vector],
                n_results=limit,
                where=chroma_filter,
                include=["metadatas", "distances"],
            )

            # Format results to match expected output
            formatted_results = []

            if not results or not results["ids"] or not results["ids"][0]:
                return []

            # Process results
            for i, id_val in enumerate(results["ids"][0]):
                distance = (
                    float(results["distances"][0][i])
                    if "distances" in results and results["distances"][0]
                    else float("inf")
                )
                # Convert L2 distance to similarity score [0, 1] (1 = closest)
                score = 1.0 / (1.0 + distance) if distance != float("inf") else 0.0
                if score < min_similarity:
                    continue
                formatted_results.append(
                    {
                        "id": int(id_val),  # Convert string ID to integer
                        "score": score,
                        "metadata": results["metadatas"][0][i]
                        if "metadatas" in results and results["metadatas"][0]
                        else {},
                    }
                )

            return formatted_results
        except Exception as e:
            _logger.error(f"Error searching vectors: {str(e)}")
            return []

    def _convert_odoo_filter_to_chroma(self, odoo_filter):
        """Convert Odoo filter format to Chroma filter format"""
        # Simple conversion - this can be expanded based on needs
        if not odoo_filter:
            return None

        # Chroma filters are generally key-value pairs
        chroma_filter = {}

        # Handle basic operators
        if "$and" in odoo_filter:
            # Convert AND conditions
            for condition in odoo_filter["$and"]:
                for key, value in condition.items():
                    chroma_filter[key] = value
        elif "$or" in odoo_filter:
            # Chroma doesn't directly support OR, so log a warning
            _logger.warning("OR conditions in filters not directly supported by Chroma")
            return None
        else:
            # Direct mapping for simple filters
            chroma_filter = odoo_filter

        return chroma_filter

    # -------------------------------------------------------------------------
    # Index Management
    # -------------------------------------------------------------------------

    def chroma_create_index(self, collection_id, index_type=None, **kwargs):
        """Create an index on a Chroma collection"""
        # Chroma manages its own indices, so this is a no-op
        _logger.info(
            "Chroma manages its own indices, no explicit index creation needed"
        )
        return True
