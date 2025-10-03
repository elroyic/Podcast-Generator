#!/usr/bin/env python3
"""
System Validation Script - Check if all services are running and accessible.
"""
import asyncio
import httpx
import logging
from datetime import datetime
from typing import Dict, List
import subprocess
import sys

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Expected services and their ports
EXPECTED_SERVICES = {
    "postgres": {"port": 5432, "type": "database"},
    "redis": {"port": 6379, "type": "cache"},
    "api-gateway": {"port": 8000, "type": "service", "health_endpoint": "/health"},
    "news-feed": {"port": 8001, "type": "service", "health_endpoint": "/health"},
    "text-generation": {"port": 8002, "type": "service", "health_endpoint": "/health"},
    "writer": {"port": 8003, "type": "service", "health_endpoint": "/health"},
    "presenter": {"port": 8004, "type": "service", "health_endpoint": "/health"},
    "publishing": {"port": 8005, "type": "service", "health_endpoint": "/health"},
    "ai-overseer": {"port": 8006, "type": "service", "health_endpoint": "/health"},
    "light-reviewer": {"port": 8007, "type": "service", "health_endpoint": "/health"},
    "heavy-reviewer": {"port": 8008, "type": "service", "health_endpoint": "/health"},
    "reviewer": {"port": 8009, "type": "service", "health_endpoint": "/health"},
    "collections": {"port": 8011, "type": "service", "health_endpoint": "/health"},
    "podcast-host": {"port": 8012, "type": "service", "health_endpoint": "/health"},
    "vllm": {"port": 8000, "type": "service", "health_endpoint": "/health"},
    "ollama": {"port": 11434, "type": "service", "health_endpoint": "/api/tags"},
    "nginx": {"port": 8095, "type": "service", "health_endpoint": "/health"}
}


class SystemValidator:
    """Validate system components and services."""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=10.0)
        self.validation_results = {}
    
    async def check_port_availability(self, service_name: str, port: int) -> Dict:
        """Check if a port is available and listening."""
        try:
            # Use netstat to check if port is listening
            result = subprocess.run(
                ["netstat", "-tuln"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                # Check if port is in the output
                port_found = f":{port}" in result.stdout
                return {
                    "available": port_found,
                    "method": "netstat"
                }
            else:
                # Fallback: try to connect to the port
                try:
                    reader, writer = await asyncio.wait_for(
                        asyncio.open_connection("localhost", port),
                        timeout=2.0
                    )
                    writer.close()
                    await writer.wait_closed()
                    return {
                        "available": True,
                        "method": "connection"
                    }
                except Exception:
                    return {
                        "available": False,
                        "method": "connection"
                    }
        except Exception as e:
            return {
                "available": False,
                "method": "error",
                "error": str(e)
            }
    
    async def check_http_service(self, service_name: str, port: int, health_endpoint: str = "/health") -> Dict:
        """Check if an HTTP service is responding."""
        try:
            url = f"http://localhost:{port}{health_endpoint}"
            response = await self.client.get(url)
            
            return {
                "available": True,
                "status_code": response.status_code,
                "response_time": response.elapsed.total_seconds() * 1000,
                "url": url
            }
        except Exception as e:
            return {
                "available": False,
                "error": str(e),
                "url": f"http://localhost:{port}{health_endpoint}"
            }
    
    async def check_docker_services(self) -> Dict:
        """Check Docker services status."""
        try:
            result = subprocess.run(
                ["docker", "compose", "ps", "--format", "json"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                # Parse JSON output (one JSON object per line)
                services = []
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        try:
                            service = eval(line)  # Use eval for simple JSON parsing
                            services.append(service)
                        except:
                            continue
                
                return {
                    "available": True,
                    "services": services,
                    "total_services": len(services)
                }
            else:
                return {
                    "available": False,
                    "error": result.stderr
                }
        except Exception as e:
            return {
                "available": False,
                "error": str(e)
            }
    
    async def validate_service(self, service_name: str, service_config: Dict) -> Dict:
        """Validate a single service."""
        port = service_config["port"]
        service_type = service_config["type"]
        health_endpoint = service_config.get("health_endpoint", "/health")
        
        logger.info(f"🔍 Validating {service_name} (port {port})...")
        
        result = {
            "service": service_name,
            "port": port,
            "type": service_type,
            "status": "unknown"
        }
        
        # Check port availability
        port_check = await self.check_port_availability(service_name, port)
        result["port_available"] = port_check["available"]
        result["port_check_method"] = port_check["method"]
        
        if "error" in port_check:
            result["port_error"] = port_check["error"]
        
        # For HTTP services, check health endpoint
        if service_type == "service" and port_check["available"]:
            health_check = await self.check_http_service(service_name, port, health_endpoint)
            result["health_available"] = health_check["available"]
            result["health_status_code"] = health_check.get("status_code")
            result["health_response_time"] = health_check.get("response_time")
            
            if "error" in health_check:
                result["health_error"] = health_check["error"]
            
            # Determine overall status
            if health_check["available"] and health_check.get("status_code") == 200:
                result["status"] = "healthy"
            elif health_check["available"]:
                result["status"] = "unhealthy"
            else:
                result["status"] = "unreachable"
        else:
            # For non-HTTP services, just check port
            if port_check["available"]:
                result["status"] = "available"
            else:
                result["status"] = "unavailable"
        
        # Log result
        status_icon = {
            "healthy": "✅",
            "available": "✅",
            "unhealthy": "⚠️",
            "unreachable": "❌",
            "unavailable": "❌"
        }.get(result["status"], "❓")
        
        logger.info(f"   {status_icon} {service_name}: {result['status']}")
        
        return result
    
    async def validate_all_services(self) -> Dict:
        """Validate all expected services."""
        logger.info("🚀 Starting System Validation...")
        logger.info(f"   Expected Services: {len(EXPECTED_SERVICES)}")
        logger.info("")
        
        results = {}
        
        for service_name, service_config in EXPECTED_SERVICES.items():
            result = await self.validate_service(service_name, service_config)
            results[service_name] = result
        
        return results
    
    async def run_comprehensive_validation(self) -> Dict:
        """Run comprehensive system validation."""
        logger.info("🎯 Starting Comprehensive System Validation...")
        logger.info("")
        
        validation_results = {}
        
        # Validate individual services
        validation_results["services"] = await self.validate_all_services()
        
        # Check Docker services
        logger.info("🔍 Checking Docker Services...")
        docker_result = await self.check_docker_services()
        validation_results["docker"] = docker_result
        
        if docker_result["available"]:
            logger.info(f"✅ Docker Services: {docker_result['total_services']} services found")
        else:
            logger.error(f"❌ Docker Services: {docker_result.get('error', 'Unknown error')}")
        
        logger.info("")
        
        return validation_results
    
    def generate_validation_report(self, results: Dict) -> str:
        """Generate a comprehensive validation report."""
        report = []
        report.append("=" * 80)
        report.append("SYSTEM VALIDATION REPORT")
        report.append("=" * 80)
        report.append(f"Generated: {datetime.utcnow().isoformat()}")
        report.append("")
        
        # Service Status Summary
        services = results.get("services", {})
        total_services = len(services)
        healthy_services = sum(1 for s in services.values() if s["status"] in ["healthy", "available"])
        unhealthy_services = sum(1 for s in services.values() if s["status"] in ["unhealthy", "unreachable", "unavailable"])
        
        report.append("SERVICE STATUS SUMMARY")
        report.append("-" * 40)
        report.append(f"Total Services: {total_services}")
        report.append(f"Healthy/Available: {healthy_services} ✅")
        report.append(f"Unhealthy/Unavailable: {unhealthy_services} ❌")
        report.append(f"Health Rate: {(healthy_services/total_services)*100:.1f}%")
        report.append("")
        
        # Individual Service Details
        report.append("INDIVIDUAL SERVICE DETAILS")
        report.append("-" * 40)
        
        for service_name, service_result in services.items():
            status_icon = {
                "healthy": "✅",
                "available": "✅",
                "unhealthy": "⚠️",
                "unreachable": "❌",
                "unavailable": "❌"
            }.get(service_result["status"], "❓")
            
            report.append(f"{status_icon} {service_name} (Port {service_result['port']}): {service_result['status']}")
            
            if service_result.get("health_response_time"):
                report.append(f"   Response Time: {service_result['health_response_time']:.1f}ms")
            
            if service_result.get("health_status_code"):
                report.append(f"   HTTP Status: {service_result['health_status_code']}")
            
            if service_result.get("health_error"):
                report.append(f"   Health Error: {service_result['health_error']}")
            
            if service_result.get("port_error"):
                report.append(f"   Port Error: {service_result['port_error']}")
            
            report.append("")
        
        # Docker Services Summary
        docker_result = results.get("docker", {})
        if docker_result.get("available"):
            report.append("DOCKER SERVICES")
            report.append("-" * 40)
            report.append(f"Total Docker Services: {docker_result.get('total_services', 0)}")
            
            # Show running services
            docker_services = docker_result.get("services", [])
            running_services = [s for s in docker_services if s.get("State") == "running"]
            report.append(f"Running Services: {len(running_services)}")
            
            for service in running_services[:10]:  # Show first 10
                name = service.get("Name", "unknown")
                state = service.get("State", "unknown")
                ports = service.get("Ports", "")
                report.append(f"   {name}: {state} {ports}")
            
            if len(docker_services) > 10:
                report.append(f"   ... and {len(docker_services) - 10} more services")
            
            report.append("")
        else:
            report.append("DOCKER SERVICES")
            report.append("-" * 40)
            report.append(f"❌ Docker Services: {docker_result.get('error', 'Unknown error')}")
            report.append("")
        
        # Recommendations
        report.append("RECOMMENDATIONS")
        report.append("-" * 40)
        
        if healthy_services == total_services:
            report.append("🎉 All services are healthy! System is ready for testing.")
        elif healthy_services > total_services * 0.8:
            report.append("⚠️  Most services are healthy. Review unhealthy services before testing.")
        else:
            report.append("🚨 Multiple services are unhealthy. Fix service issues before testing.")
        
        if unhealthy_services > 0:
            report.append("")
            report.append("Unhealthy Services to Fix:")
            for service_name, service_result in services.items():
                if service_result["status"] not in ["healthy", "available"]:
                    report.append(f"   - {service_name}: {service_result['status']}")
        
        report.append("")
        
        return "\n".join(report)
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


async def main():
    """Main validation function."""
    validator = SystemValidator()
    
    try:
        results = await validator.run_comprehensive_validation()
        
        # Generate and print report
        report = validator.generate_validation_report(results)
        print(report)
        
        # Determine exit code
        services = results.get("services", {})
        total_services = len(services)
        healthy_services = sum(1 for s in services.values() if s["status"] in ["healthy", "available"])
        
        if healthy_services == total_services:
            logger.info("🎉 SYSTEM VALIDATION PASSED!")
            return 0
        else:
            logger.error(f"⚠️  SYSTEM VALIDATION FAILED! ({healthy_services}/{total_services} services healthy)")
            return 1
            
    except Exception as e:
        logger.error(f"💥 System validation failed: {e}")
        return 1
    finally:
        await validator.close()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
