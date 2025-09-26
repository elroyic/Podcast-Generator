#!/usr/bin/env python3
"""
Collections Service Tests - Test feed grouping and collection management.
"""
import asyncio
import httpx
import pytest
import logging
from typing import Dict, List
from datetime import datetime
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Service URLs
COLLECTIONS_URL = "http://localhost:8011"
REVIEWER_URL = "http://localhost:8009"


class CollectionsServiceTester:
    """Test the collections service functionality."""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=60.0)
        self.test_results = {}
        self.test_collection_id = None
    
    async def test_collections_health(self) -> Dict:
        """Test collections service health."""
        logger.info("🔍 Testing Collections Service Health...")
        
        try:
            response = await self.client.get(f"{COLLECTIONS_URL}/health")
            
            if response.status_code == 200:
                health_data = response.json()
                logger.info(f"✅ Collections Health: OK")
                logger.info(f"   Collections Count: {health_data.get('collections_count', 0)}")
                
                return {
                    "status": "success",
                    "health_data": health_data
                }
            else:
                logger.error(f"❌ Collections Health: Error {response.status_code}")
                return {
                    "status": "error",
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
                
        except Exception as e:
            logger.error(f"❌ Collections Health: Exception - {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def test_create_collection(self) -> Dict:
        """Test creating a new collection."""
        logger.info("🔍 Testing Collection Creation...")
        
        collection_data = {
            "group_id": "test-group-001",
            "priority_tags": ["technology", "ai"],
            "max_items": 10
        }
        
        try:
            response = await self.client.post(f"{COLLECTIONS_URL}/collections", json=collection_data)
            
            if response.status_code == 200:
                result = response.json()
                collection = result.get('collection', {})
                self.test_collection_id = collection.get('collection_id')
                
                logger.info(f"✅ Collection Created: {self.test_collection_id}")
                logger.info(f"   Group ID: {collection.get('group_id')}")
                logger.info(f"   Status: {collection.get('status')}")
                logger.info(f"   Priority Tags: {collection.get('metadata', {}).get('priority_tags', [])}")
                
                return {
                    "status": "success",
                    "collection_id": self.test_collection_id,
                    "collection": collection
                }
            else:
                logger.error(f"❌ Collection Creation: Error {response.status_code}")
                return {
                    "status": "error",
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
                
        except Exception as e:
            logger.error(f"❌ Collection Creation: Exception - {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def test_get_collection(self) -> Dict:
        """Test retrieving a collection."""
        logger.info("🔍 Testing Collection Retrieval...")
        
        if not self.test_collection_id:
            return {
                "status": "error",
                "error": "No test collection ID available"
            }
        
        try:
            response = await self.client.get(f"{COLLECTIONS_URL}/collections/{self.test_collection_id}")
            
            if response.status_code == 200:
                collection = response.json()
                logger.info(f"✅ Collection Retrieved: {self.test_collection_id}")
                logger.info(f"   Items Count: {len(collection.get('items', []))}")
                logger.info(f"   Status: {collection.get('status')}")
                
                return {
                    "status": "success",
                    "collection": collection
                }
            else:
                logger.error(f"❌ Collection Retrieval: Error {response.status_code}")
                return {
                    "status": "error",
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
                
        except Exception as e:
            logger.error(f"❌ Collection Retrieval: Exception - {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def test_list_collections(self) -> Dict:
        """Test listing collections."""
        logger.info("🔍 Testing Collection Listing...")
        
        try:
            response = await self.client.get(f"{COLLECTIONS_URL}/collections")
            
            if response.status_code == 200:
                collections = response.json()
                logger.info(f"✅ Collections Listed: {len(collections)} collections found")
                
                for collection in collections[:3]:  # Show first 3
                    logger.info(f"   - {collection.get('collection_id', 'unknown')}: {collection.get('status', 'unknown')}")
                
                return {
                    "status": "success",
                    "collections": collections,
                    "count": len(collections)
                }
            else:
                logger.error(f"❌ Collection Listing: Error {response.status_code}")
                return {
                    "status": "error",
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
                
        except Exception as e:
            logger.error(f"❌ Collection Listing: Exception - {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def test_ready_collections(self) -> Dict:
        """Test getting ready collections."""
        logger.info("🔍 Testing Ready Collections...")
        
        try:
            response = await self.client.get(f"{COLLECTIONS_URL}/collections/ready")
            
            if response.status_code == 200:
                ready_collections = response.json()
                logger.info(f"✅ Ready Collections: {len(ready_collections)} ready collections found")
                
                for collection in ready_collections:
                    feed_count = sum(1 for item in collection.get('items', []) if item.get('item_type') == 'feed')
                    logger.info(f"   - {collection.get('collection_id', 'unknown')}: {feed_count} feeds")
                
                return {
                    "status": "success",
                    "ready_collections": ready_collections,
                    "count": len(ready_collections)
                }
            else:
                logger.error(f"❌ Ready Collections: Error {response.status_code}")
                return {
                    "status": "error",
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
                
        except Exception as e:
            logger.error(f"❌ Ready Collections: Exception - {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def test_collection_stats(self) -> Dict:
        """Test collection statistics."""
        logger.info("🔍 Testing Collection Statistics...")
        
        try:
            response = await self.client.get(f"{COLLECTIONS_URL}/collections/stats")
            
            if response.status_code == 200:
                stats = response.json()
                logger.info(f"✅ Collection Stats: OK")
                logger.info(f"   Total Collections: {stats.get('total_collections', 0)}")
                logger.info(f"   Status Counts: {stats.get('status_counts', {})}")
                logger.info(f"   Min Feeds Required: {stats.get('min_feeds_required', 0)}")
                logger.info(f"   Collection TTL: {stats.get('collection_ttl_hours', 0)} hours")
                
                return {
                    "status": "success",
                    "stats": stats
                }
            else:
                logger.error(f"❌ Collection Stats: Error {response.status_code}")
                return {
                    "status": "error",
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
                
        except Exception as e:
            logger.error(f"❌ Collection Stats: Exception - {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def test_collection_lifecycle(self) -> Dict:
        """Test complete collection lifecycle."""
        logger.info("🔍 Testing Collection Lifecycle...")
        
        if not self.test_collection_id:
            return {
                "status": "error",
                "error": "No test collection ID available"
            }
        
        lifecycle_results = {}
        
        # Test marking collection as ready
        try:
            response = await self.client.post(f"{COLLECTIONS_URL}/collections/{self.test_collection_id}/ready")
            if response.status_code == 200:
                logger.info(f"✅ Collection Marked Ready: {self.test_collection_id}")
                lifecycle_results['mark_ready'] = {"status": "success"}
            else:
                logger.warning(f"⚠️  Mark Ready Failed: {response.status_code} - {response.text}")
                lifecycle_results['mark_ready'] = {"status": "warning", "error": f"HTTP {response.status_code}"}
        except Exception as e:
            logger.warning(f"⚠️  Mark Ready Exception: {e}")
            lifecycle_results['mark_ready'] = {"status": "warning", "error": str(e)}
        
        # Test marking collection as used
        try:
            response = await self.client.post(f"{COLLECTIONS_URL}/collections/{self.test_collection_id}/used")
            if response.status_code == 200:
                logger.info(f"✅ Collection Marked Used: {self.test_collection_id}")
                lifecycle_results['mark_used'] = {"status": "success"}
            else:
                logger.warning(f"⚠️  Mark Used Failed: {response.status_code} - {response.text}")
                lifecycle_results['mark_used'] = {"status": "warning", "error": f"HTTP {response.status_code}"}
        except Exception as e:
            logger.warning(f"⚠️  Mark Used Exception: {e}")
            lifecycle_results['mark_used'] = {"status": "warning", "error": str(e)}
        
        return lifecycle_results
    
    async def test_collection_cleanup(self) -> Dict:
        """Test collection cleanup functionality."""
        logger.info("🔍 Testing Collection Cleanup...")
        
        try:
            response = await self.client.post(f"{COLLECTIONS_URL}/collections/cleanup")
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"✅ Collection Cleanup: {result.get('message', 'OK')}")
                
                return {
                    "status": "success",
                    "message": result.get('message', 'Cleanup completed')
                }
            else:
                logger.error(f"❌ Collection Cleanup: Error {response.status_code}")
                return {
                    "status": "error",
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
                
        except Exception as e:
            logger.error(f"❌ Collection Cleanup: Exception - {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def test_collection_deletion(self) -> Dict:
        """Test collection deletion."""
        logger.info("🔍 Testing Collection Deletion...")
        
        if not self.test_collection_id:
            return {
                "status": "error",
                "error": "No test collection ID available"
            }
        
        try:
            response = await self.client.delete(f"{COLLECTIONS_URL}/collections/{self.test_collection_id}")
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"✅ Collection Deleted: {self.test_collection_id}")
                logger.info(f"   Message: {result.get('message', 'OK')}")
                
                return {
                    "status": "success",
                    "message": result.get('message', 'Collection deleted')
                }
            else:
                logger.error(f"❌ Collection Deletion: Error {response.status_code}")
                return {
                    "status": "error",
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
                
        except Exception as e:
            logger.error(f"❌ Collection Deletion: Exception - {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def run_all_tests(self) -> Dict:
        """Run all collections service tests."""
        logger.info("🚀 Starting Collections Service Tests...")
        
        results = {}
        
        # Test service health
        results['health'] = await self.test_collections_health()
        
        # Test collection operations
        results['create'] = await self.test_create_collection()
        results['get'] = await self.test_get_collection()
        results['list'] = await self.test_list_collections()
        results['ready'] = await self.test_ready_collections()
        results['stats'] = await self.test_collection_stats()
        
        # Test lifecycle
        results['lifecycle'] = await self.test_collection_lifecycle()
        
        # Test cleanup and deletion
        results['cleanup'] = await self.test_collection_cleanup()
        results['delete'] = await self.test_collection_deletion()
        
        return results
    
    def generate_report(self, results: Dict) -> str:
        """Generate a comprehensive test report."""
        report = []
        report.append("=" * 80)
        report.append("COLLECTIONS SERVICE TEST REPORT")
        report.append("=" * 80)
        report.append(f"Generated: {datetime.utcnow().isoformat()}")
        report.append("")
        
        # Test Summary
        total_tests = len(results)
        passed_tests = sum(1 for r in results.values() if r.get('status') == 'success')
        
        report.append("TEST SUMMARY")
        report.append("-" * 40)
        report.append(f"Total Tests: {total_tests}")
        report.append(f"Passed: {passed_tests}")
        report.append(f"Failed: {total_tests - passed_tests}")
        report.append("")
        
        # Individual Test Results
        for test_name, result in results.items():
            if test_name == 'lifecycle':
                # Special handling for lifecycle test
                report.append(f"COLLECTION LIFECYCLE TEST")
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
                
                if 'count' in result:
                    report.append(f"   Count: {result['count']}")
                
                if 'message' in result:
                    report.append(f"   Message: {result['message']}")
                
                report.append("")
        
        return "\n".join(report)
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


async def main():
    """Main test function."""
    tester = CollectionsServiceTester()
    
    try:
        results = await tester.run_all_tests()
        
        # Generate and print report
        report = tester.generate_report(results)
        print(report)
        
        # Overall status
        total_tests = len(results)
        passed_tests = sum(1 for r in results.values() if r.get('status') == 'success')
        
        if passed_tests == total_tests:
            print(f"\n🎉 ALL COLLECTIONS TESTS PASSED! ({passed_tests}/{total_tests})")
            return 0
        else:
            print(f"\n⚠️  SOME COLLECTIONS TESTS FAILED! ({passed_tests}/{total_tests})")
            return 1
            
    except Exception as e:
        logger.error(f"Collections test suite failed: {e}")
        return 1
    finally:
        await tester.close()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
