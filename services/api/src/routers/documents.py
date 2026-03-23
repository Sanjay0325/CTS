"""Documents and RAG collections router - collections, upload, chunk, search."""

from fastapi import APIRouter, Depends, HTTPException

from src.auth import get_current_user
from src.core.deps import get_document_service
from src.models import DocumentCollectionCreate, DocumentUpload
from src.services.document_service_supabase import DocumentServiceSupabase

router = APIRouter()


@router.get("/collections")
async def list_collections(
    user: dict = Depends(get_current_user),
    svc: DocumentServiceSupabase = Depends(get_document_service),
):
    """List user's document collections (external DBs for RAG)."""
    return svc.list_collections(user["id"])


@router.post("/collections")
async def create_collection(
    data: DocumentCollectionCreate,
    user: dict = Depends(get_current_user),
    svc: DocumentServiceSupabase = Depends(get_document_service),
):
    """Create a document collection."""
    return svc.create_collection(user["id"], data.name, data.description)


@router.delete("/collections/{collection_id}")
async def delete_collection(
    collection_id: str,
    user: dict = Depends(get_current_user),
    svc: DocumentServiceSupabase = Depends(get_document_service),
):
    """Delete a collection."""
    ok = svc.delete_collection(collection_id, user["id"])
    if not ok:
        raise HTTPException(status_code=404, detail="Collection not found")
    return {"ok": True}


@router.get("/documents")
async def list_documents(
    collection_id: str | None = None,
    user: dict = Depends(get_current_user),
    svc: DocumentServiceSupabase = Depends(get_document_service),
):
    """List documents, optionally by collection."""
    return svc.list_documents(user["id"], collection_id)


@router.post("/documents")
async def upload_document(
    data: DocumentUpload,
    user: dict = Depends(get_current_user),
    svc: DocumentServiceSupabase = Depends(get_document_service),
):
    """Upload a document for RAG. Chunks are created automatically."""
    return svc.create_document(
        user["id"], data.name, data.content, data.collection_id
    )


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    user: dict = Depends(get_current_user),
    svc: DocumentServiceSupabase = Depends(get_document_service),
):
    """Delete a document."""
    ok = svc.delete_document(document_id, user["id"])
    if not ok:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"ok": True}
