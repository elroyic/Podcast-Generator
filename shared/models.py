"""
Shared database models for the Podcast AI application.
"""
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4

from sqlalchemy import (
    Column, String, Text, Integer, DateTime, Enum as SQLEnum,
    ForeignKey, Table, JSON, Boolean, Float
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID, ARRAY
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()

# Association tables
podcast_group_presenter = Table(
    'podcast_group_presenter',
    Base.metadata,
    Column('group_id', PGUUID(as_uuid=True), ForeignKey('podcast_groups.id'), primary_key=True),
    Column('presenter_id', PGUUID(as_uuid=True), ForeignKey('presenters.id'), primary_key=True),
    Column('order', Integer, nullable=False, default=1)
)

news_feed_assignment = Table(
    'news_feed_assignment',
    Base.metadata,
    Column('group_id', PGUUID(as_uuid=True), ForeignKey('podcast_groups.id'), primary_key=True),
    Column('feed_id', PGUUID(as_uuid=True), ForeignKey('news_feeds.id'), primary_key=True)
)

episode_article_link = Table(
    'episode_article_link',
    Base.metadata,
    Column('episode_id', PGUUID(as_uuid=True), ForeignKey('episodes.id'), primary_key=True),
    Column('article_id', PGUUID(as_uuid=True), ForeignKey('articles.id'), primary_key=True)
)


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


class PodcastGroup(Base):
    __tablename__ = "podcast_groups"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    category = Column(String(100))
    subcategory = Column(String(100))
    language = Column(String(10))  # ISO-639-1
    country = Column(String(2))    # ISO-3166-1 alpha-2
    tags = Column(ARRAY(String))
    keywords = Column(ARRAY(String))
    schedule = Column(String(100))  # cron expression
    status = Column(SQLEnum(PodcastGroupStatus, native_enum=False), default=PodcastGroupStatus.ACTIVE)
    writer_id = Column(PGUUID(as_uuid=True), ForeignKey('writers.id'))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    presenters = relationship("Presenter", secondary=podcast_group_presenter, back_populates="podcast_groups")
    episodes = relationship("Episode", back_populates="podcast_group")
    writer = relationship("Writer", back_populates="podcast_groups")
    news_feeds = relationship("NewsFeed", secondary=news_feed_assignment, back_populates="podcast_groups")


class Presenter(Base):
    __tablename__ = "presenters"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False)
    bio = Column(Text)
    age = Column(Integer)
    gender = Column(String(50))
    demographics = Column(JSON)
    biases = Column(JSON)  # topic-specific bias weighting
    specialties = Column(ARRAY(String))
    expertise = Column(ARRAY(String))
    interests = Column(ARRAY(String))
    country = Column(String(100))
    city = Column(String(100))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    podcast_groups = relationship("PodcastGroup", secondary=podcast_group_presenter, back_populates="presenters")


class Writer(Base):
    __tablename__ = "writers"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False)
    model = Column(String(100), default="Ollama")
    capabilities = Column(ARRAY(String))  # metadata fields it can generate
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    podcast_groups = relationship("PodcastGroup", back_populates="writer")


class NewsFeed(Base):
    __tablename__ = "news_feeds"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    source_url = Column(String(500), nullable=False)
    name = Column(String(255))
    type = Column(SQLEnum(FeedType, native_enum=False), nullable=False)
    last_fetched = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    articles = relationship("Article", back_populates="news_feed")
    podcast_groups = relationship("PodcastGroup", secondary=news_feed_assignment, back_populates="news_feeds")


class Article(Base):
    __tablename__ = "articles"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    feed_id = Column(PGUUID(as_uuid=True), ForeignKey('news_feeds.id'), nullable=False)
    title = Column(String(500), nullable=False)
    link = Column(String(1000), nullable=False)
    summary = Column(Text)
    content = Column(Text)
    publish_date = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    news_feed = relationship("NewsFeed", back_populates="articles")
    episodes = relationship("Episode", secondary=episode_article_link, back_populates="articles")


class Episode(Base):
    __tablename__ = "episodes"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    group_id = Column(PGUUID(as_uuid=True), ForeignKey('podcast_groups.id'), nullable=False)
    script = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(SQLEnum(EpisodeStatus, native_enum=False), default=EpisodeStatus.DRAFT)

    # Relationships
    podcast_group = relationship("PodcastGroup", back_populates="episodes")
    episode_metadata = relationship("EpisodeMetadata", back_populates="episode", uselist=False)
    audio_file = relationship("AudioFile", back_populates="episode", uselist=False)
    articles = relationship("Article", secondary=episode_article_link, back_populates="episodes")


class EpisodeMetadata(Base):
    __tablename__ = "episode_metadata"

    episode_id = Column(PGUUID(as_uuid=True), ForeignKey('episodes.id'), primary_key=True)
    title = Column(String(500))
    description = Column(Text)
    tags = Column(ARRAY(String))
    keywords = Column(ARRAY(String))
    category = Column(String(100))
    subcategory = Column(String(100))
    language = Column(String(10))
    country = Column(String(2))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    episode = relationship("Episode", back_populates="episode_metadata")


class AudioFile(Base):
    __tablename__ = "audio_files"

    episode_id = Column(PGUUID(as_uuid=True), ForeignKey('episodes.id'), primary_key=True)
    url = Column(String(1000))  # blob storage location
    duration_seconds = Column(Integer)
    file_size_bytes = Column(Integer)
    format = Column(String(10))  # mp3, wav, etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    episode = relationship("Episode", back_populates="audio_file")


class PublishRecord(Base):
    __tablename__ = "publish_records"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    episode_id = Column(PGUUID(as_uuid=True), ForeignKey('episodes.id'), nullable=False)
    platform = Column(String(100), nullable=False)  # anchor, libsyn, etc.
    external_id = Column(String(255))  # platform's episode ID
    public_url = Column(String(1000))
    status = Column(String(50))  # pending, published, failed
    error_message = Column(Text)
    published_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    episode = relationship("Episode")