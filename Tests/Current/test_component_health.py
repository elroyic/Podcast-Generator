#!/usr/bin/env python3
"""
Component Health Tests - Test individual service health and basic functionality.
"""
import asyncio
import httpx
import pytest
import logging
from typing import Dict, List
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Service URLs
SERVICE_URLS = {
    "api-gateway": "http://localhost:8000",
    "news-feed": "http://localhost:8001",
    "text-generation": "http://localhost:8002",
    "writer": "http://localhost:8003",
    "presenter": "http://localhost:8004",
    "publishing": "http://localhost:8005",
    "ai-overseer": "http://localhost:8006",
    "light-reviewer": "http://localhost:8007",
    "heavy-reviewer": "http://localhost:8008",
    "reviewer": "http://localhost:8009",
    "collections": "http://localhost:8011",
    "podcast-host": "http://localhost:8012",
    "nginx": "http://localhost:8095"
}


class ComponentHealthTester:
    """Test individual component health and basic functionality."""
    
    def __init__(self):
        self.results = {}
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def test_service_health(self, service_name: str, base_url: str) -> Dict:
        """Test a single service's health endpoint."""
        result = {
            "service": service_name,
            "url": base_url,
            "status": "unknown",
            "response_time_ms": 0,
            "error": None,
            "details": {}
        }
        
        try:
            start_time = datetime.utcnow()
            response = await self.client.get(f"{base_url}/health")
            end_time = datetime.utcnow()
            
            result["response_time_ms"] = (end_time - start_time).total_seconds() * 1000
            
            if response.status_code == 200:
                result["status"] = "healthy"
                result["details"] = response.json()
                logger.info(f"✅ {service_name}: Healthy ({result['response_time_ms']:.1f}ms)")
            else:
                result["status"] = "unhealthy"
                result["error"] = f"HTTP {response.status_code}: {response.text}"
                logger.error(f"❌ {service_name}: Unhealthy - {result['error']}")
                
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
            logger.error(f"❌ {service_name}: Error - {e}")
        
        return result
    
    async def test_all_services(self) -> Dict[str, Dict]:
        """Test health of all services."""
        logger.info("🔍 Testing all service health endpoints...")
        
        tasks = []
        for service_name, base_url in SERVICE_URLS.items():
            task = self.test_service_health(service_name, base_url)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Task failed with exception: {result}")
                continue
            
            self.results[result["service"]] = result
        
        return self.results
    
    async def test_api_gateway_endpoints(self) -> Dict:
        """Test API Gateway specific endpoints."""
        logger.info("🔍 Testing API Gateway endpoints...")
        
        endpoints = [
            ("/", "GET", "Main dashboard"),
            ("/groups", "GET", "Groups management"),
            ("/reviewer", "GET", "Reviewer dashboard"),
            ("/presenters", "GET", "Presenter management"),
            ("/api/podcast-groups", "GET", "Podcast groups API"),
            ("/api/presenters", "GET", "Presenters API"),
            ("/api/news-feeds", "GET", "News feeds API"),
            ("/api/reviewer/config", "GET", "Reviewer config API"),
            ("/api/reviewer/metrics", "GET", "Reviewer metrics API"),
        ]
        
        results = {}
        for endpoint, method, description in endpoints:
            try:
                start_time = datetime.utcnow()
                response = await self.client.request(method, f"{SERVICE_URLS['api-gateway']}{endpoint}")
                end_time = datetime.utcnow()
                
                response_time = (end_time - start_time).total_seconds() * 1000
                
                if response.status_code in [200, 404]:  # 404 is acceptable for some endpoints
                    results[endpoint] = {
                        "status": "ok",
                        "response_time_ms": response_time,
                        "status_code": response.status_code
                    }
                    logger.info(f"✅ {description}: OK ({response_time:.1f}ms)")
                else:
                    results[endpoint] = {
                        "status": "error",
                        "response_time_ms": response_time,
                        "status_code": response.status_code,
                        "error": response.text
                    }
                    logger.error(f"❌ {description}: Error {response.status_code}")
                    
            except Exception as e:
                results[endpoint] = {
                    "status": "error",
                    "error": str(e)
                }
                logger.error(f"❌ {description}: Exception - {e}")
        
        return results
    
    async def test_database_connectivity(self) -> Dict:
        """Test database connectivity through services."""
        logger.info("🔍 Testing database connectivity...")
        
        # Test through API Gateway
        try:
            response = await self.client.get(f"{SERVICE_URLS['api-gateway']}/api/podcast-groups")
            if response.status_code == 200:
                logger.info("✅ Database connectivity: OK")
                return {"status": "ok", "details": "Database accessible via API Gateway"}
            else:
                logger.error(f"❌ Database connectivity: Error {response.status_code}")
                return {"status": "error", "error": f"HTTP {response.status_code}"}
        except Exception as e:
            logger.error(f"❌ Database connectivity: Exception - {e}")
            return {"status": "error", "error": str(e)}
    
    async def test_redis_connectivity(self) -> Dict:
        """Test Redis connectivity through services."""
        logger.info("🔍 Testing Redis connectivity...")
        
        # Test through Reviewer service
        try:
            response = await self.client.get(f"{SERVICE_URLS['reviewer']}/config")
            if response.status_code == 200:
                logger.info("✅ Redis connectivity: OK")
                return {"status": "ok", "details": "Redis accessible via Reviewer service"}
            else:
                logger.error(f"❌ Redis connectivity: Error {response.status_code}")
                return {"status": "error", "error": f"HTTP {response.status_code}"}
        except Exception as e:
            logger.error(f"❌ Redis connectivity: Exception - {e}")
            return {"status": "error", "error": str(e)}
    
    def generate_report(self) -> str:
        """Generate a comprehensive health report."""
        report = []
        report.append("=" * 80)
        report.append("COMPONENT HEALTH TEST REPORT")
        report.append("=" * 80)
        report.append(f"Generated: {datetime.utcnow().isoformat()}")
        report.append("")
        
        # Service Health Summary
        healthy_count = sum(1 for r in self.results.values() if r["status"] == "healthy")
        total_count = len(self.results)
        
        report.append("SERVICE HEALTH SUMMARY")
        report.append("-" * 40)
        report.append(f"Healthy Services: {healthy_count}/{total_count}")
        report.append("")
        
        # Individual Service Results
        for service_name, result in self.results.items():
            status_icon = "✅" if result["status"] == "healthy" else "❌"
            report.append(f"{status_icon} {service_name}: {result['status']}")
            if result["response_time_ms"] > 0:
                report.append(f"   Response Time: {result['response_time_ms']:.1f}ms")
            if result["error"]:
                report.append(f"   Error: {result['error']}")
            report.append("")
        
        return "\n".join(report)
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


async def main():
    """Main test function."""
    tester = ComponentHealthTester()
    
    try:
        # Test all services
        await tester.test_all_services()
        
        # Test API Gateway endpoints
        api_results = await tester.test_api_gateway_endpoints()
        
        # Test infrastructure
        db_result = await tester.test_database_connectivity()
        redis_result = await tester.test_redis_connectivity()
        
        # Generate and print report
        report = tester.generate_report()
        print(report)
        
        # Print additional results
        print("\n" + "=" * 80)
        print("ADDITIONAL TEST RESULTS")
        print("=" * 80)
        
        print(f"\nDatabase Connectivity: {db_result['status']}")
        if db_result.get('error'):
            print(f"Error: {db_result['error']}")
        
        print(f"\nRedis Connectivity: {redis_result['status']}")
        if redis_result.get('error'):
            print(f"Error: {redis_result['error']}")
        
        print(f"\nAPI Gateway Endpoints Tested: {len(api_results)}")
        successful_endpoints = sum(1 for r in api_results.values() if r['status'] == 'ok')
        print(f"Successful Endpoints: {successful_endpoints}/{len(api_results)}")
        
        # Overall status
        healthy_services = sum(1 for r in tester.results.values() if r["status"] == "healthy")
        total_services = len(tester.results)
        
        if healthy_services == total_services:
            print(f"\n🎉 ALL TESTS PASSED! ({healthy_services}/{total_services} services healthy)")
            return 0
        else:
            print(f"\n⚠️  SOME TESTS FAILED! ({healthy_services}/{total_services} services healthy)")
            return 1
            
    except Exception as e:
        logger.error(f"Test suite failed: {e}")
        return 1
    finally:
        await tester.close()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
