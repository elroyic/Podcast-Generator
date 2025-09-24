#!/usr/bin/env python3
"""
Test script for local publishing solution.
This script tests the MinIO and file server setup.
"""

import os
import sys
import time
import requests
from minio import Minio
from minio.error import S3Error

def test_minio_connection():
    """Test MinIO connection and bucket creation."""
    print("Testing MinIO connection...")
    
    try:
        # Initialize MinIO client
        minio_client = Minio(
            "localhost:9000",
            access_key="minioadmin",
            secret_key="minioadmin",
            secure=False
        )
        
        # Test bucket creation
        bucket_name = "podcast-storage"
        if not minio_client.bucket_exists(bucket_name):
            minio_client.make_bucket(bucket_name)
            print(f"✓ Created bucket: {bucket_name}")
        else:
            print(f"✓ Bucket already exists: {bucket_name}")
        
        # Test file upload
        test_file = "/tmp/test_audio.wav"
        with open(test_file, "w") as f:
            f.write("test audio content")
        
        object_key = "test/episode/test.wav"
        minio_client.fput_object(
            bucket_name,
            object_key,
            test_file,
            content_type="audio/wav"
        )
        print(f"✓ Successfully uploaded test file to MinIO")
        
        # Clean up
        os.remove(test_file)
        minio_client.remove_object(bucket_name, object_key)
        print("✓ Cleaned up test files")
        
        return True
        
    except Exception as e:
        print(f"✗ MinIO test failed: {e}")
        return False

def test_file_server():
    """Test file server accessibility."""
    print("Testing file server...")
    
    try:
        # Test health endpoint
        response = requests.get("http://localhost:8080/health", timeout=5)
        if response.status_code == 200:
            print("✓ File server health check passed")
        else:
            print(f"✗ File server health check failed: {response.status_code}")
            return False
        
        # Test directory listing
        response = requests.get("http://localhost:8080/", timeout=5)
        if response.status_code == 200:
            print("✓ File server directory listing accessible")
        else:
            print(f"✗ File server directory listing failed: {response.status_code}")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ File server test failed: {e}")
        return False

def test_publishing_service():
    """Test publishing service endpoints."""
    print("Testing publishing service...")
    
    try:
        # Test health endpoint
        response = requests.get("http://localhost:8005/health", timeout=5)
        if response.status_code == 200:
            print("✓ Publishing service health check passed")
        else:
            print(f"✗ Publishing service health check failed: {response.status_code}")
            return False
        
        # Test platforms endpoint
        response = requests.get("http://localhost:8005/platforms", timeout=5)
        if response.status_code == 200:
            print("✓ Publishing service platforms endpoint accessible")
        else:
            print(f"✗ Publishing service platforms endpoint failed: {response.status_code}")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ Publishing service test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("=== Local Publishing Solution Test ===\n")
    
    # Wait a bit for services to start
    print("Waiting for services to start...")
    time.sleep(10)
    
    tests = [
        ("MinIO Connection", test_minio_connection),
        ("File Server", test_file_server),
        ("Publishing Service", test_publishing_service)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        result = test_func()
        results.append((test_name, result))
    
    print("\n=== Test Results ===")
    all_passed = True
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{test_name}: {status}")
        if not result:
            all_passed = False
    
    if all_passed:
        print("\n🎉 All tests passed! Local publishing solution is working.")
    else:
        print("\n❌ Some tests failed. Check the logs above for details.")
        sys.exit(1)

if __name__ == "__main__":
    main()