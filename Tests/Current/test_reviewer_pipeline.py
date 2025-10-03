#!/usr/bin/env python3
"""
Reviewer Pipeline Tests - Test the two-tier review architecture.
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
LIGHT_REVIEWER_URL = "http://localhost:8007"
HEAVY_REVIEWER_URL = "http://localhost:8008"
REVIEWER_ORCHESTRATOR_URL = "http://localhost:8009"


class ReviewerPipelineTester:
    """Test the two-tier review pipeline."""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=60.0)
        self.test_results = {}
    
    async def test_light_reviewer(self) -> Dict:
        """Test the light reviewer service."""
        logger.info("🔍 Testing Light Reviewer...")
        
        test_feed = {
            "feed_id": "test-001",
            "title": "Apple announces new AI features for iPhone",
            "url": "https://example.com/apple-ai-news",
            "content": "Apple Inc. today announced significant updates to its iPhone lineup, focusing heavily on artificial intelligence integration. The new features include improved Siri capabilities, enhanced photo processing, and on-device machine learning for better privacy and performance.",
            "published": "2025-01-26T10:00:00Z"
        }
        
        try:
            start_time = datetime.utcnow()
            response = await self.client.post(f"{LIGHT_REVIEWER_URL}/review", json=test_feed)
            end_time = datetime.utcnow()
            
            response_time = (end_time - start_time).total_seconds() * 1000
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"✅ Light Reviewer: OK ({response_time:.1f}ms)")
                logger.info(f"   Tags: {result.get('tags', [])}")
                logger.info(f"   Confidence: {result.get('confidence', 0):.2f}")
                logger.info(f"   Model: {result.get('model', 'unknown')}")
                
                return {
                    "status": "success",
                    "response_time_ms": response_time,
                    "result": result,
                    "performance_ok": response_time < 500  # Should be under 500ms
                }
            else:
                logger.error(f"❌ Light Reviewer: Error {response.status_code}")
                return {
                    "status": "error",
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
                
        except Exception as e:
            logger.error(f"❌ Light Reviewer: Exception - {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def test_heavy_reviewer(self) -> Dict:
        """Test the heavy reviewer service."""
        logger.info("🔍 Testing Heavy Reviewer...")
        
        test_feed = {
            "feed_id": "test-002",
            "title": "Federal Reserve announces interest rate changes",
            "url": "https://example.com/fed-news",
            "content": "The Federal Reserve announced today that it will maintain current interest rates while signaling potential future adjustments based on economic indicators. The decision comes amid ongoing inflation concerns and labor market dynamics.",
            "published": "2025-01-26T14:30:00Z"
        }
        
        try:
            start_time = datetime.utcnow()
            response = await self.client.post(f"{HEAVY_REVIEWER_URL}/review", json=test_feed)
            end_time = datetime.utcnow()
            
            response_time = (end_time - start_time).total_seconds() * 1000
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"✅ Heavy Reviewer: OK ({response_time:.1f}ms)")
                logger.info(f"   Tags: {result.get('tags', [])}")
                logger.info(f"   Confidence: {result.get('confidence', 0):.2f}")
                logger.info(f"   Model: {result.get('model', 'unknown')}")
                
                return {
                    "status": "success",
                    "response_time_ms": response_time,
                    "result": result,
                    "performance_ok": response_time < 2000  # Should be under 2s
                }
            else:
                logger.error(f"❌ Heavy Reviewer: Error {response.status_code}")
                return {
                    "status": "error",
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
                
        except Exception as e:
            logger.error(f"❌ Heavy Reviewer: Exception - {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def test_reviewer_orchestrator(self) -> Dict:
        """Test the reviewer orchestrator service."""
        logger.info("🔍 Testing Reviewer Orchestrator...")
        
        # Test configuration endpoint
        try:
            config_response = await self.client.get(f"{REVIEWER_ORCHESTRATOR_URL}/config")
            if config_response.status_code == 200:
                config = config_response.json()
                logger.info(f"✅ Reviewer Config: OK")
                logger.info(f"   Confidence Threshold: {config.get('conf_threshold', 0):.2f}")
                logger.info(f"   Heavy Enabled: {config.get('heavy_enabled', False)}")
                logger.info(f"   Light Model: {config.get('light_model', 'unknown')}")
                logger.info(f"   Heavy Model: {config.get('heavy_model', 'unknown')}")
            else:
                logger.error(f"❌ Reviewer Config: Error {config_response.status_code}")
                return {
                    "status": "error",
                    "error": f"Config endpoint failed: {config_response.status_code}"
                }
        except Exception as e:
            logger.error(f"❌ Reviewer Config: Exception - {e}")
            return {
                "status": "error",
                "error": str(e)
            }
        
        # Test metrics endpoint
        try:
            metrics_response = await self.client.get(f"{REVIEWER_ORCHESTRATOR_URL}/metrics")
            if metrics_response.status_code == 200:
                metrics = metrics_response.json()
                logger.info(f"✅ Reviewer Metrics: OK")
                logger.info(f"   Queue Length: {metrics.get('queue_length', 0)}")
                
                last_5m = metrics.get('last_5m', {})
                logger.info(f"   Last 5m - Light: {last_5m.get('total_light', 0)}, Heavy: {last_5m.get('total_heavy', 0)}")
                logger.info(f"   Last 5m - Light Latency: {last_5m.get('avg_latency_ms_light', 0):.1f}ms")
                logger.info(f"   Last 5m - Heavy Latency: {last_5m.get('avg_latency_ms_heavy', 0):.1f}ms")
                
                return {
                    "status": "success",
                    "config": config,
                    "metrics": metrics
                }
            else:
                logger.error(f"❌ Reviewer Metrics: Error {metrics_response.status_code}")
                return {
                    "status": "error",
                    "error": f"Metrics endpoint failed: {metrics_response.status_code}"
                }
        except Exception as e:
            logger.error(f"❌ Reviewer Metrics: Exception - {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def test_confidence_routing(self) -> Dict:
        """Test confidence-based routing between light and heavy reviewers."""
        logger.info("🔍 Testing Confidence-Based Routing...")
        
        # Test with low confidence feed (should trigger heavy reviewer)
        low_confidence_feed = {
            "feed_id": "test-low-conf",
            "title": "Mysterious market movements puzzle analysts",
            "url": "https://example.com/mysterious-news",
            "content": "Unusual trading patterns observed in various markets today have left analysts scratching their heads. The movements don't correlate with any known economic indicators or news events.",
            "published": "2025-01-26T16:00:00Z"
        }
        
        # Test with high confidence feed (should stay with light reviewer)
        high_confidence_feed = {
            "feed_id": "test-high-conf",
            "title": "Tesla stock rises 5% after earnings beat",
            "url": "https://example.com/tesla-news",
            "content": "Tesla Inc. shares jumped 5% in after-hours trading following the company's quarterly earnings report that exceeded analyst expectations. Revenue and profit margins both showed strong growth.",
            "published": "2025-01-26T18:00:00Z"
        }
        
        results = {}
        
        # Test low confidence feed
        try:
            response = await self.client.post(f"{LIGHT_REVIEWER_URL}/review", json=low_confidence_feed)
            if response.status_code == 200:
                result = response.json()
                confidence = result.get('confidence', 0)
                results['low_confidence'] = {
                    "status": "success",
                    "confidence": confidence,
                    "should_escalate": confidence < 0.85
                }
                logger.info(f"✅ Low Confidence Test: {confidence:.2f} (should escalate: {confidence < 0.85})")
            else:
                results['low_confidence'] = {"status": "error", "error": f"HTTP {response.status_code}"}
        except Exception as e:
            results['low_confidence'] = {"status": "error", "error": str(e)}
        
        # Test high confidence feed
        try:
            response = await self.client.post(f"{LIGHT_REVIEWER_URL}/review", json=high_confidence_feed)
            if response.status_code == 200:
                result = response.json()
                confidence = result.get('confidence', 0)
                results['high_confidence'] = {
                    "status": "success",
                    "confidence": confidence,
                    "should_escalate": confidence < 0.85
                }
                logger.info(f"✅ High Confidence Test: {confidence:.2f} (should escalate: {confidence < 0.85})")
            else:
                results['high_confidence'] = {"status": "error", "error": f"HTTP {response.status_code}"}
        except Exception as e:
            results['high_confidence'] = {"status": "error", "error": str(e)}
        
        return results
    
    async def test_performance_benchmarks(self) -> Dict:
        """Test performance benchmarks for both reviewers."""
        logger.info("🔍 Testing Performance Benchmarks...")
        
        test_feeds = [
            {
                "feed_id": f"perf-test-{i}",
                "title": f"Performance test article {i}",
                "url": f"https://example.com/test-{i}",
                "content": f"This is a performance test article number {i}. It contains various topics including technology, finance, and general news to test the reviewer's performance.",
                "published": "2025-01-26T12:00:00Z"
            }
            for i in range(5)
        ]
        
        # Test light reviewer performance
        light_times = []
        for feed in test_feeds:
            try:
                start_time = datetime.utcnow()
                response = await self.client.post(f"{LIGHT_REVIEWER_URL}/review", json=feed)
                end_time = datetime.utcnow()
                
                if response.status_code == 200:
                    response_time = (end_time - start_time).total_seconds() * 1000
                    light_times.append(response_time)
                else:
                    logger.warning(f"Light reviewer failed for feed {feed['feed_id']}: {response.status_code}")
            except Exception as e:
                logger.warning(f"Light reviewer exception for feed {feed['feed_id']}: {e}")
        
        # Test heavy reviewer performance
        heavy_times = []
        for feed in test_feeds:
            try:
                start_time = datetime.utcnow()
                response = await self.client.post(f"{HEAVY_REVIEWER_URL}/review", json=feed)
                end_time = datetime.utcnow()
                
                if response.status_code == 200:
                    response_time = (end_time - start_time).total_seconds() * 1000
                    heavy_times.append(response_time)
                else:
                    logger.warning(f"Heavy reviewer failed for feed {feed['feed_id']}: {response.status_code}")
            except Exception as e:
                logger.warning(f"Heavy reviewer exception for feed {feed['feed_id']}: {e}")
        
        # Calculate statistics
        light_avg = sum(light_times) / len(light_times) if light_times else 0
        heavy_avg = sum(heavy_times) / len(heavy_times) if heavy_times else 0
        
        logger.info(f"✅ Performance Benchmarks:")
        logger.info(f"   Light Reviewer: {light_avg:.1f}ms avg ({len(light_times)} successful)")
        logger.info(f"   Heavy Reviewer: {heavy_avg:.1f}ms avg ({len(heavy_times)} successful)")
        
        return {
            "light_reviewer": {
                "avg_response_time_ms": light_avg,
                "successful_requests": len(light_times),
                "performance_ok": light_avg < 500
            },
            "heavy_reviewer": {
                "avg_response_time_ms": heavy_avg,
                "successful_requests": len(heavy_times),
                "performance_ok": heavy_avg < 2000
            }
        }
    
    async def run_all_tests(self) -> Dict:
        """Run all reviewer pipeline tests."""
        logger.info("🚀 Starting Reviewer Pipeline Tests...")
        
        results = {}
        
        # Test individual services
        results['light_reviewer'] = await self.test_light_reviewer()
        results['heavy_reviewer'] = await self.test_heavy_reviewer()
        results['orchestrator'] = await self.test_reviewer_orchestrator()
        
        # Test routing logic
        results['confidence_routing'] = await self.test_confidence_routing()
        
        # Test performance
        results['performance'] = await self.test_performance_benchmarks()
        
        return results
    
    def generate_report(self, results: Dict) -> str:
        """Generate a comprehensive test report."""
        report = []
        report.append("=" * 80)
        report.append("REVIEWER PIPELINE TEST REPORT")
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
            if test_name == 'confidence_routing':
                # Special handling for routing test
                report.append(f"CONFIDENCE ROUTING TEST")
                report.append("-" * 30)
                for sub_test, sub_result in result.items():
                    status_icon = "✅" if sub_result.get('status') == 'success' else "❌"
                    report.append(f"{status_icon} {sub_test}: {sub_result.get('status', 'unknown')}")
                    if 'confidence' in sub_result:
                        report.append(f"   Confidence: {sub_result['confidence']:.2f}")
                report.append("")
            elif test_name == 'performance':
                # Special handling for performance test
                report.append(f"PERFORMANCE BENCHMARKS")
                report.append("-" * 30)
                light_perf = result.get('light_reviewer', {})
                heavy_perf = result.get('heavy_reviewer', {})
                
                light_icon = "✅" if light_perf.get('performance_ok') else "❌"
                heavy_icon = "✅" if heavy_perf.get('performance_ok') else "❌"
                
                report.append(f"{light_icon} Light Reviewer: {light_perf.get('avg_response_time_ms', 0):.1f}ms avg")
                report.append(f"{heavy_icon} Heavy Reviewer: {heavy_perf.get('avg_response_time_ms', 0):.1f}ms avg")
                report.append("")
            else:
                # Standard test result
                status_icon = "✅" if result.get('status') == 'success' else "❌"
                report.append(f"{status_icon} {test_name.upper()}: {result.get('status', 'unknown')}")
                
                if 'response_time_ms' in result:
                    report.append(f"   Response Time: {result['response_time_ms']:.1f}ms")
                
                if 'error' in result:
                    report.append(f"   Error: {result['error']}")
                
                report.append("")
        
        return "\n".join(report)
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


async def main():
    """Main test function."""
    tester = ReviewerPipelineTester()
    
    try:
        results = await tester.run_all_tests()
        
        # Generate and print report
        report = tester.generate_report(results)
        print(report)
        
        # Overall status
        total_tests = len(results)
        passed_tests = sum(1 for r in results.values() if r.get('status') == 'success')
        
        if passed_tests == total_tests:
            print(f"\n🎉 ALL REVIEWER TESTS PASSED! ({passed_tests}/{total_tests})")
            return 0
        else:
            print(f"\n⚠️  SOME REVIEWER TESTS FAILED! ({passed_tests}/{total_tests})")
            return 1
            
    except Exception as e:
        logger.error(f"Reviewer test suite failed: {e}")
        return 1
    finally:
        await tester.close()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
