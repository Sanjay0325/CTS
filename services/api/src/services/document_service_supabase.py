"""Document and RAG service using Supabase REST and vector search."""

from uuid import UUID, uuid4

from src.config import get_embedding_api_key
from src.services.document_service import chunk_text, get_embeddings_sync


class DocumentServiceSupabase:
    """Document upload, collections, and RAG search via Supabase."""

    def __init__(self, supabase_client):
        self.sb = supabase_client

    def list_collections(self, user_id: str) -> list[dict]:
        """List user's document collections (external DBs)."""
        r = (
            self.sb.table("document_collections")
            .select("id, name, description, created_at")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )
        return [dict(x) for x in (r.data or [])]

    def create_collection(self, user_id: str, name: str, description: str = "") -> dict:
        """Create a document collection."""
        r = self.sb.table("document_collections").insert({
            "user_id": user_id,
            "name": name,
            "description": description or "",
        }).execute()
        if not r.data or len(r.data) == 0:
            raise ValueError("Failed to create collection")
        return dict(r.data[0])

    def delete_collection(self, collection_id: str, user_id: str) -> bool:
        """Delete a collection."""
        r = (
            self.sb.table("document_collections")
            .delete()
            .eq("id", collection_id)
            .eq("user_id", user_id)
            .execute()
        )
        return bool(r.data and len(r.data) > 0)

    def list_documents(self, user_id: str, collection_id: str | None = None) -> list[dict]:
        """List documents, optionally filtered by collection."""
        q = self.sb.table("documents").select("id, name, collection_id, created_at").eq("user_id", user_id)
        if collection_id:
            q = q.eq("collection_id", collection_id)
        r = q.order("created_at", desc=True).execute()
        return [dict(x) for x in (r.data or [])]

    def create_document(
        self, user_id: str, name: str, content: str, collection_id: str | None = None
    ) -> dict:
        """Create document and chunks. Embeds chunks when OPENAI_API_KEY/EMBEDDING_API_KEY is set."""
        doc_id = str(uuid4())
        self.sb.table("documents").insert({
            "id": doc_id,
            "user_id": user_id,
            "collection_id": collection_id,
            "name": name,
            "content": content,
        }).execute()

        chunks = chunk_text(content)
        api_key = get_embedding_api_key()
        embeddings = get_embeddings_sync(chunks, api_key) if api_key and chunks else []

        for i, chunk in enumerate(chunks):
            row = {
                "document_id": doc_id,
                "user_id": user_id,
                "chunk_index": i,
                "content": chunk,
            }
            if i < len(embeddings) and embeddings[i]:
                row["embedding"] = embeddings[i]  # pgvector accepts JSON array
            self.sb.table("document_chunks").insert(row).execute()
        return {"id": doc_id, "name": name, "chunks": len(chunks), "embedded": len(embeddings)}

    def delete_document(self, document_id: str, user_id: str) -> bool:
        """Delete document (chunks cascade)."""
        r = (
            self.sb.table("documents")
            .delete()
            .eq("id", document_id)
            .eq("user_id", user_id)
            .execute()
        )
        return bool(r.data and len(r.data) > 0)

    def search_collections(
        self, user_id: str, collection_ids: list[str], query: str, limit: int = 5
    ) -> list[dict]:
        """Search document chunks. Uses vector similarity when embeddings exist, else text search."""
        if not collection_ids or not query or not query.strip():
            return []

        api_key = get_embedding_api_key()
        if api_key:
            try:
                query_embedding = get_embeddings_sync([query.strip()], api_key)
                if query_embedding and query_embedding[0]:
                    emb = query_embedding[0]
                    coll_uuids = [str(cid) for cid in collection_ids]
                    r = self.sb.rpc(
                        "match_document_chunks",
                        {
                            "query_embedding": emb,
                            "filter_collection_ids": coll_uuids,
                            "filter_user_id": str(user_id),
                            "match_count": limit,
                            "match_threshold": 0.3,
                        },
                    ).execute()
                    if r.data and len(r.data) > 0:
                        return [
                            {
                                "content": row.get("content", "")[:500],
                                "document_id": row.get("document_id"),
                                "chunk_id": row.get("id"),
                            }
                            for row in r.data
                        ]
            except Exception:
                pass  # Fall back to text search

        # Text-based fallback
        results = []
        for cid in collection_ids:
            docs_r = (
                self.sb.table("documents")
                .select("id")
                .eq("user_id", user_id)
                .eq("collection_id", cid)
                .execute()
            )
            doc_ids = [d["id"] for d in (docs_r.data or [])]
            if not doc_ids:
                continue

            for did in doc_ids[:20]:
                chunks_r = (
                    self.sb.table("document_chunks")
                    .select("id, content, document_id")
                    .eq("document_id", did)
                    .eq("user_id", user_id)
                    .limit(20)
                    .execute()
                )
                for ch in (chunks_r.data or []):
                    content = ch.get("content", "")
                    if query.lower() in content.lower():
                        results.append({
                            "content": content[:500],
                            "document_id": ch.get("document_id"),
                            "chunk_id": ch.get("id"),
                        })
                    elif any(w in content.lower() for w in query.lower().split() if len(w) > 2):
                        results.append({
                            "content": content[:500],
                            "document_id": ch.get("document_id"),
                            "chunk_id": ch.get("id"),
                        })
                if len(results) >= limit:
                    break
            if len(results) >= limit:
                break

        return results[:limit]

    def get_collection_names(self, user_id: str, collection_ids: list[str]) -> list[str]:
        """Get names of collections by ids (batch query)."""
        if not collection_ids:
            return []
        r = (
            self.sb.table("document_collections")
            .select("name")
            .eq("user_id", user_id)
            .in_("id", collection_ids)
            .execute()
        )
        return [row["name"] for row in (r.data or []) if row.get("name")]

