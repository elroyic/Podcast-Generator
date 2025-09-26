#!/usr/bin/env python3
"""
Performance and Load Tests - Test system performance under various loads.
"""
import asyncio
import httpx
import pytest
import logging
from typing import Dict, List
from datetime import datetime
import json
import time
import statistics

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Service URLs
API_GATEWAY_URL = "http://localhost:8000"
LIGHT_REVIEWER_URL = "http://localhost:8007"
HEAVY_REVIEWER_URL = "http://localhost:8008"
REVIEWER_URL = "http://localhost:8009"
COLLECTIONS_URL = "http://localhost:8011"


class PerformanceLoadTester:
    """Test system performance and load handling."""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=120.0)
        self.test_results = {}
    
    async def test_reviewer_performance(self, reviewer_url: str, reviewer_name: str, num_requests: int = 10) -> Dict:
        """Test reviewer performance with multiple concurrent requests."""
        logger.info(f"🔍 Testing {reviewer_name} Performance ({num_requests} requests)...")
        
        test_feed = {
            "feed_id": "perf-test",
            "title": "Performance test article for load testing",
            "url": "https://example.com/performance-test",
            "content": "This is a performance test article designed to test the reviewer's ability to handle multiple concurrent requests. It contains various topics including technology, finance, and general news to provide a realistic test scenario.",
            "published": "2025-01-26T12:00:00Z"
        }
        
        async def single_request():
            start_time = time.time()
            try:
                response = await self.client.post(f"{reviewer_url}/review", json=test_feed)
                end_time = time.time()
                
                if response.status_code == 200:
                    result = response.json()
                    return {
                        "success": True,
                        "response_time": (end_time - start_time) * 1000,  # Convert to ms
                        "confidence": result.get("confidence", 0),
                        "tags_count": len(result.get("tags", []))
                    }
                else:
                    return {
                        "success": False,
                        "response_time": (end_time - start_time) * 1000,
                        "error": f"HTTP {response.status_code}"
                    }
            except Exception as e:
                end_time = time.time()
                return {
                    "success": False,
                    "response_time": (end_time - start_time) * 1000,
                    "error": str(e)
                }
        
        # Run concurrent requests
        start_time = time.time()
        tasks = [single_request() for _ in range(num_requests)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        
        # Process results
        successful_requests = [r for r in results if isinstance(r, dict) and r.get("success")]
        failed_requests = [r for r in results if isinstance(r, dict) and not r.get("success")]
        
        if successful_requests:
            response_times = [r["response_time"] for r in successful_requests]
            confidences = [r["confidence"] for r in successful_requests]
            
            stats = {
                "total_requests": num_requests,
                "successful_requests": len(successful_requests),
                "failed_requests": len(failed_requests),
                "success_rate": len(successful_requests) / num_requests * 100,
                "total_time": (end_time - start_time) * 1000,
                "avg_response_time": statistics.mean(response_times),
                "min_response_time": min(response_times),
                "max_response_time": max(response_times),
                "median_response_time": statistics.median(response_times),
                "avg_confidence": statistics.mean(confidences) if confidences else 0,
                "requests_per_second": len(successful_requests) / ((end_time - start_time))
            }
            
            logger.info(f"✅ {reviewer_name} Performance Results:")
            logger.info(f"   Success Rate: {stats['success_rate']:.1f}%")
            logger.info(f"   Avg Response Time: {stats['avg_response_time']:.1f}ms")
            logger.info(f"   Requests/Second: {stats['requests_per_second']:.2f}")
            logger.info(f"   Avg Confidence: {stats['avg_confidence']:.2f}")
            
            return {
                "status": "success",
                "stats": stats,
                "failed_requests": failed_requests
            }
        else:
            logger.error(f"❌ {reviewer_name} Performance Test Failed: All requests failed")
            return {
                "status": "error",
                "error": "All requests failed",
                "failed_requests": failed_requests
            }
    
    async def test_api_gateway_load(self, num_requests: int = 20) -> Dict:
        """Test API Gateway under load."""
        logger.info(f"🔍 Testing API Gateway Load ({num_requests} requests)...")
        
        endpoints = [
            "/health",
            "/api/podcast-groups",
            "/api/presenters",
            "/api/news-feeds",
            "/api/reviewer/config"
        ]
        
        async def single_request(endpoint: str):
            start_time = time.time()
            try:
                response = await self.client.get(f"{API_GATEWAY_URL}{endpoint}")
                end_time = time.time()
                
                return {
                    "endpoint": endpoint,
                    "success": response.status_code == 200,
                    "response_time": (end_time - start_time) * 1000,
                    "status_code": response.status_code
                }
            except Exception as e:
                end_time = time.time()
                return {
                    "endpoint": endpoint,
                    "success": False,
                    "response_time": (end_time - start_time) * 1000,
                    "error": str(e)
                }
        
        # Run concurrent requests across different endpoints
        start_time = time.time()
        tasks = []
        for _ in range(num_requests):
            endpoint = endpoints[_ % len(endpoints)]
            tasks.append(single_request(endpoint))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        
        # Process results
        successful_requests = [r for r in results if isinstance(r, dict) and r.get("success")]
        failed_requests = [r for r in results if isinstance(r, dict) and not r.get("success")]
        
        if successful_requests:
            response_times = [r["response_time"] for r in successful_requests]
            
            stats = {
                "total_requests": num_requests,
                "successful_requests": len(successful_requests),
                "failed_requests": len(failed_requests),
                "success_rate": len(successful_requests) / num_requests * 100,
                "total_time": (end_time - start_time) * 1000,
                "avg_response_time": statistics.mean(response_times),
                "min_response_time": min(response_times),
                "max_response_time": max(response_times),
                "median_response_time": statistics.median(response_times),
                "requests_per_second": len(successful_requests) / ((end_time - start_time))
            }
            
            logger.info(f"✅ API Gateway Load Test Results:")
            logger.info(f"   Success Rate: {stats['success_rate']:.1f}%")
            logger.info(f"   Avg Response Time: {stats['avg_response_time']:.1f}ms")
            logger.info(f"   Requests/Second: {stats['requests_per_second']:.2f}")
            
            return {
                "status": "success",
                "stats": stats,
                "failed_requests": failed_requests
            }
        else:
            logger.error(f"❌ API Gateway Load Test Failed: All requests failed")
            return {
                "status": "error",
                "error": "All requests failed",
                "failed_requests": failed_requests
            }
    
    async def test_collections_service_load(self, num_requests: int = 15) -> Dict:
        """Test Collections service under load."""
        logger.info(f"🔍 Testing Collections Service Load ({num_requests} requests)...")
        
        async def single_request():
            start_time = time.time()
            try:
                # Test different endpoints
                endpoints = [
                    "/health",
                    "/collections",
                    "/collections/stats",
                    "/collections/ready"
                ]
                endpoint = endpoints[_ % len(endpoints)]
                
                response = await self.client.get(f"{COLLECTIONS_URL}{endpoint}")
                end_time = time.time()
                
                return {
                    "endpoint": endpoint,
                    "success": response.status_code == 200,
                    "response_time": (end_time - start_time) * 1000,
                    "status_code": response.status_code
                }
            except Exception as e:
                end_time = time.time()
                return {
                    "success": False,
                    "response_time": (end_time - start_time) * 1000,
                    "error": str(e)
                }
        
        # Run concurrent requests
        start_time = time.time()
        tasks = [single_request() for _ in range(num_requests)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        
        # Process results
        successful_requests = [r for r in results if isinstance(r, dict) and r.get("success")]
        failed_requests = [r for r in results if isinstance(r, dict) and not r.get("success")]
        
        if successful_requests:
            response_times = [r["response_time"] for r in successful_requests]
            
            stats = {
                "total_requests": num_requests,
                "successful_requests": len(successful_requests),
                "failed_requests": len(failed_requests),
                "success_rate": len(successful_requests) / num_requests * 100,
                "total_time": (end_time - start_time) * 1000,
                "avg_response_time": statistics.mean(response_times),
                "min_response_time": min(response_times),
                "max_response_time": max(response_times),
                "median_response_time": statistics.median(response_times),
                "requests_per_second": len(successful_requests) / ((end_time - start_time))
            }
            
            logger.info(f"✅ Collections Service Load Test Results:")
            logger.info(f"   Success Rate: {stats['success_rate']:.1f}%")
            logger.info(f"   Avg Response Time: {stats['avg_response_time']:.1f}ms")
            logger.info(f"   Requests/Second: {stats['requests_per_second']:.2f}")
            
            return {
                "status": "success",
                "stats": stats,
                "failed_requests": failed_requests
            }
        else:
            logger.error(f"❌ Collections Service Load Test Failed: All requests failed")
            return {
                "status": "error",
                "error": "All requests failed",
                "failed_requests": failed_requests
            }
    
    async def test_memory_usage(self) -> Dict:
        """Test memory usage patterns."""
        logger.info("🔍 Testing Memory Usage Patterns...")
        
        # This is a simplified test - in a real scenario, you'd use system monitoring tools
        try:
            # Test creating multiple collections to see memory impact
            collection_data = {
                "group_id": "memory-test-group",
                "priority_tags": ["test"],
                "max_items": 50
            }
            
            collections_created = []
            start_time = time.time()
            
            # Create multiple collections
            for i in range(10):
                response = await self.client.post(f"{COLLECTIONS_URL}/collections", json=collection_data)
                if response.status_code == 200:
                    result = response.json()
                    collections_created.append(result.get('collection', {}).get('collection_id'))
                else:
                    logger.warning(f"Failed to create collection {i}: {response.status_code}")
            
            end_time = time.time()
            
            # Clean up collections
            for collection_id in collections_created:
                try:
                    await self.client.delete(f"{COLLECTIONS_URL}/collections/{collection_id}")
                except Exception as e:
                    logger.warning(f"Failed to delete collection {collection_id}: {e}")
            
            logger.info(f"✅ Memory Usage Test: Created and cleaned up {len(collections_created)} collections")
            
            return {
                "status": "success",
                "collections_created": len(collections_created),
                "creation_time": (end_time - start_time) * 1000
            }
            
        except Exception as e:
            logger.error(f"❌ Memory Usage Test Failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def test_concurrent_workflows(self, num_workflows: int = 5) -> Dict:
        """Test concurrent workflow execution."""
        logger.info(f"🔍 Testing Concurrent Workflows ({num_workflows} workflows)...")
        
        async def single_workflow(workflow_id: int):
            """Simulate a single workflow."""
            start_time = time.time()
            try:
                # Create a test collection
                collection_data = {
                    "group_id": f"concurrent-test-group-{workflow_id}",
                    "priority_tags": ["concurrent", "test"],
                    "max_items": 10
                }
                
                response = await self.client.post(f"{COLLECTIONS_URL}/collections", json=collection_data)
                if response.status_code == 200:
                    result = response.json()
                    collection_id = result.get('collection', {}).get('collection_id')
                    
                    # Get collection stats
                    stats_response = await self.client.get(f"{COLLECTIONS_URL}/collections/stats")
                    
                    # Clean up
                    await self.client.delete(f"{COLLECTIONS_URL}/collections/{collection_id}")
                    
                    end_time = time.time()
                    return {
                        "workflow_id": workflow_id,
                        "success": True,
                        "duration": (end_time - start_time) * 1000
                    }
                else:
                    end_time = time.time()
                    return {
                        "workflow_id": workflow_id,
                        "success": False,
                        "duration": (end_time - start_time) * 1000,
                        "error": f"HTTP {response.status_code}"
                    }
            except Exception as e:
                end_time = time.time()
                return {
                    "workflow_id": workflow_id,
                    "success": False,
                    "duration": (end_time - start_time) * 1000,
                    "error": str(e)
                }
        
        # Run concurrent workflows
        start_time = time.time()
        tasks = [single_workflow(i) for i in range(num_workflows)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        
        # Process results
        successful_workflows = [r for r in results if isinstance(r, dict) and r.get("success")]
        failed_workflows = [r for r in results if isinstance(r, dict) and not r.get("success")]
        
        if successful_workflows:
            durations = [r["duration"] for r in successful_workflows]
            
            stats = {
                "total_workflows": num_workflows,
                "successful_workflows": len(successful_workflows),
                "failed_workflows": len(failed_workflows),
                "success_rate": len(successful_workflows) / num_workflows * 100,
                "total_time": (end_time - start_time) * 1000,
                "avg_duration": statistics.mean(durations),
                "min_duration": min(durations),
                "max_duration": max(durations),
                "median_duration": statistics.median(durations)
            }
            
            logger.info(f"✅ Concurrent Workflows Test Results:")
            logger.info(f"   Success Rate: {stats['success_rate']:.1f}%")
            logger.info(f"   Avg Duration: {stats['avg_duration']:.1f}ms")
            logger.info(f"   Total Time: {stats['total_time']:.1f}ms")
            
            return {
                "status": "success",
                "stats": stats,
                "failed_workflows": failed_workflows
            }
        else:
            logger.error(f"❌ Concurrent Workflows Test Failed: All workflows failed")
            return {
                "status": "error",
                "error": "All workflows failed",
                "failed_workflows": failed_workflows
            }
    
    async def run_all_performance_tests(self) -> Dict:
        """Run all performance and load tests."""
        logger.info("🚀 Starting Performance and Load Tests...")
        
        results = {}
        
        # Test reviewer performance
        results['light_reviewer_performance'] = await self.test_reviewer_performance(
            LIGHT_REVIEWER_URL, "Light Reviewer", 15
        )
        results['heavy_reviewer_performance'] = await self.test_reviewer_performance(
            HEAVY_REVIEWER_URL, "Heavy Reviewer", 8
        )
        
        # Test API Gateway load
        results['api_gateway_load'] = await self.test_api_gateway_load(25)
        
        # Test Collections service load
        results['collections_load'] = await self.test_collections_service_load(20)
        
        # Test memory usage
        results['memory_usage'] = await self.test_memory_usage()
        
        # Test concurrent workflows
        results['concurrent_workflows'] = await self.test_concurrent_workflows(8)
        
        return results
    
    def generate_report(self, results: Dict) -> str:
        """Generate a comprehensive performance test report."""
        report = []
        report.append("=" * 80)
        report.append("PERFORMANCE AND LOAD TEST REPORT")
        report.append("=" * 80)
        report.append(f"Generated: {datetime.utcnow().isoformat()}")
        report.append("")
        
        # Test Summary
        total_tests = len(results)
        successful_tests = sum(1 for r in results.values() if r.get('status') == 'success')
        
        report.append("PERFORMANCE TEST SUMMARY")
        report.append("-" * 40)
        report.append(f"Total Tests: {total_tests}")
        report.append(f"Successful Tests: {successful_tests}")
        report.append(f"Failed Tests: {total_tests - successful_tests}")
        report.append("")
        
        # Individual Test Results
        for test_name, result in results.items():
            status_icon = "✅" if result.get('status') == 'success' else "❌"
            report.append(f"{status_icon} {test_name.upper().replace('_', ' ')}: {result.get('status', 'unknown')}")
            
            if 'stats' in result:
                stats = result['stats']
                report.append(f"   Success Rate: {stats.get('success_rate', 0):.1f}%")
                report.append(f"   Avg Response Time: {stats.get('avg_response_time', 0):.1f}ms")
                if 'requests_per_second' in stats:
                    report.append(f"   Requests/Second: {stats['requests_per_second']:.2f}")
                if 'avg_duration' in stats:
                    report.append(f"   Avg Duration: {stats['avg_duration']:.1f}ms")
            
            if 'error' in result:
                report.append(f"   Error: {result['error']}")
            
            report.append("")
        
        # Performance Benchmarks
        report.append("PERFORMANCE BENCHMARKS")
        report.append("-" * 40)
        
        # Light Reviewer benchmarks
        light_perf = results.get('light_reviewer_performance', {})
        if light_perf.get('status') == 'success':
            light_stats = light_perf.get('stats', {})
            report.append(f"Light Reviewer:")
            report.append(f"  Target: <500ms avg response time")
            report.append(f"  Actual: {light_stats.get('avg_response_time', 0):.1f}ms")
            report.append(f"  Status: {'✅ PASS' if light_stats.get('avg_response_time', 0) < 500 else '❌ FAIL'}")
        
        # Heavy Reviewer benchmarks
        heavy_perf = results.get('heavy_reviewer_performance', {})
        if heavy_perf.get('status') == 'success':
            heavy_stats = heavy_perf.get('stats', {})
            report.append(f"Heavy Reviewer:")
            report.append(f"  Target: <2000ms avg response time")
            report.append(f"  Actual: {heavy_stats.get('avg_response_time', 0):.1f}ms")
            report.append(f"  Status: {'✅ PASS' if heavy_stats.get('avg_response_time', 0) < 2000 else '❌ FAIL'}")
        
        # API Gateway benchmarks
        api_perf = results.get('api_gateway_load', {})
        if api_perf.get('status') == 'success':
            api_stats = api_perf.get('stats', {})
            report.append(f"API Gateway:")
            report.append(f"  Target: >95% success rate")
            report.append(f"  Actual: {api_stats.get('success_rate', 0):.1f}%")
            report.append(f"  Status: {'✅ PASS' if api_stats.get('success_rate', 0) > 95 else '❌ FAIL'}")
        
        report.append("")
        
        return "\n".join(report)
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


async def main():
    """Main test function."""
    tester = PerformanceLoadTester()
    
    try:
        results = await tester.run_all_performance_tests()
        
        # Generate and print report
        report = tester.generate_report(results)
        print(report)
        
        # Overall status
        total_tests = len(results)
        successful_tests = sum(1 for r in results.values() if r.get('status') == 'success')
        
        if successful_tests == total_tests:
            print(f"\n🎉 ALL PERFORMANCE TESTS PASSED! ({successful_tests}/{total_tests})")
            return 0
        else:
            print(f"\n⚠️  SOME PERFORMANCE TESTS FAILED! ({successful_tests}/{total_tests})")
            return 1
            
    except Exception as e:
        logger.error(f"Performance test suite failed: {e}")
        return 1
    finally:
        await tester.close()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
