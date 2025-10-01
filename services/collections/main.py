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
    
    async def create_collection_snapshot(self, collection_id: str, episode_id: str, db: Session) -> Optional[str]:
        """Create a snapshot of a collection for an episode and create a new collection for future articles."""
        try:
            # Get the original collection from database
            from uuid import UUID
            db_collection = db.query(DBCollection).filter(DBCollection.id == UUID(collection_id)).first()
            if not db_collection:
                logger.error(f"Collection {collection_id} not found in database")
                return None
            
            # Get all articles in this collection
            articles = db.query(Article).filter(Article.collection_id == UUID(collection_id)).all()
            
            if not articles:
                logger.warning(f"No articles found in collection {collection_id}")
                return None
            
            # Create snapshot collection with episode ID in name
            snapshot_name = f"Episode {episode_id[:8]} Snapshot"
            snapshot_collection = DBCollection(
                name=snapshot_name,
                description=f"Snapshot of {db_collection.name} for episode {episode_id}",
                status="snapshot",
                episode_id=UUID(episode_id),
                parent_collection_id=UUID(collection_id)
            )
            db.add(snapshot_collection)
            db.flush()  # Get the ID without committing
            
            # Assign the same podcast groups to snapshot
            snapshot_collection.podcast_groups = db_collection.podcast_groups
            
            # Move articles from original collection to snapshot
            article_count = 0
            for article in articles:
                article.collection_id = snapshot_collection.id
                article_count += 1
            
            logger.info(f"Moved {article_count} articles to snapshot collection {snapshot_collection.id}")
            
            # Create a new collection to continue collecting articles
            new_collection = DBCollection(
                name=db_collection.name,  # Keep the same name
                description=db_collection.description,
                status="building",
                parent_collection_id=snapshot_collection.id  # Link to snapshot as parent
            )
            db.add(new_collection)
            db.flush()
            
            # Assign the same podcast groups to new collection
            new_collection.podcast_groups = db_collection.podcast_groups
            
            # Delete the old collection as it's now empty and replaced
            db.delete(db_collection)
            
            # Commit all changes
            db.commit()
            db.refresh(snapshot_collection)
            db.refresh(new_collection)
            
            # Update in-memory collections
            # Remove old collection from memory
            if collection_id in self.collections:
                del self.collections[collection_id]
            
            # Add snapshot to memory
            snapshot_dto = CollectionDTO(
                collection_id=str(snapshot_collection.id),
                name=snapshot_collection.name,
                description=snapshot_collection.description,
                group_ids=[str(group.id) for group in snapshot_collection.podcast_groups],
                status=snapshot_collection.status,
                items=[],  # Articles are in DB, not loaded to memory for snapshots
                metadata={
                    "episode_id": episode_id,
                    "article_count": article_count,
                    "snapshot_created_at": datetime.utcnow().isoformat()
                },
                created_at=snapshot_collection.created_at or datetime.utcnow(),
                updated_at=snapshot_collection.updated_at or datetime.utcnow(),
                expires_at=None  # Snapshots don't expire
            )
            self.collections[str(snapshot_collection.id)] = snapshot_dto
            
            # Add new building collection to memory
            new_dto = CollectionDTO(
                collection_id=str(new_collection.id),
                name=new_collection.name,
                description=new_collection.description,
                group_ids=[str(group.id) for group in new_collection.podcast_groups],
                status=new_collection.status,
                items=[],
                metadata={
                    "parent_snapshot_id": str(snapshot_collection.id),
                    "created_from_snapshot": True
                },
                created_at=new_collection.created_at or datetime.utcnow(),
                updated_at=new_collection.updated_at or datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(hours=COLLECTION_TTL_HOURS)
            )
            self.collections[str(new_collection.id)] = new_dto
            
            logger.info(f"✅ Created snapshot {snapshot_collection.id} with {article_count} articles")
            logger.info(f"✅ Created new building collection {new_collection.id}")
            
            return str(snapshot_collection.id)
            
        except Exception as e:
            logger.error(f"Error creating collection snapshot: {e}")
            db.rollback()
            return None
    
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
        return [c for c in self.collections.values() if group_id in c.group_ids]
    
    def get_active_collection_for_group(self, group_id: str, db: Session) -> Optional[str]:
        """Get the active collection for a group - prioritize ready over building, create one if none exists."""
        # Check in-memory collections first - prioritize ready over building
        ready_collection = None
        building_collection = None
        
        for collection in self.collections.values():
            if group_id in collection.group_ids:
                if collection.status == "ready" and not ready_collection:
                    ready_collection = collection.collection_id
                elif collection.status == "building" and not building_collection:
                    building_collection = collection.collection_id
        
        # Return ready first, then building
        if ready_collection:
            logger.info(f"Found ready collection {ready_collection} for group {group_id}")
            return ready_collection
        if building_collection:
            return building_collection
        
        # Check database for ready or building collections
        from uuid import UUID
        group = db.query(PodcastGroup).filter(PodcastGroup.id == UUID(group_id)).first()
        if not group:
            logger.error(f"Group {group_id} not found")
            return None
        
        # Find ready collection first, then building collection for this group
        for collection in group.collections:
            if collection.status == "ready":
                self._load_collection_into_memory(collection, db)
                logger.info(f"Found ready collection {collection.id} in DB for group {group_id}")
                return str(collection.id)
        
        for collection in group.collections:
            if collection.status == "building":
                # Load it into memory
                self._load_collection_into_memory(collection, db)
                return str(collection.id)
        
        # No building collection found, create one
        logger.info(f"No building collection found for group {group_id}, creating one")
        new_collection = DBCollection(
            name=f"{group.name} Collection",
            description=f"Active collection for {group.name}",
            status="building"
        )
        db.add(new_collection)
        db.flush()
        
        # Assign to group
        new_collection.podcast_groups.append(group)
        db.commit()
        db.refresh(new_collection)
        
        # Load into memory
        self._load_collection_into_memory(new_collection, db)
        
        logger.info(f"Created new building collection {new_collection.id} for group {group_id}")
        return str(new_collection.id)
    
    def _load_collection_into_memory(self, db_collection: DBCollection, db: Session):
        """Load a collection from database into memory."""
        articles = db.query(Article).filter(Article.collection_id == db_collection.id).all()
        
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
        
        collection_dto = CollectionDTO(
            collection_id=str(db_collection.id),
            name=db_collection.name,
            description=db_collection.description,
            group_ids=[str(group.id) for group in db_collection.podcast_groups],
            status=db_collection.status,
            items=items,
            metadata={"loaded_from_db": True},
            created_at=db_collection.created_at or datetime.utcnow(),
            updated_at=db_collection.updated_at or datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=COLLECTION_TTL_HOURS) if db_collection.status == "building" else None
        )
        
        self.collections[str(db_collection.id)] = collection_dto


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


@app.get("/metrics/prometheus")
async def get_prometheus_metrics(db: Session = Depends(get_db)):
    """Prometheus-compatible metrics endpoint."""
    from fastapi.responses import PlainTextResponse
    
    try:
        # Get worker count from environment or default to 1
        workers_active = int(os.getenv("WORKERS_ACTIVE", "1"))
        
        # Count collections by status
        status_counts = {}
        for status in ["building", "ready", "used", "expired"]:
            count = db.query(DBCollection).filter(DBCollection.status == status).count()
            status_counts[status] = count
        
        # Total collections
        total_collections = len(collections_manager.collections)
        
        # Generate Prometheus format
        metrics = []
        
        # Worker metrics
        metrics.append(f"collections_workers_active {workers_active}")
        
        # Collection metrics by status
        for status, count in status_counts.items():
            metrics.append(f'collections_total{{status="{status}"}} {count}')
        
        # Active collections
        metrics.append(f"collections_active_total {total_collections}")
        
        prometheus_output = "\n".join([
            "# HELP collections_workers_active Number of active workers",
            "# TYPE collections_workers_active gauge",
            "# HELP collections_total Total collections by status",
            "# TYPE collections_total gauge",
            "# HELP collections_active_total Total active collections in memory",
            "# TYPE collections_active_total gauge",
            "",
            *metrics
        ])
        
        return PlainTextResponse(prometheus_output, media_type="text/plain")
    except Exception as e:
        logger.error(f"Error generating Prometheus metrics: {e}")
        return PlainTextResponse("# Error generating metrics\n", media_type="text/plain")


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
        collections = [c for c in collections if group_id in c.group_ids]  # Fixed: group_ids is a list
    
    if status:
        collections = [c for c in collections if c.status == status]
    
    # Sort by updated_at descending - handle timezone-aware and naive datetimes
    def safe_sort_key(x):
        try:
            dt = x.updated_at
            # If timezone-naive, treat as UTC
            if dt and dt.tzinfo is None:
                from datetime import timezone
                return dt.replace(tzinfo=timezone.utc)
            return dt if dt else datetime.min.replace(tzinfo=timezone.utc)
        except:
            from datetime import timezone
            return datetime.min.replace(tzinfo=timezone.utc)
    
    collections.sort(key=safe_sort_key, reverse=True)
    
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


@app.post("/collections/{collection_id}/snapshot")
async def create_collection_snapshot(
    collection_id: str,
    episode_id: str,
    db: Session = Depends(get_db)
):
    """Create a snapshot of a collection for an episode and create a new collection for future articles."""
    snapshot_id = await collections_manager.create_collection_snapshot(collection_id, episode_id, db)
    
    if not snapshot_id:
        raise HTTPException(status_code=400, detail="Failed to create collection snapshot")
    
    return {
        "message": f"Collection snapshot created successfully",
        "snapshot_id": snapshot_id,
        "original_collection_id": collection_id,
        "episode_id": episode_id
    }


@app.get("/collections/group/{group_id}/active")
async def get_active_collection_for_group(
    group_id: str,
    db: Session = Depends(get_db)
):
    """Get or create the active building collection for a group."""
    collection_id = collections_manager.get_active_collection_for_group(group_id, db)
    
    if not collection_id:
        raise HTTPException(status_code=404, detail="Failed to get or create active collection")
    
    collection = collections_manager.get_collection(collection_id)
    return collection


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8011)