#!/usr/bin/env python3
"""
Complete System Setup - Sets up the entire podcast generation system.
This script initializes all components and creates the necessary data structures.
"""
import asyncio
import logging
import os
import sys
from datetime import datetime
from typing import Dict, Any, List
from uuid import UUID, uuid4

# Add shared directory to path
sys.path.append('/workspace/shared')

from shared.database import create_tables, get_db
from shared.models import PodcastGroup, Presenter, Writer, NewsFeed, FeedType

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SystemSetup:
    """Handles complete system setup and initialization."""
    
    def __init__(self):
        self.db = next(get_db())
    
    def create_database_tables(self):
        """Create all database tables."""
        logger.info("Creating database tables...")
        try:
            create_tables()
            logger.info("✓ Database tables created successfully")
            return True
        except Exception as e:
            logger.error(f"✗ Failed to create database tables: {e}")
            return False
    
    def create_sample_podcast_groups(self) -> List[Dict[str, Any]]:
        """Create sample podcast groups."""
        logger.info("Creating sample podcast groups...")
        
        sample_groups = [
            {
                "name": "Tech & Finance Daily",
                "description": "Daily analysis of technology and financial news",
                "category": "Technology",
                "subcategory": "Business Technology",
                "language": "en",
                "country": "US",
                "tags": ["technology", "finance", "ai", "markets"],
                "keywords": ["tech news", "financial analysis", "AI developments", "market trends"],
                "schedule": "0 8 * * *"  # Daily at 8 AM
            },
            {
                "name": "World News Roundup",
                "description": "Comprehensive coverage of global news and events",
                "category": "News",
                "subcategory": "World News",
                "language": "en",
                "country": "US",
                "tags": ["world news", "politics", "international", "current events"],
                "keywords": ["global news", "international affairs", "world politics", "current events"],
                "schedule": "0 18 * * *"  # Daily at 6 PM
            },
            {
                "name": "AI & Innovation Weekly",
                "description": "Weekly deep dive into AI developments and innovation",
                "category": "Technology",
                "subcategory": "Artificial Intelligence",
                "language": "en",
                "country": "US",
                "tags": ["ai", "innovation", "technology", "research"],
                "keywords": ["artificial intelligence", "machine learning", "innovation", "tech research"],
                "schedule": "0 10 * * 1"  # Weekly on Monday at 10 AM
            }
        ]
        
        created_groups = []
        for group_data in sample_groups:
            try:
                # Check if group already exists
                existing = self.db.query(PodcastGroup).filter(
                    PodcastGroup.name == group_data["name"]
                ).first()
                
                if not existing:
                    group = PodcastGroup(**group_data)
                    self.db.add(group)
                    self.db.commit()
                    self.db.refresh(group)
                    created_groups.append({
                        "id": str(group.id),
                        "name": group.name,
                        "description": group.description
                    })
                    logger.info(f"✓ Created podcast group: {group.name}")
                else:
                    created_groups.append({
                        "id": str(existing.id),
                        "name": existing.name,
                        "description": existing.description
                    })
                    logger.info(f"✓ Podcast group already exists: {existing.name}")
                    
            except Exception as e:
                logger.error(f"✗ Failed to create podcast group {group_data['name']}: {e}")
        
        return created_groups
    
    def create_sample_presenters(self) -> List[Dict[str, Any]]:
        """Create sample presenters."""
        logger.info("Creating sample presenters...")
        
        sample_presenters = [
            {
                "name": "Alex Chen",
                "bio": "Tech-savvy financial analyst with a passion for explaining complex topics in accessible ways. Specializes in AI, fintech, and market analysis.",
                "age": 32,
                "gender": "Non-binary",
                "country": "United States",
                "city": "San Francisco",
                "specialties": ["Technology", "Finance", "AI"],
                "expertise": ["Financial Markets", "Technology Trends", "Economic Analysis", "AI/ML"],
                "interests": ["Innovation", "Sustainability", "Social Impact", "Cryptocurrency"]
            },
            {
                "name": "Sarah Johnson",
                "bio": "Experienced journalist with a focus on international affairs and global politics. Known for balanced reporting and deep analysis.",
                "age": 28,
                "gender": "Female",
                "country": "United States",
                "city": "New York",
                "specialties": ["International Relations", "Politics", "Journalism"],
                "expertise": ["Global Politics", "International Affairs", "Diplomacy", "Conflict Analysis"],
                "interests": ["Human Rights", "Climate Change", "Global Economics", "Cultural Exchange"]
            },
            {
                "name": "Dr. Michael Rodriguez",
                "bio": "AI researcher and technology consultant with deep expertise in machine learning and emerging technologies. PhD in Computer Science.",
                "age": 35,
                "gender": "Male",
                "country": "United States",
                "city": "Seattle",
                "specialties": ["AI Research", "Machine Learning", "Technology Innovation"],
                "expertise": ["Artificial Intelligence", "Machine Learning", "Neural Networks", "Tech Innovation"],
                "interests": ["Research", "Education", "Ethics in AI", "Future Technology"]
            }
        ]
        
        created_presenters = []
        for presenter_data in sample_presenters:
            try:
                # Check if presenter already exists
                existing = self.db.query(Presenter).filter(
                    Presenter.name == presenter_data["name"]
                ).first()
                
                if not existing:
                    presenter = Presenter(**presenter_data)
                    self.db.add(presenter)
                    self.db.commit()
                    self.db.refresh(presenter)
                    created_presenters.append({
                        "id": str(presenter.id),
                        "name": presenter.name,
                        "bio": presenter.bio,
                        "expertise": presenter.expertise
                    })
                    logger.info(f"✓ Created presenter: {presenter.name}")
                else:
                    created_presenters.append({
                        "id": str(existing.id),
                        "name": existing.name,
                        "bio": existing.bio,
                        "expertise": existing.expertise
                    })
                    logger.info(f"✓ Presenter already exists: {existing.name}")
                    
            except Exception as e:
                logger.error(f"✗ Failed to create presenter {presenter_data['name']}: {e}")
        
        return created_presenters
    
    def create_sample_writers(self) -> List[Dict[str, Any]]:
        """Create sample writers."""
        logger.info("Creating sample writers...")
        
        sample_writers = [
            {
                "name": "Qwen3 Script Writer",
                "model": "qwen3:latest",
                "capabilities": ["script_generation", "content_creation", "storytelling"]
            },
            {
                "name": "Qwen3 Metadata Writer",
                "model": "qwen3:latest", 
                "capabilities": ["metadata_generation", "seo_optimization", "content_tagging"]
            }
        ]
        
        created_writers = []
        for writer_data in sample_writers:
            try:
                # Check if writer already exists
                existing = self.db.query(Writer).filter(
                    Writer.name == writer_data["name"]
                ).first()
                
                if not existing:
                    writer = Writer(**writer_data)
                    self.db.add(writer)
                    self.db.commit()
                    self.db.refresh(writer)
                    created_writers.append({
                        "id": str(writer.id),
                        "name": writer.name,
                        "model": writer.model,
                        "capabilities": writer.capabilities
                    })
                    logger.info(f"✓ Created writer: {writer.name}")
                else:
                    created_writers.append({
                        "id": str(existing.id),
                        "name": existing.name,
                        "model": existing.model,
                        "capabilities": existing.capabilities
                    })
                    logger.info(f"✓ Writer already exists: {existing.name}")
                    
            except Exception as e:
                logger.error(f"✗ Failed to create writer {writer_data['name']}: {e}")
        
        return created_writers
    
    def setup_rss_feeds(self) -> bool:
        """Setup RSS feeds."""
        logger.info("Setting up RSS feeds...")
        try:
            # Run the RSS feeds setup script
            import subprocess
            result = subprocess.run(
                ["python", "/workspace/setup_rss_feeds.py"],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                logger.info("✓ RSS feeds setup completed successfully")
                return True
            else:
                logger.error(f"✗ RSS feeds setup failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"✗ RSS feeds setup failed: {e}")
            return False
    
    def create_docker_compose_override(self):
        """Create docker-compose override for the new services."""
        logger.info("Creating docker-compose override...")
        
        override_content = """
version: '3.8'

services:
  reviewer:
    build:
      context: .
      dockerfile: services/reviewer/Dockerfile
    ports:
      - "8007:8007"
    environment:
      - OLLAMA_BASE_URL=http://ollama:11434
      - OLLAMA_MODEL=qwen3:latest
    depends_on:
      - ollama
      - postgres
    volumes:
      - ./services/reviewer:/app
      - ./shared:/app/shared

  presenter-persona:
    build:
      context: .
      dockerfile: services/presenter/Dockerfile
    ports:
      - "8008:8008"
    environment:
      - OLLAMA_BASE_URL=http://ollama:11434
      - OLLAMA_MODEL=gpt-oss-20b
    depends_on:
      - ollama
      - postgres
    volumes:
      - ./services/presenter:/app
      - ./shared:/app/shared

  writer-script:
    build:
      context: .
      dockerfile: services/writer/Dockerfile
    ports:
      - "8010:8010"
    environment:
      - OLLAMA_BASE_URL=http://ollama:11434
      - OLLAMA_MODEL=qwen3:latest
    depends_on:
      - ollama
      - postgres
    volumes:
      - ./services/writer:/app
      - ./shared:/app/shared

  editor:
    build:
      context: .
      dockerfile: services/editor/Dockerfile
    ports:
      - "8009:8009"
    environment:
      - OLLAMA_BASE_URL=http://ollama:11434
      - OLLAMA_MODEL=qwen3:latest
    depends_on:
      - ollama
      - postgres
    volumes:
      - ./services/editor:/app
      - ./shared:/app/shared

  collections:
    build:
      context: .
      dockerfile: services/collections/Dockerfile
    ports:
      - "8011:8011"
    depends_on:
      - postgres
    volumes:
      - ./services/collections:/app
      - ./shared:/app/shared

  ai-overseer-enhanced:
    build:
      context: .
      dockerfile: services/ai-overseer/Dockerfile
    ports:
      - "8012:8012"
    depends_on:
      - reviewer
      - presenter-persona
      - writer-script
      - editor
      - collections
      - news-feed
    volumes:
      - ./services/ai-overseer:/app
      - ./shared:/app/shared

  presenter-vibevoice:
    build:
      context: .
      dockerfile: services/presenter/Dockerfile
    ports:
      - "8013:8013"
    environment:
      - VIBEVOICE_PATH=/workspace/VibeVoice-Community
    depends_on:
      - postgres
    volumes:
      - ./services/presenter:/app
      - ./shared:/app/shared
      - ./VibeVoice-Community:/workspace/VibeVoice-Community
"""
        
        try:
            with open("/workspace/docker-compose.override.yml", "w") as f:
                f.write(override_content)
            logger.info("✓ Docker compose override created")
            return True
        except Exception as e:
            logger.error(f"✗ Failed to create docker compose override: {e}")
            return False
    
    def run_complete_setup(self) -> Dict[str, Any]:
        """Run the complete system setup."""
        logger.info("Starting complete system setup...")
        start_time = datetime.utcnow()
        
        setup_results = {
            "database_tables": self.create_database_tables(),
            "podcast_groups": self.create_sample_podcast_groups(),
            "presenters": self.create_sample_presenters(),
            "writers": self.create_sample_writers(),
            "rss_feeds": self.setup_rss_feeds(),
            "docker_compose": self.create_docker_compose_override()
        }
        
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        # Calculate success rate
        successful_setups = sum(1 for success in setup_results.values() if success)
        total_setups = len(setup_results)
        
        summary = {
            "setup_summary": {
                "total_components": total_setups,
                "successful_setups": successful_setups,
                "failed_setups": total_setups - successful_setups,
                "success_rate": f"{(successful_setups / total_setups * 100):.1f}%" if total_setups > 0 else "0%",
                "duration_seconds": duration
            },
            "setup_results": setup_results,
            "timestamp": end_time.isoformat()
        }
        
        return summary
    
    def __del__(self):
        """Clean up database connection."""
        if hasattr(self, 'db'):
            self.db.close()


def main():
    """Main setup function."""
    print("="*80)
    print("PODCAST GENERATION SYSTEM - COMPLETE SETUP")
    print("="*80)
    
    setup = SystemSetup()
    
    try:
        # Run complete setup
        results = setup.run_complete_setup()
        
        # Print summary
        summary = results["setup_summary"]
        print(f"\nSetup Summary:")
        print(f"Total Components: {summary['total_components']}")
        print(f"Successful: {summary['successful_setups']}")
        print(f"Failed: {summary['failed_setups']}")
        print(f"Success Rate: {summary['success_rate']}")
        print(f"Duration: {summary['duration_seconds']:.2f} seconds")
        
        print(f"\nDetailed Results:")
        print("-" * 40)
        
        for component, success in results["setup_results"].items():
            status = "✓ SUCCESS" if success else "✗ FAILED"
            print(f"{component}: {status}")
        
        # Save results
        import json
        with open("/workspace/setup_results.json", "w") as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\nSetup results saved to: /workspace/setup_results.json")
        
        if summary["successful_setups"] == summary["total_components"]:
            print("\n🎉 COMPLETE SETUP SUCCESSFUL!")
            print("\nNext steps:")
            print("1. Start the services: docker-compose up -d")
            print("2. Run the test: python /workspace/test_complete_workflow.py")
            print("3. Generate a podcast: Use the AI Overseer API")
            return True
        else:
            print(f"\n⚠️  {summary['failed_setups']} components failed setup. Please check the logs above.")
            return False
            
    except Exception as e:
        logger.error(f"Setup failed: {e}")
        print(f"\n❌ Setup failed: {e}")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)