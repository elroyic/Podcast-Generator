#!/usr/bin/env python3
"""
Complete Workflow Test - Tests the entire podcast generation pipeline.
This script verifies that all components work together to generate a 10-minute podcast.
"""
import asyncio
import httpx
import logging
import json
from datetime import datetime
from typing import Dict, Any, List
from uuid import UUID, uuid4

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Service URLs
SERVICES = {
    "news_feed": "http://localhost:8001",
    "reviewer": "http://localhost:8007", 
    "presenter": "http://localhost:8008",
    "writer": "http://localhost:8010",
    "editor": "http://localhost:8009",
    "collections": "http://localhost:8011",
    "ai_overseer": "http://localhost:8012",
    "presenter_vibevoice": "http://localhost:8013"
}


class WorkflowTester:
    """Tests the complete podcast generation workflow."""
    
    def __init__(self):
        self.http_client = httpx.AsyncClient(timeout=300.0)
        self.test_results = {}
    
    async def test_service_health(self) -> Dict[str, bool]:
        """Test health of all services."""
        logger.info("Testing service health...")
        health_status = {}
        
        for service_name, base_url in SERVICES.items():
            try:
                response = await self.http_client.get(f"{base_url}/health")
                health_status[service_name] = response.status_code == 200
                logger.info(f"✓ {service_name}: {'Healthy' if health_status[service_name] else 'Unhealthy'}")
            except Exception as e:
                health_status[service_name] = False
                logger.error(f"✗ {service_name}: {e}")
        
        return health_status
    
    async def test_rss_feeds_setup(self) -> Dict[str, Any]:
        """Test RSS feeds setup."""
        logger.info("Testing RSS feeds setup...")
        
        try:
            # Run the RSS feeds setup script
            import subprocess
            result = subprocess.run(
                ["python", "/workspace/setup_rss_feeds.py"],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            success = result.returncode == 0
            logger.info(f"RSS feeds setup: {'Success' if success else 'Failed'}")
            
            return {
                "success": success,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
            
        except Exception as e:
            logger.error(f"RSS feeds setup failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def test_reviewer_service(self) -> Dict[str, Any]:
        """Test the Reviewer service."""
        logger.info("Testing Reviewer service...")
        
        try:
            response = await self.http_client.post(
                f"{SERVICES['reviewer']}/test-review",
                json={
                    "test_title": "Apple announces new AI features for iPhone",
                    "test_summary": "Apple unveiled new artificial intelligence capabilities for its latest iPhone models.",
                    "test_content": "Apple Inc. today announced significant updates to its iPhone lineup, focusing heavily on artificial intelligence integration."
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info("✓ Reviewer service test passed")
                return {"success": True, "result": result}
            else:
                logger.error(f"✗ Reviewer service test failed: {response.status_code}")
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            logger.error(f"✗ Reviewer service test failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def test_presenter_service(self) -> Dict[str, Any]:
        """Test the Presenter service."""
        logger.info("Testing Presenter service...")
        
        try:
            response = await self.http_client.post(
                f"{SERVICES['presenter']}/test-brief-generation",
                json={
                    "presenter_name": "Alex Chen",
                    "test_articles": [
                        {
                            "title": "Apple announces new AI features",
                            "summary": "Apple unveiled new AI capabilities for iPhone models.",
                            "source": "TechCrunch",
                            "publish_date": "2024-01-15"
                        }
                    ]
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info("✓ Presenter service test passed")
                return {"success": True, "result": result}
            else:
                logger.error(f"✗ Presenter service test failed: {response.status_code}")
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            logger.error(f"✗ Presenter service test failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def test_writer_service(self) -> Dict[str, Any]:
        """Test the Writer service."""
        logger.info("Testing Writer service...")
        
        try:
            response = await self.http_client.post(
                f"{SERVICES['writer']}/test-script-generation",
                json={
                    "test_collection_id": "test-collection-001",
                    "target_length_minutes": 10
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info("✓ Writer service test passed")
                return {"success": True, "result": result}
            else:
                logger.error(f"✗ Writer service test failed: {response.status_code}")
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            logger.error(f"✗ Writer service test failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def test_editor_service(self) -> Dict[str, Any]:
        """Test the Editor service."""
        logger.info("Testing Editor service...")
        
        try:
            response = await self.http_client.post(
                f"{SERVICES['editor']}/test-script-editing",
                json={
                    "test_script": "Welcome to today's podcast. We'll discuss the latest developments in technology and finance.",
                    "target_length_minutes": 10,
                    "target_audience": "general"
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info("✓ Editor service test passed")
                return {"success": True, "result": result}
            else:
                logger.error(f"✗ Editor service test failed: {response.status_code}")
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            logger.error(f"✗ Editor service test failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def test_collections_service(self) -> Dict[str, Any]:
        """Test the Collections service."""
        logger.info("Testing Collections service...")
        
        try:
            response = await self.http_client.post(
                f"{SERVICES['collections']}/test-collection-creation",
                json={
                    "group_name": "Test Podcast Group",
                    "collection_name": "Test Collection"
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info("✓ Collections service test passed")
                return {"success": True, "result": result}
            else:
                logger.error(f"✗ Collections service test failed: {response.status_code}")
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            logger.error(f"✗ Collections service test failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def test_vibevoice_service(self) -> Dict[str, Any]:
        """Test the VibeVoice service."""
        logger.info("Testing VibeVoice service...")
        
        try:
            response = await self.http_client.post(
                f"{SERVICES['presenter_vibevoice']}/test-vibevoice-generation",
                json={
                    "test_text": "Hello, this is a test of the VibeVoice text-to-speech system for podcast generation."
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info("✓ VibeVoice service test passed")
                return {"success": True, "result": result}
            else:
                logger.error(f"✗ VibeVoice service test failed: {response.status_code}")
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            logger.error(f"✗ VibeVoice service test failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def test_complete_workflow(self) -> Dict[str, Any]:
        """Test the complete workflow end-to-end."""
        logger.info("Testing complete workflow...")
        
        try:
            response = await self.http_client.post(
                f"{SERVICES['ai_overseer']}/test-complete-workflow",
                json={
                    "group_name": "Complete Workflow Test",
                    "target_length_minutes": 10
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info("✓ Complete workflow test passed")
                return {"success": True, "result": result}
            else:
                logger.error(f"✗ Complete workflow test failed: {response.status_code}")
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            logger.error(f"✗ Complete workflow test failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all tests and generate a comprehensive report."""
        logger.info("Starting comprehensive workflow testing...")
        
        start_time = datetime.utcnow()
        
        # Test service health
        health_status = await self.test_service_health()
        
        # Test individual services
        test_results = {
            "health_status": health_status,
            "rss_feeds_setup": await self.test_rss_feeds_setup(),
            "reviewer_service": await self.test_reviewer_service(),
            "presenter_service": await self.test_presenter_service(),
            "writer_service": await self.test_writer_service(),
            "editor_service": await self.test_editor_service(),
            "collections_service": await self.test_collections_service(),
            "vibevoice_service": await self.test_vibevoice_service(),
            "complete_workflow": await self.test_complete_workflow()
        }
        
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        # Generate summary
        total_tests = len(test_results) - 1  # Exclude health_status
        passed_tests = sum(1 for test_name, result in test_results.items() 
                          if test_name != "health_status" and result.get("success", False))
        
        summary = {
            "test_summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": total_tests - passed_tests,
                "success_rate": f"{(passed_tests / total_tests * 100):.1f}%" if total_tests > 0 else "0%",
                "duration_seconds": duration
            },
            "test_results": test_results,
            "timestamp": end_time.isoformat()
        }
        
        return summary


async def main():
    """Main test function."""
    tester = WorkflowTester()
    
    try:
        # Run all tests
        results = await tester.run_all_tests()
        
        # Print summary
        print("\n" + "="*80)
        print("COMPLETE WORKFLOW TEST RESULTS")
        print("="*80)
        
        summary = results["test_summary"]
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Passed: {summary['passed_tests']}")
        print(f"Failed: {summary['failed_tests']}")
        print(f"Success Rate: {summary['success_rate']}")
        print(f"Duration: {summary['duration_seconds']:.2f} seconds")
        
        print("\nDetailed Results:")
        print("-" * 40)
        
        for test_name, result in results["test_results"].items():
            if test_name == "health_status":
                print(f"\nService Health Status:")
                for service, healthy in result.items():
                    status = "✓ Healthy" if healthy else "✗ Unhealthy"
                    print(f"  {service}: {status}")
            else:
                status = "✓ PASSED" if result.get("success", False) else "✗ FAILED"
                print(f"{test_name}: {status}")
                if not result.get("success", False) and "error" in result:
                    print(f"  Error: {result['error']}")
        
        # Save results to file
        with open("/workspace/test_results.json", "w") as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\nDetailed results saved to: /workspace/test_results.json")
        
        # Return success if all tests passed
        if summary["passed_tests"] == summary["total_tests"]:
            print("\n🎉 ALL TESTS PASSED! The complete workflow is working correctly.")
            return True
        else:
            print(f"\n⚠️  {summary['failed_tests']} tests failed. Please check the results above.")
            return False
            
    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        print(f"\n❌ Test execution failed: {e}")
        return False
    
    finally:
        await tester.http_client.aclose()


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)