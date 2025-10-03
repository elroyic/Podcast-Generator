#!/usr/bin/env python3
"""
Verify that all services are exposing worker and review metrics correctly.
"""
import httpx
import sys
from typing import Dict, List

# Service endpoints
SERVICES = {
    "News Feed": "http://localhost:8001/metrics/prometheus",
    "Reviewer": "http://localhost:8013/metrics/prometheus",
    "Light Reviewer": "http://localhost:8007/metrics/prometheus",
    "Heavy Reviewer": "http://localhost:8011/metrics/prometheus",
    "AI Overseer": "http://localhost:8000/metrics/prometheus",
    "Collections": "http://localhost:8014/metrics/prometheus",
    "Presenter": "http://localhost:8004/metrics/prometheus",
    "Writer": "http://localhost:8003/metrics/prometheus",
    "Editor": "http://localhost:8009/metrics/prometheus",
    "Publishing": "http://localhost:8005/metrics/prometheus",
}

# Expected metrics for each service
EXPECTED_METRICS = {
    "News Feed": ["news_feed_workers_active", "news_feed_articles_per_hour"],
    "Reviewer": ["reviewer_workers_active", "reviewer_light_total", "reviewer_heavy_total"],
    "Light Reviewer": ["light_reviewer_workers_active", "light_reviewer_reviews_per_hour"],
    "Heavy Reviewer": ["heavy_reviewer_workers_active", "heavy_reviewer_reviews_per_hour"],
    "AI Overseer": ["overseer_workers_active", "overseer_episodes_generated_total"],
    "Collections": ["collections_workers_active", "collections_active_total"],
    "Presenter": ["presenter_workers_active", "presenter_reviews_per_hour"],
    "Writer": ["writer_workers_active", "writer_scripts_per_hour"],
    "Editor": ["editor_workers_active", "editor_scripts_per_hour"],
    "Publishing": ["publishing_workers_active", "publishing_success_total"],
}


def parse_prometheus_metrics(content: str) -> Dict[str, float]:
    """Parse Prometheus metrics from text content."""
    metrics = {}
    for line in content.split('\n'):
        line = line.strip()
        if line and not line.startswith('#'):
            # Parse metric line: metric_name{labels} value
            parts = line.split()
            if len(parts) >= 2:
                metric_name = parts[0].split('{')[0]  # Remove labels
                try:
                    value = float(parts[1])
                    metrics[metric_name] = value
                except ValueError:
                    pass
    return metrics


def verify_service(service_name: str, url: str, expected: List[str]) -> bool:
    """Verify a service's metrics endpoint."""
    print(f"\n{'='*60}")
    print(f"Checking: {service_name}")
    print(f"URL: {url}")
    print(f"{'='*60}")
    
    try:
        response = httpx.get(url, timeout=10.0)
        response.raise_for_status()
        
        metrics = parse_prometheus_metrics(response.text)
        
        print(f"✅ Service is responding")
        print(f"📊 Metrics found: {len(metrics)}")
        
        # Check for expected metrics
        all_found = True
        for expected_metric in expected:
            if expected_metric in metrics:
                print(f"  ✅ {expected_metric}: {metrics[expected_metric]}")
            else:
                print(f"  ❌ MISSING: {expected_metric}")
                all_found = False
        
        # Show additional metrics
        other_metrics = [m for m in metrics.keys() if m not in expected]
        if other_metrics:
            print(f"\n📈 Additional metrics ({len(other_metrics)}):")
            for metric in sorted(other_metrics)[:5]:  # Show first 5
                print(f"  • {metric}: {metrics[metric]}")
            if len(other_metrics) > 5:
                print(f"  ... and {len(other_metrics) - 5} more")
        
        return all_found
        
    except httpx.HTTPError as e:
        print(f"❌ HTTP Error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    """Main verification function."""
    print("🔍 Verifying Metrics Implementation")
    print("=" * 60)
    
    results = {}
    for service_name, url in SERVICES.items():
        expected = EXPECTED_METRICS.get(service_name, [])
        results[service_name] = verify_service(service_name, url, expected)
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 VERIFICATION SUMMARY")
    print(f"{'='*60}")
    
    total_services = len(results)
    passed_services = sum(1 for v in results.values() if v)
    failed_services = total_services - passed_services
    
    for service_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {service_name}")
    
    print(f"\n{'='*60}")
    print(f"Total Services: {total_services}")
    print(f"Passed: {passed_services}")
    print(f"Failed: {failed_services}")
    
    if failed_services == 0:
        print("✅ All metrics verified successfully!")
        return 0
    else:
        print(f"⚠️ {failed_services} service(s) failed verification")
        return 1


if __name__ == "__main__":
    sys.exit(main())


