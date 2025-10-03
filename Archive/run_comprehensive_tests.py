#!/usr/bin/env python3
"""
Comprehensive Test Execution Script - Run all tests with system validation.
"""
import asyncio
import subprocess
import sys
import os
import logging
from datetime import datetime
import argparse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def run_command(command: str, description: str) -> bool:
    """Run a command and return success status."""
    logger.info(f"🚀 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        logger.info(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ {description} failed: {e}")
        if e.stdout:
            logger.error(f"STDOUT: {e.stdout}")
        if e.stderr:
            logger.error(f"STDERR: {e.stderr}")
        return False


def check_docker_compose():
    """Check if docker-compose is available and services are running."""
    logger.info("🔍 Checking Docker Compose...")
    
    # Check if docker-compose is available
    try:
        result = subprocess.run(["docker", "compose", "version"], capture_output=True, text=True)
        if result.returncode != 0:
            logger.error("❌ Docker Compose not available")
            return False
        logger.info("✅ Docker Compose is available")
    except FileNotFoundError:
        logger.error("❌ Docker Compose not found")
        return False
    
    # Check if services are running
    try:
        result = subprocess.run(["docker", "compose", "ps"], capture_output=True, text=True)
        if result.returncode != 0:
            logger.error("❌ Failed to check Docker services")
            return False
        
        # Count running services
        lines = result.stdout.strip().split('\n')
        running_services = [line for line in lines if 'running' in line.lower()]
        
        logger.info(f"✅ Found {len(running_services)} running services")
        return True
    except Exception as e:
        logger.error(f"❌ Error checking Docker services: {e}")
        return False


def start_services():
    """Start all services using docker-compose."""
    logger.info("🚀 Starting all services...")
    
    # Start services in detached mode
    if not run_command("docker-compose up -d", "Starting services"):
        return False
    
    # Wait for services to be ready
    logger.info("⏳ Waiting for services to be ready...")
    import time
    time.sleep(30)  # Wait 30 seconds for services to start
    
    return True


def stop_services():
    """Stop all services."""
    logger.info("🛑 Stopping all services...")
    return run_command("docker-compose down", "Stopping services")


def run_system_validation():
    """Run system validation tests."""
    logger.info("🔍 Running system validation...")
    
    test_dir = "Tests/Current"
    if not os.path.exists(test_dir):
        logger.error(f"❌ Test directory not found: {test_dir}")
        return False
    
    validation_script = os.path.join(test_dir, "validate_system.py")
    if not os.path.exists(validation_script):
        logger.error(f"❌ Validation script not found: {validation_script}")
        return False
    
    return run_command(f"python {validation_script}", "System validation")


def run_component_tests():
    """Run individual component tests."""
    logger.info("🧪 Running component tests...")
    
    test_dir = "Tests/Current"
    test_scripts = [
        "test_component_health.py",
        "test_reviewer_pipeline.py",
        "test_collections_service.py"
    ]
    
    all_passed = True
    
    for script in test_scripts:
        script_path = os.path.join(test_dir, script)
        if os.path.exists(script_path):
            if not run_command(f"python {script_path}", f"Running {script}"):
                all_passed = False
        else:
            logger.warning(f"⚠️  Test script not found: {script_path}")
    
    return all_passed


def run_workflow_tests():
    """Run full workflow tests."""
    logger.info("🔄 Running workflow tests...")
    
    test_dir = "Tests/Current"
    workflow_script = os.path.join(test_dir, "test_full_workflow.py")
    
    if os.path.exists(workflow_script):
        return run_command(f"python {workflow_script}", "Full workflow test")
    else:
        logger.error(f"❌ Workflow test script not found: {workflow_script}")
        return False


def run_performance_tests():
    """Run performance and load tests."""
    logger.info("⚡ Running performance tests...")
    
    test_dir = "Tests/Current"
    performance_script = os.path.join(test_dir, "test_performance_load.py")
    
    if os.path.exists(performance_script):
        return run_command(f"python {performance_script}", "Performance tests")
    else:
        logger.error(f"❌ Performance test script not found: {performance_script}")
        return False


def run_all_tests():
    """Run all tests using the comprehensive test runner."""
    logger.info("🎯 Running all tests...")
    
    test_dir = "Tests/Current"
    test_runner = os.path.join(test_dir, "run_all_tests.py")
    
    if os.path.exists(test_runner):
        return run_command(f"python {test_runner}", "Comprehensive test suite")
    else:
        logger.error(f"❌ Test runner not found: {test_runner}")
        return False


def setup_rss_feeds():
    """Set up RSS feeds for testing."""
    logger.info("📡 Setting up RSS feeds...")
    
    setup_script = "setup_rss_feeds.py"
    if os.path.exists(setup_script):
        return run_command(f"python {setup_script}", "RSS feeds setup")
    else:
        logger.warning(f"⚠️  RSS setup script not found: {setup_script}")
        return True  # Not critical for testing


def main():
    """Main test execution function."""
    parser = argparse.ArgumentParser(description="Comprehensive Test Execution Script")
    parser.add_argument("--skip-startup", action="store_true", help="Skip service startup")
    parser.add_argument("--skip-shutdown", action="store_true", help="Skip service shutdown")
    parser.add_argument("--validation-only", action="store_true", help="Run only system validation")
    parser.add_argument("--component-only", action="store_true", help="Run only component tests")
    parser.add_argument("--workflow-only", action="store_true", help="Run only workflow tests")
    parser.add_argument("--performance-only", action="store_true", help="Run only performance tests")
    parser.add_argument("--setup-feeds", action="store_true", help="Set up RSS feeds")
    
    args = parser.parse_args()
    
    logger.info("🎯 Starting Comprehensive Test Execution")
    logger.info(f"   Timestamp: {datetime.utcnow().isoformat()}")
    logger.info("")
    
    success = True
    
    try:
        # Check Docker Compose
        if not check_docker_compose():
            logger.error("❌ Docker Compose check failed")
            return 1
        
        # Start services (unless skipped)
        if not args.skip_startup:
            if not start_services():
                logger.error("❌ Failed to start services")
                return 1
        
        # Set up RSS feeds (if requested)
        if args.setup_feeds:
            if not setup_rss_feeds():
                logger.warning("⚠️  RSS feeds setup failed, continuing...")
        
        # Run tests based on arguments
        if args.validation_only:
            success = run_system_validation()
        elif args.component_only:
            success = run_component_tests()
        elif args.workflow_only:
            success = run_workflow_tests()
        elif args.performance_only:
            success = run_performance_tests()
        else:
            # Run all tests
            success = run_all_tests()
        
        # Stop services (unless skipped)
        if not args.skip_shutdown:
            stop_services()
        
        # Final status
        if success:
            logger.info("🎉 ALL TESTS COMPLETED SUCCESSFULLY!")
            return 0
        else:
            logger.error("❌ SOME TESTS FAILED!")
            return 1
            
    except KeyboardInterrupt:
        logger.info("🛑 Test execution interrupted by user")
        if not args.skip_shutdown:
            stop_services()
        return 1
    except Exception as e:
        logger.error(f"💥 Test execution failed: {e}")
        if not args.skip_shutdown:
            stop_services()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
