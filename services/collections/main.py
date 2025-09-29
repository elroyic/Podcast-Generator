"""
Collections Service - Manages feed grouping, review aggregation, and collection readiness.
Handles the workflow from individual feeds to complete collections ready for podcast generation.
"""
import logging
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from uuid import UUID, uuid4

import httpx
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from shared.database import get_db, get_db_session, create_tables
from shared.models import Article, NewsFeed, PodcastGroup, Collection as DBCollection

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Collections Service", version="1.0.0")

# Configuration
REVIEWER_URL = os.getenv("REVIEWER_URL", "http://reviewer:8007")
MIN_FEEDS_PER_COLLECTION = int(os.getenv("MIN_FEEDS_PER_COLLECTION", "3"))
COLLECTION_TTL_HOURS = int(os.getenv("COLLECTION_TTL_HOURS", "24"))


class CollectionItem(BaseModel):
    """An item within a collection."""
    item_id: str
    item_type: str  # "feed", "review", "brief", "script"
    content: Dict[str, Any]
    created_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CollectionDTO(BaseModel):
    """A collection of related content."""
    collection_id: str
    name: str
    description: Optional[str] = None
    group_ids: List[str] = Field(default_factory=list)  # Podcast groups assigned to this collection
    status: str  # "building", "ready", "used", "expired"
    items: List[CollectionItem]
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime] = None


class CollectionCreate(BaseModel):
    """Request to create a new collection."""
    name: str
    description: Optional[str] = None
    group_ids: List[str] = Field(default_factory=list)  # Optional podcast groups to assign
    priority_tags: List[str] = Field(default_factory=list)
    max_items: int = 10


class CollectionUpdate(BaseModel):
    """Request to update a collection."""
    status: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class CollectionResponse(BaseModel):
    """Response for collection operations."""
    collection: CollectionDTO
    message: str


class CollectionsManager:
    """Manages collections and their lifecycle."""
    
    def __init__(self):
        self.reviewer_client = httpx.AsyncClient(timeout=30.0)
        # In-memory store for active collections
        self.collections: Dict[str, CollectionDTO] = {}
        # Load existing collections from database on startup
        self._load_collections_from_db()
    
    def _load_collections_from_db(self):
        """Load existing collections from database on startup."""
        try:
            db = get_db_session()
            try:
                db_collections = db.query(DBCollection).all()
                for db_collection in db_collections:
                    # Get articles for this collection
                    articles = db.query(Article).filter(Article.collection_id == db_collection.id).all()
                    
                    # Create collection items from articles
                    items = []
                    for article in articles:
                        feed_item = CollectionItem(
                            item_id=str(article.id),
                            item_type="feed",
                            content={
                                "title": article.title,
                                "link": article.link,
                                "summary": article.summary,
                                "content": article.content,
                                "publish_date": article.publish_date.isoformat() if article.publish_date else None,
                                "source": article.news_feed.name if article.news_feed else "Unknown"
                            },
                            created_at=article.created_at,
                            metadata={
                                "article_id": str(article.id),
                                "feed_id": str(article.feed_id)
                            }
                        )
                        items.append(feed_item)
                    
                    # Create CollectionDTO
                    collection = CollectionDTO(
                        collection_id=str(db_collection.id),
                        name=db_collection.name,
                        description=db_collection.description,
                        group_ids=[str(group.id) for group in db_collection.podcast_groups],
                        status=db_collection.status,
                        items=items,
                        metadata={
                            "min_feeds_required": MIN_FEEDS_PER_COLLECTION,
                            "loaded_from_db": True
                        },
                        created_at=db_collection.created_at or datetime.utcnow(),
                        updated_at=db_collection.updated_at or datetime.utcnow(),
                        expires_at=datetime.utcnow() + timedelta(hours=COLLECTION_TTL_HOURS)
                    )
                    
                    # Auto-mark as ready if it has enough feeds
                    feed_count = len([item for item in items if item.item_type == "feed"])
                    if feed_count >= MIN_FEEDS_PER_COLLECTION and collection.status == "building":
                        collection.status = "ready"
                        # Update database
                        db_collection.status = "ready"
                        db.commit()
                        logger.info(f"Auto-marked collection {collection.collection_id} as ready with {feed_count} feeds")
                    
                    self.collections[collection.collection_id] = collection
                
                logger.info(f"Loaded {len(self.collections)} collections from database")
                
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Error loading collections from database: {e}")
    
    async def create_collection(self, request: CollectionCreate, db: Session) -> CollectionDTO:
        """Create a new collection."""
        # Create collection in database
        db_collection = DBCollection(
            name=request.name,
            description=request.description,
            status="building"
        )
        db.add(db_collection)
        db.commit()
        db.refresh(db_collection)
        
        # Assign to podcast groups if specified
        if request.group_ids:
            for group_id in request.group_ids:
                group = db.query(PodcastGroup).filter(PodcastGroup.id == UUID(group_id)).first()
                if group:
                    db_collection.podcast_groups.append(group)
            db.commit()
            db.refresh(db_collection)
        
        # Create Pydantic model for response
        now = datetime.utcnow()
        created_at = db_collection.created_at or now
        updated_at = db_collection.updated_at or created_at
        collection = CollectionDTO(
            collection_id=str(db_collection.id),
            name=db_collection.name,
            description=db_collection.description,
            group_ids=[str(group.id) for group in db_collection.podcast_groups],
            status=db_collection.status,
            items=[],
            metadata={
                "priority_tags": request.priority_tags,
                "max_items": request.max_items,
                "min_feeds_required": MIN_FEEDS_PER_COLLECTION
            },
            created_at=created_at,
            updated_at=updated_at,
            expires_at=now + timedelta(hours=COLLECTION_TTL_HOURS)
        )
        # Store in-memory representation
        self.collections[collection.collection_id] = collection
        
        logger.info(f"Created collection {collection.collection_id} for groups {request.group_ids}")
        
        return collection
    
    async def add_feed_to_collection(self, collection_id: str, article: Article) -> bool:
        """Add a feed item to a collection."""
        if collection_id not in self.collections:
            return False
        
        collection = self.collections[collection_id]
        
        # Check if collection is still building and not expired
        if collection.status != "building" or (collection.expires_at and datetime.utcnow() > collection.expires_at):
            return False
        
        # Create feed item
        feed_item = CollectionItem(
            item_id=str(uuid4()),
            item_type="feed",
            content={
                "title": article.title,
                "link": article.link,
                "summary": article.summary,
                "content": article.content,
                "publish_date": article.publish_date.isoformat() if article.publish_date else None,
                "source": article.news_feed.name if article.news_feed else "Unknown"
            },
            created_at=datetime.utcnow(),
            metadata={
                "article_id": str(article.id),
                "feed_id": str(article.feed_id)
            }
        )
        
        collection.items.append(feed_item)
        collection.updated_at = datetime.utcnow()
        
        # Auto-review the feed if we have a reviewer
        try:
            await self._auto_review_feed(collection_id, feed_item)
        except Exception as e:
            logger.warning(f"Auto-review failed for feed {feed_item.item_id}: {e}")
        
        # Auto-mark collection as ready if it now has enough feeds
        feed_count = len([item for item in collection.items if item.item_type == "feed"])
        if feed_count >= MIN_FEEDS_PER_COLLECTION and collection.status == "building":
            collection.status = "ready"
            collection.updated_at = datetime.utcnow()
            logger.info(f"Auto-marked collection {collection_id} as ready with {feed_count} feeds")
        
        logger.info(f"Added feed to collection {collection_id}: {article.title[:50]}...")
        return True
    
    async def _auto_review_feed(self, collection_id: str, feed_item: CollectionItem):
        """Automatically review a feed item and add review to collection."""
        try:
            # Call reviewer service
            review_request = {
                "feed_id": feed_item.item_id,
                "title": feed_item.content["title"],
                "url": feed_item.content["link"],
                "content": feed_item.content.get("content", ""),
                "published": feed_item.content.get("publish_date", "")
            }
            
            response = await self.reviewer_client.post(
                f"{REVIEWER_URL}/review",
                json=review_request
            )
            response.raise_for_status()
            review_data = response.json()
            
            # Create review item
            review_item = CollectionItem(
                item_id=str(uuid4()),
                item_type="review",
                content={
                    "tags": review_data.get("tags", []),
                    "summary": review_data.get("summary", ""),
                    "confidence": review_data.get("confidence", 0.0),
                    "model": review_data.get("model", "unknown"),
                    "reviewer_type": review_data.get("reviewer_type", "unknown")
                },
                created_at=datetime.utcnow(),
                metadata={
                    "feed_item_id": feed_item.item_id,
                    "review_timestamp": datetime.utcnow().isoformat()
                }
            )
            
            collection = self.collections[collection_id]
            collection.items.append(review_item)
            collection.updated_at = datetime.utcnow()
            
            logger.info(f"Added review to collection {collection_id}: confidence={review_data.get('confidence', 0.0):.2f}")
            
        except Exception as e:
            logger.error(f"Failed to auto-review feed: {e}")
    
    def get_collection(self, collection_id: str) -> Optional[CollectionDTO]:
        """Get a collection by ID."""
        return self.collections.get(collection_id)
    
    def get_ready_collections(self, group_id: Optional[str] = None) -> List[CollectionDTO]:
        """Get collections that are ready for podcast generation."""
        ready_collections = []
        
        for collection in self.collections.values():
            if collection.status != "ready":
                continue
            
            if group_id and collection.group_id != group_id:
                continue
            
            # Check if collection has minimum required feeds
            feed_count = sum(1 for item in collection.items if item.item_type == "feed")
            if feed_count >= MIN_FEEDS_PER_COLLECTION:
                ready_collections.append(collection)
        
        return ready_collections
    
    def mark_collection_ready(self, collection_id: str) -> bool:
        """Mark a collection as ready for podcast generation."""
        if collection_id not in self.collections:
            return False
        
        collection = self.collections[collection_id]
        feed_count = sum(1 for item in collection.items if item.item_type == "feed")
        
        if feed_count >= MIN_FEEDS_PER_COLLECTION:
            collection.status = "ready"
            collection.updated_at = datetime.utcnow()
            logger.info(f"Marked collection {collection_id} as ready with {feed_count} feeds")
            return True
        
        return False
    
    def mark_collection_used(self, collection_id: str) -> bool:
        """Mark a collection as used (for podcast generation)."""
        if collection_id not in self.collections:
            return False
        
        collection = self.collections[collection_id]
        collection.status = "used"
        collection.updated_at = datetime.utcnow()
        logger.info(f"Marked collection {collection_id} as used")
        return True
    
    def cleanup_expired_collections(self):
        """Remove expired collections."""
        now = datetime.utcnow()
        expired_ids = []
        
        for collection_id, collection in self.collections.items():
            if collection.expires_at and now > collection.expires_at:
                expired_ids.append(collection_id)
        
        for collection_id in expired_ids:
            del self.collections[collection_id]
            logger.info(f"Cleaned up expired collection {collection_id}")
    
    def get_collections_for_group(self, group_id: str) -> List[CollectionDTO]:
        """Get all collections for a specific group."""
        return [c for c in self.collections.values() if c.group_id == group_id]


# Initialize collections manager
collections_manager = CollectionsManager()


# Create tables on startup
@app.on_event("startup")
async def startup_event():
    create_tables()
    logger.info("Collections Service started")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "collections",
        "collections_count": len(collections_manager.collections),
        "timestamp": datetime.utcnow()
    }


@app.post("/collections", response_model=CollectionResponse)
async def create_collection(request: CollectionCreate, db: Session = Depends(get_db)):
    """Create a new collection."""
    collection = await collections_manager.create_collection(request, db)
    
    return CollectionResponse(
        collection=collection,
        message=f"Collection {collection.collection_id} created successfully"
    )


@app.get("/collections/{collection_id}", response_model=CollectionDTO)
async def get_collection(collection_id: str):
    """Get a specific collection."""
    collection = collections_manager.get_collection(collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    return collection


@app.get("/collections", response_model=List[CollectionDTO])
async def list_collections(
    group_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50
):
    """List collections with optional filtering."""
    collections = list(collections_manager.collections.values())
    
    if group_id:
        collections = [c for c in collections if c.group_id == group_id]
    
    if status:
        collections = [c for c in collections if c.status == status]
    
    # Sort by updated_at descending
    collections.sort(key=lambda x: x.updated_at, reverse=True)
    
    return collections[:limit]


@app.get("/collections/ready", response_model=List[CollectionDTO])
async def get_ready_collections(group_id: Optional[str] = None):
    """Get collections that are ready for podcast generation."""
    return collections_manager.get_ready_collections(group_id)


@app.put("/collections/{collection_id}", response_model=CollectionResponse)
async def update_collection(collection_id: str, request: CollectionUpdate):
    """Update a collection."""
    collection = collections_manager.get_collection(collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    if request.status:
        collection.status = request.status
    
    if request.metadata:
        collection.metadata.update(request.metadata)
    
    collection.updated_at = datetime.utcnow()
    
    return CollectionResponse(
        collection=collection,
        message=f"Collection {collection_id} updated successfully"
    )


@app.post("/collections/{collection_id}/feeds/{article_id}")
async def add_feed_to_collection(
    collection_id: str,
    article_id: str,
    db: Session = Depends(get_db)
):
    """Add a feed to a collection."""
    # Get article from database
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    success = await collections_manager.add_feed_to_collection(collection_id, article)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to add feed to collection")
    
    return {"message": f"Feed {article_id} added to collection {collection_id}"}


@app.post("/collections/{collection_id}/ready")
async def mark_collection_ready(collection_id: str):
    """Mark a collection as ready for podcast generation."""
    success = collections_manager.mark_collection_ready(collection_id)
    if not success:
        raise HTTPException(status_code=400, detail="Collection does not meet minimum requirements")
    
    return {"message": f"Collection {collection_id} marked as ready"}


@app.post("/collections/{collection_id}/used")
async def mark_collection_used(collection_id: str):
    """Mark a collection as used."""
    success = collections_manager.mark_collection_used(collection_id)
    if not success:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    return {"message": f"Collection {collection_id} marked as used"}


@app.delete("/collections/{collection_id}")
async def delete_collection(collection_id: str):
    """Delete a collection."""
    if collection_id not in collections_manager.collections:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    del collections_manager.collections[collection_id]
    return {"message": f"Collection {collection_id} deleted successfully"}


@app.post("/collections/cleanup")
async def cleanup_expired_collections(background_tasks: BackgroundTasks):
    """Trigger cleanup of expired collections."""
    background_tasks.add_task(collections_manager.cleanup_expired_collections)
    return {"message": "Cleanup task queued"}


@app.get("/collections/group/{group_id}", response_model=List[CollectionDTO])
async def get_collections_for_group(group_id: str):
    """Get all collections for a specific group."""
    return collections_manager.get_collections_for_group(group_id)


@app.get("/collections/stats")
async def get_collections_stats():
    """Get collections statistics."""
    total_collections = len(collections_manager.collections)
    status_counts = {}
    
    for collection in collections_manager.collections.values():
        status = collection.status
        status_counts[status] = status_counts.get(status, 0) + 1
    
    return {
        "total_collections": total_collections,
        "status_counts": status_counts,
        "min_feeds_required": MIN_FEEDS_PER_COLLECTION,
        "collection_ttl_hours": COLLECTION_TTL_HOURS
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8011)