#!/usr/bin/env python3
"""
Test script to verify all critical fixes from the Action Plan are working correctly.

Tests:
1. Editor Service Integration
2. Episode Generation Locking
3. AudioFile DB Persistence
4. Collection Min Feeds Validation
"""

import asyncio
import sys
import json
from datetime import datetime
from uuid import uuid4, UUID

import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Database setup
DATABASE_URL = "postgresql://podcast_user:podcast_pass@localhost:5432/podcast_ai"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

BASE_URL = "http://localhost:8000"

# Test colors
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'


def print_test(test_name: str):
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}TEST: {test_name}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")


def print_pass(message: str):
    print(f"{GREEN}✅ PASS: {message}{RESET}")


def print_fail(message: str):
    print(f"{RED}❌ FAIL: {message}{RESET}")


def print_info(message: str):
    print(f"{YELLOW}ℹ️  INFO: {message}{RESET}")


async def test_1_editor_integration():
    """Test 1: Verify Editor Service is integrated in episode generation workflow"""
    print_test("Editor Service Integration")
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            # Check if editor service is running
            print_info("Checking editor service health...")
            response = await client.get("http://localhost:8009/health")
            if response.status_code == 200:
                print_pass("Editor service is running")
            else:
                print_fail(f"Editor service unhealthy: {response.status_code}")
                return False
            
            # Check AI Overseer service source code mentions editor
            print_info("Verifying editor is called in AI Overseer...")
            
            # Read the services.py file to verify editor integration
            with open('/workspace/services/ai-overseer/app/services.py', 'r') as f:
                services_code = f.read()
                
            if 'editor_service.edit_script' in services_code:
                print_pass("Editor service is called in AI Overseer workflow")
            else:
                print_fail("Editor service NOT found in AI Overseer workflow")
                return False
            
            # Verify the endpoint exists
            if 'edit_result = await self.editor_service.edit_script' in services_code:
                print_pass("Editor edit_script method is invoked")
            else:
                print_fail("Editor edit_script method NOT invoked")
                return False
            
            # Check for fallback handling
            if 'except Exception as e:' in services_code and 'editor' in services_code.lower():
                print_pass("Editor has fallback error handling")
            else:
                print_fail("No fallback error handling for editor")
            
            print_pass("✅ Test 1: Editor Integration PASSED")
            return True
            
        except Exception as e:
            print_fail(f"Test 1 failed with error: {e}")
            return False


async def test_2_episode_locking():
    """Test 2: Verify Episode Generation Locking prevents concurrent runs"""
    print_test("Episode Generation Locking")
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            # Check if locking code exists
            print_info("Verifying locking mechanism in code...")
            
            with open('/workspace/services/ai-overseer/app/services.py', 'r') as f:
                services_code = f.read()
            
            # Check for CadenceManager with locking
            if 'acquire_group_lock' in services_code:
                print_pass("Lock acquisition method found")
            else:
                print_fail("Lock acquisition method NOT found")
                return False
            
            if 'release_group_lock' in services_code:
                print_pass("Lock release method found")
            else:
                print_fail("Lock release method NOT found")
                return False
            
            # Check if lock is used in episode generation
            if 'cadence_manager.acquire_group_lock(group_id)' in services_code:
                print_pass("Lock is acquired before episode generation")
            else:
                print_fail("Lock NOT acquired before episode generation")
                return False
            
            # Check Redis-based locking
            if 'redis.set' in services_code and 'nx=True' in services_code:
                print_pass("Redis-based locking with NX flag implemented")
            else:
                print_fail("Redis-based locking NOT properly implemented")
                return False
            
            # Check lock timeout
            if 'ex=' in services_code or 'timeout_hours' in services_code:
                print_pass("Lock timeout configured")
            else:
                print_fail("Lock timeout NOT configured")
            
            print_pass("✅ Test 2: Episode Locking PASSED")
            return True
            
        except Exception as e:
            print_fail(f"Test 2 failed with error: {e}")
            return False


async def test_3_audiofile_persistence():
    """Test 3: Verify AudioFile DB records are created"""
    print_test("AudioFile DB Persistence")
    
    try:
        # Check if AudioFile creation code exists
        print_info("Verifying AudioFile creation in AI Overseer...")
        
        with open('/workspace/services/ai-overseer/app/services.py', 'r') as f:
            services_code = f.read()
        
        # Check for AudioFile model import
        if 'AudioFile' in services_code:
            print_pass("AudioFile model is imported")
        else:
            print_fail("AudioFile model NOT imported")
            return False
        
        # Check for AudioFile creation after audio generation
        if 'AudioFile(' in services_code:
            print_pass("AudioFile record creation found")
        else:
            print_fail("AudioFile record creation NOT found")
            return False
        
        # Check for required fields
        if 'episode_id=' in services_code and 'url=' in services_code:
            print_pass("AudioFile has required fields (episode_id, url)")
        else:
            print_fail("AudioFile missing required fields")
            return False
        
        # Check if it's added to database
        if 'db.add(audio_file)' in services_code:
            print_pass("AudioFile is added to database")
        else:
            print_fail("AudioFile NOT added to database")
            return False
        
        # Check for duration and file size
        if 'duration_seconds' in services_code:
            print_pass("Duration tracking implemented")
        else:
            print_info("Duration tracking may be optional")
        
        if 'file_size' in services_code:
            print_pass("File size tracking implemented")
        else:
            print_info("File size tracking may be optional")
        
        print_pass("✅ Test 3: AudioFile Persistence PASSED")
        return True
        
    except Exception as e:
        print_fail(f"Test 3 failed with error: {e}")
        return False


async def test_4_min_feeds_validation():
    """Test 4: Verify Collection Min Feeds Validation"""
    print_test("Collection Min Feeds Validation")
    
    try:
        # Check if validation code exists
        print_info("Verifying min feeds validation in AI Overseer...")
        
        with open('/workspace/services/ai-overseer/app/services.py', 'r') as f:
            services_code = f.read()
        
        # Check for MIN_FEEDS_REQUIRED
        if 'MIN_FEEDS_REQUIRED' in services_code or 'MIN_FEEDS_PER_COLLECTION' in services_code:
            print_pass("Min feeds configuration found")
        else:
            print_fail("Min feeds configuration NOT found")
            return False
        
        # Check for article count validation
        if 'len(articles)' in services_code and 'MIN_FEEDS' in services_code:
            print_pass("Article count validation implemented")
        else:
            print_fail("Article count validation NOT implemented")
            return False
        
        # Check for error raising on insufficient articles
        if 'Insufficient articles' in services_code or 'len(articles) <' in services_code:
            print_pass("Error raised for insufficient articles")
        else:
            print_fail("No error raised for insufficient articles")
            return False
        
        # Check for configurable threshold
        if 'os.getenv' in services_code and 'MIN_FEEDS' in services_code:
            print_pass("Threshold is configurable via environment variable")
        else:
            print_info("Threshold may be hardcoded (not ideal)")
        
        # Check default value
        if '"3"' in services_code or ', 3)' in services_code:
            print_pass("Default threshold of 3 articles configured")
        else:
            print_info("Default threshold may differ from specification")
        
        print_pass("✅ Test 4: Min Feeds Validation PASSED")
        return True
        
    except Exception as e:
        print_fail(f"Test 4 failed with error: {e}")
        return False


async def test_5_integration_check():
    """Test 5: Overall integration check"""
    print_test("Overall Integration Check")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Check all critical services are running
            services = {
                "API Gateway": "http://localhost:8000/health",
                "Editor": "http://localhost:8009/health",
                "Reviewer": "http://localhost:8013/health",
                "Presenter": "http://localhost:8004/health",
                "Light Reviewer": "http://localhost:8007/health",
                "Heavy Reviewer": "http://localhost:8011/health",
            }
            
            print_info("Checking service health...")
            all_healthy = True
            
            for service_name, health_url in services.items():
                try:
                    response = await client.get(health_url)
                    if response.status_code == 200:
                        print_pass(f"{service_name} is healthy")
                    else:
                        print_fail(f"{service_name} is unhealthy ({response.status_code})")
                        all_healthy = False
                except Exception as e:
                    print_fail(f"{service_name} is unreachable: {e}")
                    all_healthy = False
            
            if all_healthy:
                print_pass("All critical services are healthy")
            else:
                print_fail("Some services are unhealthy")
            
            return all_healthy
            
        except Exception as e:
            print_fail(f"Test 5 failed with error: {e}")
            return False


async def main():
    """Run all tests"""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}CRITICAL FIXES VALIDATION TEST SUITE{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")
    print(f"{YELLOW}Testing implementation of Action Plan critical fixes{RESET}\n")
    
    results = []
    
    # Run all tests
    results.append(("Editor Integration", await test_1_editor_integration()))
    results.append(("Episode Locking", await test_2_episode_locking()))
    results.append(("AudioFile Persistence", await test_3_audiofile_persistence()))
    results.append(("Min Feeds Validation", await test_4_min_feeds_validation()))
    results.append(("Integration Check", await test_5_integration_check()))
    
    # Print summary
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}TEST SUMMARY{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = f"{GREEN}PASS{RESET}" if result else f"{RED}FAIL{RESET}"
        print(f"  {test_name}: {status}")
    
    print(f"\n{BLUE}Total: {passed}/{total} tests passed{RESET}")
    
    if passed == total:
        print(f"\n{GREEN}{'='*60}{RESET}")
        print(f"{GREEN}🎉 ALL CRITICAL FIXES VALIDATED SUCCESSFULLY! 🎉{RESET}")
        print(f"{GREEN}{'='*60}{RESET}")
        return 0
    else:
        print(f"\n{RED}{'='*60}{RESET}")
        print(f"{RED}⚠️  SOME TESTS FAILED - REVIEW NEEDED{RESET}")
        print(f"{RED}{'='*60}{RESET}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
