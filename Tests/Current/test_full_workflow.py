#!/usr/bin/env python3
"""
Full Workflow Tests - Test complete end-to-end podcast generation workflow.
"""
import asyncio
import httpx
import pytest
import logging
from typing import Dict, List
from datetime import datetime
import json
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Service URLs
API_GATEWAY_URL = "http://localhost:8000"
NEWS_FEED_URL = "http://localhost:8001"
COLLECTIONS_URL = "http://localhost:8011"
REVIEWER_URL = "http://localhost:8009"
AI_OVerseer_URL = "http://localhost:8006"
WRITER_URL = "http://localhost:8003"
PRESENTER_URL = "http://localhost:8004"
PUBLISHING_URL = "http://localhost:8005"


class FullWorkflowTester:
    """Test the complete end-to-end podcast generation workflow."""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=120.0)
        self.test_results = {}
        self.test_data = {
            "group_id": None,
            "presenter_id": None,
            "writer_id": None,
            "feed_ids": [],
            "collection_id": None,
            "episode_id": None
        }
    
    async def setup_test_data(self) -> Dict:
        """Set up test data for the workflow."""
        logger.info("🔧 Setting up test data...")
        
        setup_results = {}
        
        # Create a test podcast group
        try:
            group_data = {
                "name": "Test Tech News",
                "description": "Test podcast group for workflow testing",
                "schedule": "daily",
                "podcast_length": 10,
                "tags": ["technology", "ai", "news"],
                "subjects": ["artificial intelligence", "tech industry"]
            }
            
            response = await self.client.post(f"{API_GATEWAY_URL}/api/podcast-groups", json=group_data)
            if response.status_code == 200:
                group = response.json()
                self.test_data["group_id"] = group["id"]
                setup_results['podcast_group'] = {"status": "success", "group_id": group["id"]}
                logger.info(f"✅ Created test podcast group: {group['id']}")
            else:
                setup_results['podcast_group'] = {"status": "error", "error": f"HTTP {response.status_code}"}
                logger.error(f"❌ Failed to create podcast group: {response.status_code}")
        except Exception as e:
            setup_results['podcast_group'] = {"status": "error", "error": str(e)}
            logger.error(f"❌ Exception creating podcast group: {e}")
        
        # Create a test presenter
        try:
            presenter_data = {
                "name": "Test Presenter",
                "persona": "A knowledgeable tech journalist with a friendly, engaging style",
                "voice_model": "vibevoice",
                "llm_model": "gpt-oss-20b",
                "status": "active"
            }
            
            response = await self.client.post(f"{API_GATEWAY_URL}/api/presenters", json=presenter_data)
            if response.status_code == 200:
                presenter = response.json()
                self.test_data["presenter_id"] = presenter["id"]
                setup_results['presenter'] = {"status": "success", "presenter_id": presenter["id"]}
                logger.info(f"✅ Created test presenter: {presenter['id']}")
            else:
                setup_results['presenter'] = {"status": "error", "error": f"HTTP {response.status_code}"}
                logger.error(f"❌ Failed to create presenter: {response.status_code}")
        except Exception as e:
            setup_results['presenter'] = {"status": "error", "error": str(e)}
            logger.error(f"❌ Exception creating presenter: {e}")
        
        # Create a test writer
        try:
            writer_data = {
                "name": "Test Writer",
                "llm_model": "qwen3:4b",
                "status": "active"
            }
            
            response = await self.client.post(f"{API_GATEWAY_URL}/api/writers", json=writer_data)
            if response.status_code == 200:
                writer = response.json()
                self.test_data["writer_id"] = writer["id"]
                setup_results['writer'] = {"status": "success", "writer_id": writer["id"]}
                logger.info(f"✅ Created test writer: {writer['id']}")
            else:
                setup_results['writer'] = {"status": "error", "error": f"HTTP {response.status_code}"}
                logger.error(f"❌ Failed to create writer: {response.status_code}")
        except Exception as e:
            setup_results['writer'] = {"status": "error", "error": str(e)}
            logger.error(f"❌ Exception creating writer: {e}")
        
        return setup_results
    
    async def test_news_feed_processing(self) -> Dict:
        """Test news feed processing and article creation."""
        logger.info("🔍 Testing News Feed Processing...")
        
        # Create a test news feed
        try:
            feed_data = {
                "source_url": "https://feeds.bbci.co.uk/news/technology/rss.xml",
                "name": "BBC Technology Test Feed",
                "type": "RSS",
                "is_active": True
            }
            
            response = await self.client.post(f"{API_GATEWAY_URL}/api/news-feeds", json=feed_data)
            if response.status_code == 200:
                feed = response.json()
                feed_id = feed["id"]
                logger.info(f"✅ Created test news feed: {feed_id}")
                
                # Trigger feed processing
                process_response = await self.client.post(f"{NEWS_FEED_URL}/process-feed/{feed_id}")
                if process_response.status_code == 200:
                    result = process_response.json()
                    articles_processed = result.get("articles_processed", 0)
                    logger.info(f"✅ Processed feed: {articles_processed} articles")
                    
                    # Get articles for this feed
                    articles_response = await self.client.get(f"{API_GATEWAY_URL}/api/articles?feed_id={feed_id}")
                    if articles_response.status_code == 200:
                        articles = articles_response.json()
                        self.test_data["feed_ids"] = [str(article["id"]) for article in articles[:3]]  # Take first 3
                        logger.info(f"✅ Retrieved {len(articles)} articles for testing")
                        
                        return {
                            "status": "success",
                            "feed_id": feed_id,
                            "articles_processed": articles_processed,
                            "test_articles": len(self.test_data["feed_ids"])
                        }
                    else:
                        return {"status": "error", "error": f"Failed to get articles: {articles_response.status_code}"}
                else:
                    return {"status": "error", "error": f"Failed to process feed: {process_response.status_code}"}
            else:
                return {"status": "error", "error": f"Failed to create feed: {response.status_code}"}
                
        except Exception as e:
            logger.error(f"❌ News feed processing exception: {e}")
            return {"status": "error", "error": str(e)}
    
    async def test_collection_creation_and_management(self) -> Dict:
        """Test collection creation and management."""
        logger.info("🔍 Testing Collection Creation and Management...")
        
        if not self.test_data["group_id"]:
            return {"status": "error", "error": "No group ID available"}
        
        try:
            # Create a collection
            collection_data = {
                "group_id": self.test_data["group_id"],
                "priority_tags": ["technology", "ai"],
                "max_items": 10
            }
            
            response = await self.client.post(f"{COLLECTIONS_URL}/collections", json=collection_data)
            if response.status_code == 200:
                result = response.json()
                collection = result.get('collection', {})
                self.test_data["collection_id"] = collection.get('collection_id')
                logger.info(f"✅ Created collection: {self.test_data['collection_id']}")
                
                # Add articles to collection (if we have any)
                if self.test_data["feed_ids"]:
                    for article_id in self.test_data["feed_ids"][:2]:  # Add first 2 articles
                        add_response = await self.client.post(
                            f"{COLLECTIONS_URL}/collections/{self.test_data['collection_id']}/feeds/{article_id}"
                        )
                        if add_response.status_code == 200:
                            logger.info(f"✅ Added article {article_id} to collection")
                        else:
                            logger.warning(f"⚠️  Failed to add article {article_id}: {add_response.status_code}")
                
                # Mark collection as ready
                ready_response = await self.client.post(
                    f"{COLLECTIONS_URL}/collections/{self.test_data['collection_id']}/ready"
                )
                if ready_response.status_code == 200:
                    logger.info(f"✅ Marked collection as ready")
                else:
                    logger.warning(f"⚠️  Failed to mark collection as ready: {ready_response.status_code}")
                
                return {
                    "status": "success",
                    "collection_id": self.test_data["collection_id"],
                    "articles_added": len(self.test_data["feed_ids"][:2])
                }
            else:
                return {"status": "error", "error": f"Failed to create collection: {response.status_code}"}
                
        except Exception as e:
            logger.error(f"❌ Collection management exception: {e}")
            return {"status": "error", "error": str(e)}
    
    async def test_episode_generation(self) -> Dict:
        """Test episode generation workflow."""
        logger.info("🔍 Testing Episode Generation...")
        
        if not all([self.test_data["group_id"], self.test_data["presenter_id"], self.test_data["writer_id"]]):
            return {"status": "error", "error": "Missing required test data"}
        
        try:
            # Generate episode
            generation_data = {
                "group_id": self.test_data["group_id"],
                "presenter_id": self.test_data["presenter_id"],
                "writer_id": self.test_data["writer_id"],
                "collection_id": self.test_data.get("collection_id")
            }
            
            response = await self.client.post(f"{API_GATEWAY_URL}/api/generate-episode", json=generation_data)
            if response.status_code == 200:
                result = response.json()
                episode_id = result.get("episode_id")
                self.test_data["episode_id"] = episode_id
                logger.info(f"✅ Started episode generation: {episode_id}")
                
                # Wait for generation to complete (with timeout)
                max_wait_time = 300  # 5 minutes
                wait_interval = 10   # 10 seconds
                elapsed_time = 0
                
                while elapsed_time < max_wait_time:
                    await asyncio.sleep(wait_interval)
                    elapsed_time += wait_interval
                    
                    # Check episode status
                    status_response = await self.client.get(f"{API_GATEWAY_URL}/api/episodes/{episode_id}")
                    if status_response.status_code == 200:
                        episode = status_response.json()
                        status = episode.get("status", "unknown")
                        logger.info(f"   Episode status: {status} (elapsed: {elapsed_time}s)")
                        
                        if status in ["completed", "published"]:
                            logger.info(f"✅ Episode generation completed: {status}")
                            return {
                                "status": "success",
                                "episode_id": episode_id,
                                "final_status": status,
                                "generation_time": elapsed_time
                            }
                        elif status == "failed":
                            logger.error(f"❌ Episode generation failed")
                            return {
                                "status": "error",
                                "error": "Episode generation failed",
                                "episode_id": episode_id
                            }
                    else:
                        logger.warning(f"⚠️  Failed to check episode status: {status_response.status_code}")
                
                # Timeout reached
                logger.warning(f"⚠️  Episode generation timeout after {max_wait_time}s")
                return {
                    "status": "timeout",
                    "episode_id": episode_id,
                    "timeout_seconds": max_wait_time
                }
            else:
                return {"status": "error", "error": f"Failed to start episode generation: {response.status_code}"}
                
        except Exception as e:
            logger.error(f"❌ Episode generation exception: {e}")
            return {"status": "error", "error": str(e)}
    
    async def test_episode_retrieval_and_playback(self) -> Dict:
        """Test episode retrieval and playback functionality."""
        logger.info("🔍 Testing Episode Retrieval and Playback...")
        
        if not self.test_data["episode_id"]:
            return {"status": "error", "error": "No episode ID available"}
        
        try:
            # Get episode details
            response = await self.client.get(f"{API_GATEWAY_URL}/api/episodes/{self.test_data['episode_id']}")
            if response.status_code == 200:
                episode = response.json()
                logger.info(f"✅ Retrieved episode: {episode.get('title', 'Untitled')}")
                logger.info(f"   Status: {episode.get('status', 'unknown')}")
                logger.info(f"   Duration: {episode.get('duration', 0)} minutes")
                
                # Check if audio file exists
                audio_url = episode.get("audio_url")
                if audio_url:
                    # Test audio file accessibility
                    audio_response = await self.client.head(audio_url)
                    if audio_response.status_code == 200:
                        logger.info(f"✅ Audio file accessible: {audio_url}")
                        return {
                            "status": "success",
                            "episode": episode,
                            "audio_accessible": True
                        }
                    else:
                        logger.warning(f"⚠️  Audio file not accessible: {audio_response.status_code}")
                        return {
                            "status": "partial",
                            "episode": episode,
                            "audio_accessible": False
                        }
                else:
                    logger.warning(f"⚠️  No audio URL found")
                    return {
                        "status": "partial",
                        "episode": episode,
                        "audio_accessible": False
                    }
            else:
                return {"status": "error", "error": f"Failed to retrieve episode: {response.status_code}"}
                
        except Exception as e:
            logger.error(f"❌ Episode retrieval exception: {e}")
            return {"status": "error", "error": str(e)}
    
    async def test_dashboard_functionality(self) -> Dict:
        """Test dashboard functionality."""
        logger.info("🔍 Testing Dashboard Functionality...")
        
        dashboard_tests = {}
        
        # Test main dashboard
        try:
            response = await self.client.get(f"{API_GATEWAY_URL}/")
            if response.status_code == 200:
                dashboard_tests['main_dashboard'] = {"status": "success"}
                logger.info(f"✅ Main dashboard accessible")
            else:
                dashboard_tests['main_dashboard'] = {"status": "error", "error": f"HTTP {response.status_code}"}
        except Exception as e:
            dashboard_tests['main_dashboard'] = {"status": "error", "error": str(e)}
        
        # Test groups management
        try:
            response = await self.client.get(f"{API_GATEWAY_URL}/groups")
            if response.status_code == 200:
                dashboard_tests['groups_management'] = {"status": "success"}
                logger.info(f"✅ Groups management accessible")
            else:
                dashboard_tests['groups_management'] = {"status": "error", "error": f"HTTP {response.status_code}"}
        except Exception as e:
            dashboard_tests['groups_management'] = {"status": "error", "error": str(e)}
        
        # Test reviewer dashboard
        try:
            response = await self.client.get(f"{API_GATEWAY_URL}/reviewer")
            if response.status_code == 200:
                dashboard_tests['reviewer_dashboard'] = {"status": "success"}
                logger.info(f"✅ Reviewer dashboard accessible")
            else:
                dashboard_tests['reviewer_dashboard'] = {"status": "error", "error": f"HTTP {response.status_code}"}
        except Exception as e:
            dashboard_tests['reviewer_dashboard'] = {"status": "error", "error": str(e)}
        
        # Test presenter management
        try:
            response = await self.client.get(f"{API_GATEWAY_URL}/presenters")
            if response.status_code == 200:
                dashboard_tests['presenter_management'] = {"status": "success"}
                logger.info(f"✅ Presenter management accessible")
            else:
                dashboard_tests['presenter_management'] = {"status": "error", "error": f"HTTP {response.status_code}"}
        except Exception as e:
            dashboard_tests['presenter_management'] = {"status": "error", "error": str(e)}
        
        return dashboard_tests
    
    async def cleanup_test_data(self) -> Dict:
        """Clean up test data."""
        logger.info("🧹 Cleaning up test data...")
        
        cleanup_results = {}
        
        # Delete test episode
        if self.test_data["episode_id"]:
            try:
                response = await self.client.delete(f"{API_GATEWAY_URL}/api/episodes/{self.test_data['episode_id']}")
                if response.status_code == 200:
                    cleanup_results['episode'] = {"status": "success"}
                    logger.info(f"✅ Deleted test episode: {self.test_data['episode_id']}")
                else:
                    cleanup_results['episode'] = {"status": "warning", "error": f"HTTP {response.status_code}"}
            except Exception as e:
                cleanup_results['episode'] = {"status": "warning", "error": str(e)}
        
        # Delete test collection
        if self.test_data["collection_id"]:
            try:
                response = await self.client.delete(f"{COLLECTIONS_URL}/collections/{self.test_data['collection_id']}")
                if response.status_code == 200:
                    cleanup_results['collection'] = {"status": "success"}
                    logger.info(f"✅ Deleted test collection: {self.test_data['collection_id']}")
                else:
                    cleanup_results['collection'] = {"status": "warning", "error": f"HTTP {response.status_code}"}
            except Exception as e:
                cleanup_results['collection'] = {"status": "warning", "error": str(e)}
        
        # Delete test presenter
        if self.test_data["presenter_id"]:
            try:
                response = await self.client.delete(f"{API_GATEWAY_URL}/api/presenters/{self.test_data['presenter_id']}")
                if response.status_code == 200:
                    cleanup_results['presenter'] = {"status": "success"}
                    logger.info(f"✅ Deleted test presenter: {self.test_data['presenter_id']}")
                else:
                    cleanup_results['presenter'] = {"status": "warning", "error": f"HTTP {response.status_code}"}
            except Exception as e:
                cleanup_results['presenter'] = {"status": "warning", "error": str(e)}
        
        # Delete test writer
        if self.test_data["writer_id"]:
            try:
                response = await self.client.delete(f"{API_GATEWAY_URL}/api/writers/{self.test_data['writer_id']}")
                if response.status_code == 200:
                    cleanup_results['writer'] = {"status": "success"}
                    logger.info(f"✅ Deleted test writer: {self.test_data['writer_id']}")
                else:
                    cleanup_results['writer'] = {"status": "warning", "error": f"HTTP {response.status_code}"}
            except Exception as e:
                cleanup_results['writer'] = {"status": "warning", "error": str(e)}
        
        # Delete test podcast group
        if self.test_data["group_id"]:
            try:
                response = await self.client.delete(f"{API_GATEWAY_URL}/api/podcast-groups/{self.test_data['group_id']}")
                if response.status_code == 200:
                    cleanup_results['podcast_group'] = {"status": "success"}
                    logger.info(f"✅ Deleted test podcast group: {self.test_data['group_id']}")
                else:
                    cleanup_results['podcast_group'] = {"status": "warning", "error": f"HTTP {response.status_code}"}
            except Exception as e:
                cleanup_results['podcast_group'] = {"status": "warning", "error": str(e)}
        
        return cleanup_results
    
    async def run_full_workflow_test(self) -> Dict:
        """Run the complete workflow test."""
        logger.info("🚀 Starting Full Workflow Test...")
        
        results = {}
        
        # Setup test data
        results['setup'] = await self.setup_test_data()
        
        # Test news feed processing
        results['news_processing'] = await self.test_news_feed_processing()
        
        # Test collection management
        results['collection_management'] = await self.test_collection_creation_and_management()
        
        # Test episode generation
        results['episode_generation'] = await self.test_episode_generation()
        
        # Test episode retrieval
        results['episode_retrieval'] = await self.test_episode_retrieval_and_playback()
        
        # Test dashboard functionality
        results['dashboard'] = await self.test_dashboard_functionality()
        
        # Cleanup
        results['cleanup'] = await self.cleanup_test_data()
        
        return results
    
    def generate_report(self, results: Dict) -> str:
        """Generate a comprehensive workflow test report."""
        report = []
        report.append("=" * 80)
        report.append("FULL WORKFLOW TEST REPORT")
        report.append("=" * 80)
        report.append(f"Generated: {datetime.utcnow().isoformat()}")
        report.append("")
        
        # Test Summary
        total_tests = len(results)
        successful_tests = sum(1 for r in results.values() if r.get('status') == 'success')
        
        report.append("WORKFLOW TEST SUMMARY")
        report.append("-" * 40)
        report.append(f"Total Test Phases: {total_tests}")
        report.append(f"Successful Phases: {successful_tests}")
        report.append(f"Failed Phases: {total_tests - successful_tests}")
        report.append("")
        
        # Individual Test Results
        for test_name, result in results.items():
            if test_name == 'dashboard':
                # Special handling for dashboard test
                report.append(f"DASHBOARD FUNCTIONALITY TEST")
                report.append("-" * 30)
                for sub_test, sub_result in result.items():
                    status_icon = "✅" if sub_result.get('status') == 'success' else "❌"
                    report.append(f"{status_icon} {sub_test}: {sub_result.get('status', 'unknown')}")
                    if 'error' in sub_result:
                        report.append(f"   Error: {sub_result['error']}")
                report.append("")
            elif test_name == 'cleanup':
                # Special handling for cleanup test
                report.append(f"CLEANUP TEST")
                report.append("-" * 30)
                for sub_test, sub_result in result.items():
                    status_icon = "✅" if sub_result.get('status') == 'success' else "⚠️"
                    report.append(f"{status_icon} {sub_test}: {sub_result.get('status', 'unknown')}")
                    if 'error' in sub_result:
                        report.append(f"   Note: {sub_result['error']}")
                report.append("")
            else:
                # Standard test result
                status_icon = "✅" if result.get('status') == 'success' else "❌"
                report.append(f"{status_icon} {test_name.upper()}: {result.get('status', 'unknown')}")
                
                if 'error' in result:
                    report.append(f"   Error: {result['error']}")
                
                if 'generation_time' in result:
                    report.append(f"   Generation Time: {result['generation_time']}s")
                
                if 'episode_id' in result:
                    report.append(f"   Episode ID: {result['episode_id']}")
                
                if 'collection_id' in result:
                    report.append(f"   Collection ID: {result['collection_id']}")
                
                report.append("")
        
        return "\n".join(report)
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


async def main():
    """Main test function."""
    tester = FullWorkflowTester()
    
    try:
        results = await tester.run_full_workflow_test()
        
        # Generate and print report
        report = tester.generate_report(results)
        print(report)
        
        # Overall status
        total_tests = len(results)
        successful_tests = sum(1 for r in results.values() if r.get('status') == 'success')
        
        if successful_tests == total_tests:
            print(f"\n🎉 FULL WORKFLOW TEST PASSED! ({successful_tests}/{total_tests} phases successful)")
            return 0
        else:
            print(f"\n⚠️  FULL WORKFLOW TEST HAD ISSUES! ({successful_tests}/{total_tests} phases successful)")
            return 1
            
    except Exception as e:
        logger.error(f"Full workflow test suite failed: {e}")
        return 1
    finally:
        await tester.close()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
