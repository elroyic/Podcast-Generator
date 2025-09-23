"""
Pydantic schemas for request/response validation.
"""
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field


# Enums
class PodcastGroupStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class FeedType(str, Enum):
    RSS = "RSS"
    MCP = "MCP"


class EpisodeStatus(str, Enum):
    DRAFT = "draft"
    VOICED = "voiced"
    PUBLISHED = "published"


# Base schemas
class BaseSchema(BaseModel):
    class Config:
        from_attributes = True


# Presenter schemas
class PresenterBase(BaseSchema):
    name: str
    bio: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    demographics: Optional[Dict[str, Any]] = None
    biases: Optional[Dict[str, Any]] = None
    specialties: Optional[List[str]] = None
    expertise: Optional[List[str]] = None
    interests: Optional[List[str]] = None
    country: Optional[str] = None
    city: Optional[str] = None


class PresenterCreate(PresenterBase):
    pass


class PresenterUpdate(PresenterBase):
    name: Optional[str] = None


class Presenter(PresenterBase):
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None


# Writer schemas
class WriterBase(BaseSchema):
    name: str
    model: str = "Ollama"
    capabilities: Optional[List[str]] = None


class WriterCreate(WriterBase):
    pass


class WriterUpdate(WriterBase):
    name: Optional[str] = None
    model: Optional[str] = None


class Writer(WriterBase):
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None


# News Feed schemas
class NewsFeedBase(BaseSchema):
    source_url: str
    name: Optional[str] = None
    type: FeedType
    is_active: bool = True


class NewsFeedCreate(NewsFeedBase):
    pass


class NewsFeedUpdate(NewsFeedBase):
    source_url: Optional[str] = None
    type: Optional[FeedType] = None
    is_active: Optional[bool] = None


class NewsFeed(NewsFeedBase):
    id: UUID
    last_fetched: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


# Article schemas
class ArticleBase(BaseSchema):
    title: str
    link: str
    summary: Optional[str] = None
    content: Optional[str] = None
    publish_date: Optional[datetime] = None


class ArticleCreate(ArticleBase):
    feed_id: UUID


class Article(ArticleBase):
    id: UUID
    feed_id: UUID
    created_at: datetime


# Podcast Group schemas
class PodcastGroupBase(BaseSchema):
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    language: Optional[str] = None
    country: Optional[str] = None
    tags: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    schedule: Optional[str] = None
    status: PodcastGroupStatus = PodcastGroupStatus.ACTIVE


class PodcastGroupCreate(PodcastGroupBase):
    presenter_ids: List[UUID] = Field(default_factory=list)
    writer_id: UUID
    news_feed_ids: List[UUID] = Field(default_factory=list)


class PodcastGroupUpdate(PodcastGroupBase):
    name: Optional[str] = None
    presenter_ids: Optional[List[UUID]] = None
    writer_id: Optional[UUID] = None
    news_feed_ids: Optional[List[UUID]] = None
    status: Optional[PodcastGroupStatus] = None


class PodcastGroup(PodcastGroupBase):
    id: UUID
    writer_id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    presenters: List[Presenter] = []
    writer: Optional[Writer] = None
    news_feeds: List[NewsFeed] = []


# Episode schemas
class EpisodeMetadataBase(BaseSchema):
    title: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    language: Optional[str] = None
    country: Optional[str] = None


class EpisodeMetadataCreate(EpisodeMetadataBase):
    pass


class EpisodeMetadata(EpisodeMetadataBase):
    episode_id: UUID
    created_at: datetime


class AudioFileBase(BaseSchema):
    url: Optional[str] = None
    duration_seconds: Optional[int] = None
    file_size_bytes: Optional[int] = None
    format: Optional[str] = None


class AudioFileCreate(AudioFileBase):
    pass


class AudioFile(AudioFileBase):
    episode_id: UUID
    created_at: datetime


class EpisodeBase(BaseSchema):
    script: Optional[str] = None
    status: EpisodeStatus = EpisodeStatus.DRAFT


class EpisodeCreate(EpisodeBase):
    group_id: UUID
    article_ids: List[UUID] = Field(default_factory=list)


class EpisodeUpdate(EpisodeBase):
    script: Optional[str] = None
    status: Optional[EpisodeStatus] = None


class Episode(EpisodeBase):
    id: UUID
    group_id: UUID
    created_at: datetime
    metadata: Optional[EpisodeMetadata] = None
    audio_file: Optional[AudioFile] = None
    articles: List[Article] = []


# Publish Record schemas
class PublishRecordBase(BaseSchema):
    platform: str
    external_id: Optional[str] = None
    public_url: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    published_at: Optional[datetime] = None


class PublishRecordCreate(PublishRecordBase):
    episode_id: UUID


class PublishRecord(PublishRecordBase):
    id: UUID
    episode_id: UUID
    created_at: datetime


# Request/Response schemas
class GenerationRequest(BaseSchema):
    group_id: UUID
    force_regenerate: bool = False


class GenerationResponse(BaseSchema):
    episode_id: UUID
    status: str
    message: str


class HealthCheck(BaseSchema):
    status: str
    timestamp: datetime
    services: Dict[str, str] = {}


class ErrorResponse(BaseSchema):
    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)