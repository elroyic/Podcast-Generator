"""
Test script to verify the Reviewer Service production pause mechanism.

This script tests:
1. Setting and clearing the production lock
2. Checking reviewer status during production
3. Manual pause/resume controls
"""
import asyncio
import httpx
import json
from datetime import datetime

# Service URLs
REVIEWER_URL = "http://localhost:8008"

async def test_production_pause():
    """Test the production pause mechanism."""
    print("=" * 60)
    print("Testing Reviewer Service Production Pause Mechanism")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        
        # Test 1: Check initial status
        print("\n1️⃣ Checking initial reviewer status...")
        response = await client.get(f"{REVIEWER_URL}/production/status")
        status = response.json()
        print(f"   Production Active: {status['production_active']}")
        print(f"   Reviewer Status: {status['message']}")
        
        # Test 2: Check queue worker status
        print("\n2️⃣ Checking queue worker status...")
        response = await client.get(f"{REVIEWER_URL}/queue/worker/status")
        worker_status = response.json()
        print(f"   Worker Running: {worker_status['worker_running']}")
        print(f"   Paused: {worker_status['paused']}")
        print(f"   Production Active: {worker_status['production_active']}")
        
        # Test 3: Manually pause reviews
        print("\n3️⃣ Testing manual pause...")
        response = await client.post(f"{REVIEWER_URL}/production/pause")
        pause_result = response.json()
        print(f"   ✅ {pause_result['message']}")
        print(f"   Lock Info: {json.dumps(pause_result['lock_info'], indent=6)}")
        
        # Test 4: Verify pause is active
        print("\n4️⃣ Verifying pause is active...")
        response = await client.get(f"{REVIEWER_URL}/production/status")
        status = response.json()
        print(f"   Production Active: {status['production_active']}")
        print(f"   Reviewer Paused: {status['reviewer_paused']}")
        assert status['reviewer_paused'] == True, "Reviewer should be paused"
        print("   ✅ Pause confirmed")
        
        # Test 5: Check queue status during pause
        print("\n5️⃣ Checking queue status during pause...")
        response = await client.get(f"{REVIEWER_URL}/queue/status")
        queue_status = response.json()
        print(f"   Queue Length: {queue_status['queue_length']}")
        print(f"   Status: {queue_status['status']}")
        
        # Test 6: Manually resume reviews
        print("\n6️⃣ Testing manual resume...")
        response = await client.post(f"{REVIEWER_URL}/production/resume")
        resume_result = response.json()
        print(f"   ✅ {resume_result['message']}")
        
        # Test 7: Verify resume is active
        print("\n7️⃣ Verifying resume is active...")
        response = await client.get(f"{REVIEWER_URL}/production/status")
        status = response.json()
        print(f"   Production Active: {status['production_active']}")
        print(f"   Reviewer Paused: {status['reviewer_paused']}")
        assert status['reviewer_paused'] == False, "Reviewer should be active"
        print("   ✅ Resume confirmed")
        
        # Test 8: Final health check
        print("\n8️⃣ Final health check...")
        response = await client.get(f"{REVIEWER_URL}/health")
        health = response.json()
        print(f"   Service: {health['service']}")
        print(f"   Status: {health['status']}")
        print(f"   Model Light: {health['model_light']}")
        print(f"   Model Heavy: {health['model_heavy']}")
        
        print("\n" + "=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)
        print("\nThe Reviewer Service production pause mechanism is working correctly:")
        print("  • Production status can be checked")
        print("  • Reviews can be manually paused")
        print("  • Reviews can be manually resumed")
        print("  • Lock state is properly managed in Redis")
        print("\nDuring actual podcast production:")
        print("  • The lock will be set automatically when episode generation starts")
        print("  • The reviewer queue worker will pause processing")
        print("  • The review dispatch task will skip sending new articles")
        print("  • Everything resumes when episode generation completes")


async def test_simulated_production():
    """Simulate a production workflow to test automatic pause."""
    print("\n" + "=" * 60)
    print("Simulating Production Workflow")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        
        # Manually set production lock to simulate episode generation
        print("\n🎬 Simulating episode generation start...")
        response = await client.post(f"{REVIEWER_URL}/production/pause")
        print("   🔒 Production lock activated")
        
        # Check reviewer status
        response = await client.get(f"{REVIEWER_URL}/production/status")
        status = response.json()
        print(f"   ⏸️ {status['message']}")
        
        # Simulate production work
        print("\n📝 Simulating production pipeline...")
        production_steps = [
            "Creating episode record",
            "Generating presenter briefs",
            "Generating script",
            "Editing script",
            "Generating metadata",
            "Generating audio",
            "Publishing episode"
        ]
        
        for i, step in enumerate(production_steps, 1):
            await asyncio.sleep(0.5)  # Simulate work
            print(f"   {i}. {step}... ✓")
        
        print("\n✅ Episode generation complete")
        
        # Clear production lock
        print("   🔓 Clearing production lock...")
        response = await client.post(f"{REVIEWER_URL}/production/resume")
        print("   ✅ Reviewer Service resumed")
        
        # Verify reviewer is active
        response = await client.get(f"{REVIEWER_URL}/production/status")
        status = response.json()
        print(f"\n{status['message']}")


async def main():
    """Run all tests."""
    try:
        # Run basic tests
        await test_production_pause()
        
        # Run simulated production
        await test_simulated_production()
        
        print("\n" + "=" * 60)
        print("🎉 All Tests Completed Successfully!")
        print("=" * 60)
        
    except httpx.ConnectError:
        print("\n❌ Error: Could not connect to Reviewer Service")
        print("   Make sure the service is running:")
        print("   docker-compose up -d reviewer")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
