import logging

from qdrant_client import QdrantClient
from qdrant_client import models as qdrant_models
from qdrant_client.http.exceptions import UnexpectedResponse

from odoo import _, api, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class LLMStoreQdrant(models.Model):
    _inherit = "llm.store"
    _description = "Qdrant Vector Store Implementation"

    @api.model
    def _get_available_services(self):
        services = super()._get_available_services()
        services.append(("qdrant", "Qdrant"))
        return services

    # -------------------------------------------------------------------------
    # Qdrant Client Management
    # -------------------------------------------------------------------------

    def qdrant_sanitize_collection_name(self, name):
        """Sanitize a collection name for Qdrant."""
        return self._default_sanitize_collection_name(name)

    def _get_qdrant_client(self):
        """Get a Qdrant client for the current store configuration."""
        self.ensure_one()
        if self.service != "qdrant":
            return None

        kwargs = {}
        if self.connection_uri:
            kwargs["url"] = self.connection_uri
        else:
            kwargs["host"] = "localhost"
            kwargs["port"] = 6333

        if self.api_key:
            kwargs["api_key"] = self.api_key

        try:
            client = QdrantClient(**kwargs)
            return client
        except Exception as err:
            _logger.error(
                "Failed to connect to Qdrant server at %s: %s",
                kwargs.get("url") or kwargs.get("host"),
                err,
            )
            raise UserError(
                _(
                    "Could not connect to the Qdrant vector database server.\n\n"
                    "Please check:\n"
                    "• The server is running at the configured address\n"
                    "• The API key (if required) is correct\n"
                    "• Network/firewall allows the connection\n\n"
                    "Technical details: %s"
                )
                % str(err)
            ) from err

    # -------------------------------------------------------------------------
    # Collection Management
    # -------------------------------------------------------------------------

    def qdrant_collection_exists(self, collection_id, **kwargs):
        """Check if a collection exists in Qdrant."""
        self.ensure_one()
        client = self._get_qdrant_client()
        if not client:
            return False

        qdrant_collection_name = self.get_santized_collection_name(collection_id)

        return client.collection_exists(collection_name=qdrant_collection_name)

    def qdrant_create_collection(
        self, collection_id, dimension=None, metadata=None, **kwargs
    ):
        """Create a collection in Qdrant."""
        self.ensure_one()
        client = self._get_qdrant_client()
        if not client:
            raise UserError(_("Failed to connect to Qdrant server"))

        collection_record = self.env["llm.knowledge.collection"].browse(collection_id)
        if not dimension and collection_record.embedding_model_id:
            embedding_model = self.env["llm.model"].browse(
                collection_record.embedding_model_id.id
            )
            if embedding_model.exists():
                # Generate a sample embedding to determine dimensions
                sample_embedding = embedding_model.embedding("")[0]
                dimension = len(sample_embedding) if sample_embedding else None
        qdrant_collection_name = self.get_santized_collection_name(collection_id)

        if self.qdrant_collection_exists(collection_id):
            # TODO: could check dimension mismatch here if needed
            return True

        try:
            vector_params = qdrant_models.VectorParams(
                size=dimension, distance=qdrant_models.Distance.COSINE
            )
            client.create_collection(
                collection_name=qdrant_collection_name,
                vectors_config=vector_params,
            )
            return True
        except UnexpectedResponse as err:
            _logger.exception(
                f"Could not create collection {qdrant_collection_name}: {err.status_code} - {err.content.decode()}"
            )
            return False

    def qdrant_delete_collection(self, collection_id, **kwargs):
        """Delete a collection from Qdrant."""
        self.ensure_one()
        client = self._get_qdrant_client()
        if not client:
            raise UserError(_("Failed to connect to Qdrant server"))

        qdrant_collection_name = self.get_santized_collection_name(collection_id)

        if not self.qdrant_collection_exists(collection_id):
            return True

        result = client.delete_collection(
            collection_name=qdrant_collection_name, timeout=30
        )
        if result is not True:
            _logger.warning(
                f"Qdrant delete_collection for {qdrant_collection_name} returned {result}. Assuming success if no exception."
            )
        return True

    def qdrant_list_collections(self, **kwargs):
        """List all collections managed by this Qdrant instance."""
        self.ensure_one()
        client = self._get_qdrant_client()
        if not client:
            return []

        collections_response = client.get_collections()
        return [c.name for c in collections_response.collections]

    # -------------------------------------------------------------------------
    # Vector Management
    # -------------------------------------------------------------------------

    def qdrant_insert_vectors(
        self, collection_id, vectors, metadata=None, ids=None, **kwargs
    ):
        """Insert or update vectors in a Qdrant collection."""
        self.ensure_one()
        client = self._get_qdrant_client()
        if not client:
            raise UserError(_("Failed to connect to Qdrant server"))

        qdrant_collection_name = self.get_santized_collection_name(collection_id)

        if not ids or len(ids) != len(vectors):
            raise UserError(
                _("Must provide unique IDs matching the number of vectors.")
            )

        points = []
        for i, vec_id in enumerate(ids):
            point_id = int(vec_id)
            if point_id < 0:
                raise UserError(
                    _(
                        "Qdrant vector IDs must be non-negative integers or UUIDs. Received: %s"
                    )
                    % vec_id
                )

            payload = metadata[i] if metadata and i < len(metadata) else {}
            clean_payload = self._sanitize_payload(payload)

            points.append(
                qdrant_models.PointStruct(
                    id=point_id, vector=vectors[i], payload=clean_payload
                )
            )

        response = client.upsert(
            collection_name=qdrant_collection_name, points=points, wait=True
        )
        if response.status != qdrant_models.UpdateStatus.COMPLETED:
            _logger.warning(
                f"Qdrant upsert status for collection {qdrant_collection_name}: {response.status}"
            )
        return ids

    def _sanitize_payload(self, payload):
        """Ensure payload dictionary is JSON serializable for Qdrant."""
        if not isinstance(payload, dict):
            return {}
        clean_payload = {}
        for k, v in payload.items():
            if isinstance(v, (str, int, float, bool, list)) or v is None:
                if isinstance(v, list):
                    if all(
                        isinstance(item, (str, int, float, bool)) or item is None
                        for item in v
                    ):
                        clean_payload[k] = v
                    else:
                        clean_payload[k] = str(
                            v
                        )  # Convert list with complex items to string
                else:
                    clean_payload[k] = v
            else:
                clean_payload[k] = str(v)
        return clean_payload

    def qdrant_delete_vectors(self, collection_id, ids, **kwargs):
        """Delete vectors from a Qdrant collection."""
        self.ensure_one()
        client = self._get_qdrant_client()
        if not client:
            return False

        if not ids:
            return False

        qdrant_collection_name = self.get_santized_collection_name(collection_id)

        point_ids = [int(vid) for vid in ids if str(vid).isdigit() and int(vid) >= 0]
        if len(point_ids) != len(ids):
            _logger.warning(
                "Some provided IDs for deletion were invalid (non-integer or negative), skipping them."
            )
        if not point_ids:
            return False

        response = client.delete(
            collection_name=qdrant_collection_name,
            points_selector=qdrant_models.PointIdsList(points=point_ids),
            wait=True,
        )
        if response.status != qdrant_models.UpdateStatus.COMPLETED:
            _logger.warning(
                f"Qdrant delete status for collection {qdrant_collection_name}: {response.status}"
            )
            return False
        else:
            return True

    def qdrant_search_vectors(
        self,
        collection_id,
        query_vector,
        limit=10,
        filter=None,
        min_similarity=0.5,
        **kwargs,
    ):
        """Search for similar vectors in a Qdrant collection."""
        self.ensure_one()
        client = self._get_qdrant_client()
        if not client:
            return []

        qdrant_collection_name = self.get_santized_collection_name(collection_id)
        qdrant_filter = self._convert_odoo_filter_to_qdrant(filter) if filter else None
        score_threshold = min_similarity

        search_result = client.query_points(
            collection_name=qdrant_collection_name,
            query=query_vector,
            query_filter=qdrant_filter,
            limit=limit,
            score_threshold=score_threshold,
            with_payload=True,
            with_vectors=False,
        )

        formatted_results = []
        for hit in search_result.points:
            formatted_results.append(
                {
                    "id": hit.id,
                    "score": hit.score,
                    "metadata": hit.payload if hit.payload else {},
                }
            )
        return formatted_results

    # TODO: not used right now, need testing
    def _convert_odoo_filter_to_qdrant(self, odoo_filter):
        """Convert Odoo-like filter format to Qdrant filter format (basic implementation)."""
        if not odoo_filter or not isinstance(odoo_filter, dict):
            return None

        must_conditions = []
        must_not_conditions = []

        for key, value in odoo_filter.items():
            if key == "$and" and isinstance(value, list):
                for condition in value:
                    sub_filter = self._convert_odoo_filter_to_qdrant(condition)
                    if sub_filter:
                        if sub_filter.must:
                            must_conditions.extend(sub_filter.must)
                        if sub_filter.must_not:
                            must_not_conditions.extend(sub_filter.must_not)
            elif key == "$or" and isinstance(value, list):
                _logger.warning(
                    "'$or' operator in filters is not fully supported yet for Qdrant."
                )
            elif isinstance(value, dict):
                field_key = f"payload.{key}"
                for op, op_val in value.items():
                    if op == "$eq":
                        must_conditions.append(
                            qdrant_models.FieldCondition(
                                key=field_key,
                                match=qdrant_models.MatchValue(value=op_val),
                            )
                        )
                    elif op == "$ne":
                        must_not_conditions.append(
                            qdrant_models.FieldCondition(
                                key=field_key,
                                match=qdrant_models.MatchValue(value=op_val),
                            )
                        )
                    elif op == "$gt":
                        must_conditions.append(
                            qdrant_models.FieldCondition(
                                key=field_key, range=qdrant_models.Range(gt=op_val)
                            )
                        )
                    elif op == "$gte":
                        must_conditions.append(
                            qdrant_models.FieldCondition(
                                key=field_key, range=qdrant_models.Range(gte=op_val)
                            )
                        )
                    elif op == "$lt":
                        must_conditions.append(
                            qdrant_models.FieldCondition(
                                key=field_key, range=qdrant_models.Range(lt=op_val)
                            )
                        )
                    elif op == "$lte":
                        must_conditions.append(
                            qdrant_models.FieldCondition(
                                key=field_key, range=qdrant_models.Range(lte=op_val)
                            )
                        )
                    elif op == "$in" and isinstance(op_val, list):
                        must_conditions.append(
                            qdrant_models.FieldCondition(
                                key=field_key, match=qdrant_models.MatchAny(any=op_val)
                            )
                        )
                    elif op == "$nin" and isinstance(op_val, list):
                        must_not_conditions.append(
                            qdrant_models.FieldCondition(
                                key=field_key, match=qdrant_models.MatchAny(any=op_val)
                            )
                        )
                    else:
                        _logger.warning(
                            f"Unsupported filter operator '{op}' for key '{key}'"
                        )
            elif isinstance(value, (str, int, float, bool)):
                field_key = f"payload.{key}"
                must_conditions.append(
                    qdrant_models.FieldCondition(
                        key=field_key, match=qdrant_models.MatchValue(value=value)
                    )
                )
            else:
                _logger.warning(
                    f"Unsupported filter value type for key '{key}': {type(value)}"
                )

        if not must_conditions and not must_not_conditions:
            return None

        return qdrant_models.Filter(
            must=must_conditions if must_conditions else None,
            must_not=must_not_conditions if must_not_conditions else None,
        )

    # -------------------------------------------------------------------------
    # Index Management (Payload Indexing)
    # -------------------------------------------------------------------------
    # TODO: qdrant does not have automatic indexing, if needed in future, we could use this
    # to apply indexing on specific fields
    def qdrant_create_index(self, collection_id, index_type=None, **kwargs):
        """Create a payload index on a specific field in a Qdrant collection."""
        self.ensure_one()
        client = self._get_qdrant_client()
        if not client:
            raise UserError(_("Failed to connect to Qdrant server"))

        qdrant_collection_name = self.get_santized_collection_name(collection_id)

        field_name = kwargs.get("field_name")
        field_schema = kwargs.get("field_schema")

        if not field_name or not field_schema:
            return True

        schema_map = {
            "keyword": qdrant_models.PayloadSchemaType.KEYWORD,
            "integer": qdrant_models.PayloadSchemaType.INTEGER,
            "float": qdrant_models.PayloadSchemaType.FLOAT,
            "geo": qdrant_models.PayloadSchemaType.GEO,
            "text": qdrant_models.PayloadSchemaType.TEXT,
        }
        qdrant_schema_type = schema_map.get(field_schema.lower())

        if not qdrant_schema_type:
            raise UserError(
                _("Unsupported field_schema '%s'. Must be one of: %s")
                % (field_schema, list(schema_map.keys()))
            )

        try:
            response = client.create_payload_index(
                collection_name=qdrant_collection_name,
                field_name=field_name,
                field_schema=qdrant_schema_type,
                wait=True,
            )
            if response.status != qdrant_models.UpdateStatus.COMPLETED:
                _logger.warning(
                    f"Qdrant create_payload_index status for {qdrant_collection_name}.{field_name}: {response.status}"
                )
                return False
            return True
        except UnexpectedResponse as err:
            _logger.error(
                f"Error creating payload index on {qdrant_collection_name}.{field_name}: {err.status_code} - {err.content.decode()}"
            )
            if "already exists" in err.content.decode().lower():
                return True  # Index already exists is not a failure
            return False
