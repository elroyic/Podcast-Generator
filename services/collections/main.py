"""
Collections Service - Manages collections of feeds, reviews, and content.
Collections belong to Podcast Groups and contain feeds, reviewer output, presenter output, and writer output.
"""
import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from shared.database import get_db, create_tables
from shared.models import PodcastGroup, Article, NewsFeed

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Collections Service", version="1.0.0")


class CollectionItem(BaseModel):
    """Individual item in a collection."""
    item_id: str
    item_type: str  # "feed", "review", "brief", "script", "feedback"
    content: Dict[str, Any]
    created_at: datetime
    metadata: Dict[str, Any]


class Collection(BaseModel):
    """Collection of content for podcast generation."""
    collection_id: str
    group_id: UUID
    name: str
    description: Optional[str] = None
    status: str = "building"  # building, ready, processing, completed
    items: List[CollectionItem] = []
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any] = {}


class CollectionCreate(BaseModel):
    """Request to create a new collection."""
    group_id: UUID
    name: str
    description: Optional[str] = None


class CollectionUpdate(BaseModel):
    """Request to update a collection."""
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class AddItemRequest(BaseModel):
    """Request to add an item to a collection."""
    collection_id: str
    item_type: str
    content: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None


class CollectionManager:
    """Handles collection management logic."""
    
    def __init__(self):
        # In-memory storage for collections (in production, use database)
        self.collections: Dict[str, Collection] = {}
    
    def create_collection(self, request: CollectionCreate) -> Collection:
        """Create a new collection."""
        collection_id = str(uuid4())
        
        collection = Collection(
            collection_id=collection_id,
            group_id=request.group_id,
            name=request.name,
            description=request.description,
            status="building",
            items=[],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            metadata={}
        )
        
        self.collections[collection_id] = collection
        logger.info(f"Created collection {collection_id} for group {request.group_id}")
        
        return collection
    
    def get_collection(self, collection_id: str) -> Optional[Collection]:
        """Get a collection by ID."""
        return self.collections.get(collection_id)
    
    def update_collection(self, collection_id: str, request: CollectionUpdate) -> Optional[Collection]:
        """Update a collection."""
        collection = self.collections.get(collection_id)
        if not collection:
            return None
        
        if request.name is not None:
            collection.name = request.name
        if request.description is not None:
            collection.description = request.description
        if request.status is not None:
            collection.status = request.status
        
        collection.updated_at = datetime.utcnow()
        
        logger.info(f"Updated collection {collection_id}")
        return collection
    
    def add_item_to_collection(self, request: AddItemRequest) -> Optional[Collection]:
        """Add an item to a collection."""
        collection = self.collections.get(request.collection_id)
        if not collection:
            return None
        
        item = CollectionItem(
            item_id=str(uuid4()),
            item_type=request.item_type,
            content=request.content,
            created_at=datetime.utcnow(),
            metadata=request.metadata or {}
        )
        
        collection.items.append(item)
        collection.updated_at = datetime.utcnow()
        
        # Update collection status based on content
        self._update_collection_status(collection)
        
        logger.info(f"Added {request.item_type} item to collection {request.collection_id}")
        return collection
    
    def _update_collection_status(self, collection: Collection):
        """Update collection status based on its contents."""
        item_types = [item.item_type for item in collection.items]
        
        # Check if collection has minimum required items (3 feeds + summaries as per workflow)
        feed_count = item_types.count("feed")
        review_count = item_types.count("review")
        
        if feed_count >= 3 and review_count >= 3:
            collection.status = "ready"
        elif feed_count > 0 or review_count > 0:
            collection.status = "building"
        else:
            collection.status = "empty"
    
    def get_collections_by_group(self, group_id: UUID) -> List[Collection]:
        """Get all collections for a podcast group."""
        return [
            collection for collection in self.collections.values()
            if collection.group_id == group_id
        ]
    
    def get_ready_collections(self) -> List[Collection]:
        """Get all collections that are ready for processing."""
        return [
            collection for collection in self.collections.values()
            if collection.status == "ready"
        ]
    
    def delete_collection(self, collection_id: str) -> bool:
        """Delete a collection."""
        if collection_id in self.collections:
            del self.collections[collection_id]
            logger.info(f"Deleted collection {collection_id}")
            return True
        return False


# Initialize services
collection_manager = CollectionManager()

# Create tables on startup
@app.on_event("startup")
async def startup_event():
    create_tables()
    logger.info("Collections Service started")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "collections", "timestamp": datetime.utcnow()}


@app.post("/collections", response_model=Collection)
async def create_collection(
    request: CollectionCreate,
    db: Session = Depends(get_db)
):
    """Create a new collection."""
    
    # Verify podcast group exists
    group = db.query(PodcastGroup).filter(PodcastGroup.id == request.group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Podcast group not found")
    
    try:
        collection = collection_manager.create_collection(request)
        return collection
        
    except Exception as e:
        logger.error(f"Error creating collection: {e}")
        raise HTTPException(status_code=500, detail=f"Collection creation failed: {str(e)}")


@app.get("/collections/{collection_id}", response_model=Collection)
async def get_collection(collection_id: str):
    """Get a specific collection."""
    collection = collection_manager.get_collection(collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    return collection


@app.put("/collections/{collection_id}", response_model=Collection)
async def update_collection(
    collection_id: str,
    request: CollectionUpdate
):
    """Update a collection."""
    collection = collection_manager.update_collection(collection_id, request)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    return collection


@app.delete("/collections/{collection_id}")
async def delete_collection(collection_id: str):
    """Delete a collection."""
    success = collection_manager.delete_collection(collection_id)
    if not success:
        raise HTTPException(status_code=404, detail="Collection not found")
    return {"message": "Collection deleted successfully"}


@app.post("/collections/{collection_id}/items", response_model=Collection)
async def add_item_to_collection(
    collection_id: str,
    request: AddItemRequest
):
    """Add an item to a collection."""
    request.collection_id = collection_id  # Ensure consistency
    collection = collection_manager.add_item_to_collection(request)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    return collection


@app.get("/collections/group/{group_id}", response_model=List[Collection])
async def get_collections_by_group(group_id: UUID):
    """Get all collections for a podcast group."""
    collections = collection_manager.get_collections_by_group(group_id)
    return collections


@app.get("/collections/ready", response_model=List[Collection])
async def get_ready_collections():
    """Get all collections that are ready for processing."""
    collections = collection_manager.get_ready_collections()
    return collections


@app.get("/collections", response_model=List[Collection])
async def list_all_collections():
    """List all collections."""
    return list(collection_manager.collections.values())


@app.post("/test-collection-creation")
async def test_collection_creation(
    group_name: str = "Test Podcast Group",
    collection_name: str = "Test Collection",
    db: Session = Depends(get_db)
):
    """Test endpoint for collection creation."""
    
    try:
        # Create a test podcast group
        test_group = PodcastGroup(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            name=group_name,
            description="Test podcast group for collection testing",
            category="Technology",
            language="en",
            country="US"
        )
        
        # Create test collection
        collection_request = CollectionCreate(
            group_id=test_group.id,
            name=collection_name,
            description="Test collection for demonstration"
        )
        
        collection = collection_manager.create_collection(collection_request)
        
        # Add some test items
        test_items = [
            {
                "item_type": "feed",
                "content": {
                    "title": "Test Article 1",
                    "summary": "This is a test article about technology",
                    "source": "Test Source"
                }
            },
            {
                "item_type": "review",
                "content": {
                    "topic": "Technology",
                    "subject": "AI/ML",
                    "tags": ["technology", "ai", "innovation"],
                    "importance_rank": 8
                }
            },
            {
                "item_type": "brief",
                "content": {
                    "presenter_name": "Test Presenter",
                    "brief": "This is a test brief from a presenter"
                }
            }
        ]
        
        for item_data in test_items:
            add_request = AddItemRequest(
                collection_id=collection.collection_id,
                item_type=item_data["item_type"],
                content=item_data["content"]
            )
            collection = collection_manager.add_item_to_collection(add_request)
        
        return {
            "test_group": {
                "id": str(test_group.id),
                "name": test_group.name,
                "description": test_group.description
            },
            "created_collection": collection.dict(),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in test collection creation: {e}")
        raise HTTPException(status_code=500, detail=f"Test collection creation failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8011)