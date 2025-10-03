#!/usr/bin/env python3
"""
Comprehensive Implementation Review Test Suite
Tests all documented features against actual codebase
"""
import os
import sys
import json
import asyncio
from pathlib import Path
from typing import Dict, List, Any

# Color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(text: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(80)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}\n")

def print_success(text: str):
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")

def print_failure(text: str):
    print(f"{Colors.RED}✗ {text}{Colors.END}")

def print_warning(text: str):
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")

def print_info(text: str):
    print(f"{Colors.BLUE}ℹ {text}{Colors.END}")

class ImplementationReviewTest:
    def __init__(self):
        self.workspace = Path("/workspace")
        self.services_dir = self.workspace / "services"
        self.results = {
            "passed": [],
            "failed": [],
            "warnings": []
        }
    
    def check_file_exists(self, path: Path, description: str) -> bool:
        """Check if a file exists"""
        if path.exists():
            print_success(f"{description}: {path}")
            self.results["passed"].append(description)
            return True
        else:
            print_failure(f"{description}: NOT FOUND - {path}")
            self.results["failed"].append(description)
            return False
    
    def check_code_pattern(self, file_path: Path, pattern: str, description: str) -> bool:
        """Check if a code pattern exists in a file"""
        try:
            if not file_path.exists():
                print_failure(f"{description}: File not found - {file_path}")
                self.results["failed"].append(description)
                return False
            
            content = file_path.read_text()
            if pattern in content:
                print_success(f"{description}")
                self.results["passed"].append(description)
                return True
            else:
                print_failure(f"{description}: Pattern not found in {file_path}")
                self.results["failed"].append(description)
                return False
        except Exception as e:
            print_failure(f"{description}: Error - {e}")
            self.results["failed"].append(description)
            return False
    
    def test_reviewer_architecture(self):
        """Test two-tier reviewer architecture"""
        print_header("Testing Two-Tier Reviewer Architecture")
        
        # Check Light Reviewer service
        self.check_file_exists(
            self.services_dir / "light-reviewer" / "main.py",
            "Light Reviewer Service"
        )
        
        # Check Heavy Reviewer service
        self.check_file_exists(
            self.services_dir / "heavy-reviewer" / "main.py",
            "Heavy Reviewer Service"
        )
        
        # Check Reviewer Orchestrator
        self.check_file_exists(
            self.services_dir / "reviewer" / "main.py",
            "Reviewer Orchestrator Service"
        )
        
        # Check confidence threshold logic
        self.check_code_pattern(
            self.services_dir / "reviewer" / "main.py",
            "DEFAULT_CONF_THRESHOLD",
            "Confidence Threshold Configuration"
        )
        
        self.check_code_pattern(
            self.services_dir / "reviewer" / "main.py",
            "DEFAULT_HEAVY_CONF_THRESHOLD",
            "Heavy Confidence Threshold Configuration"
        )
        
        # Check two-tier routing
        self.check_code_pattern(
            self.services_dir / "reviewer" / "main.py",
            "generate_light_review",
            "Light Review Function"
        )
        
        self.check_code_pattern(
            self.services_dir / "reviewer" / "main.py",
            "generate_heavy_review",
            "Heavy Review Function"
        )
    
    def test_deduplication_system(self):
        """Test deduplication implementation"""
        print_header("Testing Deduplication System")
        
        # Check deduplication in news feed service
        self.check_code_pattern(
            self.services_dir / "news-feed" / "main.py",
            "reviewer:fingerprints",
            "Redis Fingerprint Storage Key"
        )
        
        self.check_code_pattern(
            self.services_dir / "news-feed" / "main.py",
            "DEDUP_ENABLED",
            "Deduplication Toggle Configuration"
        )
        
        self.check_code_pattern(
            self.services_dir / "news-feed" / "main.py",
            "DEDUP_TTL",
            "Deduplication TTL Configuration"
        )
        
        self.check_code_pattern(
            self.services_dir / "news-feed" / "main.py",
            "fingerprint",
            "Fingerprint Generation Logic"
        )
    
    def test_cadence_management(self):
        """Test cadence management system"""
        print_header("Testing Cadence Management System")
        
        # Check CadenceManager class
        self.check_code_pattern(
            self.services_dir / "ai-overseer" / "app" / "services.py",
            "class CadenceManager",
            "CadenceManager Class"
        )
        
        self.check_code_pattern(
            self.services_dir / "ai-overseer" / "app" / "services.py",
            "acquire_group_lock",
            "Group Lock Acquisition"
        )
        
        self.check_code_pattern(
            self.services_dir / "ai-overseer" / "app" / "services.py",
            "release_group_lock",
            "Group Lock Release"
        )
        
        self.check_code_pattern(
            self.services_dir / "ai-overseer" / "app" / "services.py",
            "_determine_cadence_bucket",
            "Adaptive Cadence Logic"
        )
        
        # Check API endpoint
        self.check_code_pattern(
            self.services_dir / "ai-overseer" / "main.py",
            "/cadence/status",
            "Cadence Status API Endpoint"
        )
    
    def test_dashboard_pages(self):
        """Test all dashboard pages"""
        print_header("Testing Dashboard Pages")
        
        templates_dir = self.services_dir / "api-gateway" / "templates"
        
        dashboards = [
            ("dashboard.html", "Main Dashboard"),
            ("groups.html", "Podcast Groups Dashboard"),
            ("reviewer-dashboard.html", "Reviewer Dashboard"),
            ("presenter-management.html", "Presenter Management"),
            ("news-feed-dashboard.html", "News Feed Dashboard"),
            ("collections-dashboard.html", "Collections Dashboard"),
            ("writers.html", "Writers Dashboard"),
            ("episodes.html", "Episodes Dashboard"),
            ("login.html", "Login Page")
        ]
        
        for filename, description in dashboards:
            self.check_file_exists(templates_dir / filename, description)
    
    def test_api_endpoints(self):
        """Test API endpoint implementations"""
        print_header("Testing API Endpoints")
        
        api_gateway = self.services_dir / "api-gateway" / "main.py"
        
        endpoints = [
            ("/api/reviewer/config", "Reviewer Config Endpoint (GET)"),
            ("/api/reviewer/metrics", "Reviewer Metrics Endpoint"),
            ("/api/reviewer/scale/light", "Reviewer Scaling Endpoint"),
            ("/api/cadence/status", "Cadence Status Endpoint"),
            ("/api/podcast-groups", "Podcast Groups API"),
            ("/api/presenters", "Presenters API"),
            ("/api/writers", "Writers API"),
            ("/api/news-feeds", "News Feeds API"),
            ("/api/collections", "Collections API"),
            ("/api/episodes", "Episodes API"),
        ]
        
        for endpoint, description in endpoints:
            self.check_code_pattern(api_gateway, endpoint, description)
    
    def test_service_implementations(self):
        """Test core service implementations"""
        print_header("Testing Core Services")
        
        services = [
            ("news-feed", "News Feed Service"),
            ("reviewer", "Reviewer Service"),
            ("light-reviewer", "Light Reviewer Service"),
            ("heavy-reviewer", "Heavy Reviewer Service"),
            ("text-generation", "Text Generation Service"),
            ("writer", "Writer Service"),
            ("presenter", "Presenter Service"),
            ("editor", "Editor Service"),
            ("collections", "Collections Service"),
            ("publishing", "Publishing Service"),
            ("ai-overseer", "AI Overseer Service"),
        ]
        
        for service_name, description in services:
            self.check_file_exists(
                self.services_dir / service_name / "main.py",
                f"{description} Main Module"
            )
    
    def test_docker_configuration(self):
        """Test Docker configuration"""
        print_header("Testing Docker Configuration")
        
        self.check_file_exists(
            self.workspace / "docker-compose.yml",
            "Docker Compose Configuration"
        )
        
        # Check for service definitions
        docker_compose = self.workspace / "docker-compose.yml"
        if docker_compose.exists():
            content = docker_compose.read_text()
            
            services = [
                "light-reviewer",
                "heavy-reviewer",
                "reviewer",
                "news-feed",
                "ai-overseer",
                "text-generation",
                "presenter",
                "writer",
                "editor",
                "collections",
                "publishing",
                "api-gateway",
            ]
            
            for service in services:
                if service in content:
                    print_success(f"Docker service defined: {service}")
                    self.results["passed"].append(f"Docker service: {service}")
                else:
                    print_warning(f"Docker service not found: {service}")
                    self.results["warnings"].append(f"Docker service: {service}")
    
    def test_workflow_components(self):
        """Test workflow components"""
        print_header("Testing Workflow Components")
        
        # RSS Feed Ingestion
        self.check_code_pattern(
            self.services_dir / "news-feed" / "main.py",
            "feedparser",
            "RSS Feed Parsing"
        )
        
        # Article Review
        self.check_code_pattern(
            self.services_dir / "reviewer" / "main.py",
            "review-article",
            "Article Review Endpoint"
        )
        
        # Collection Building
        self.check_code_pattern(
            self.services_dir / "collections" / "main.py",
            "Collection",
            "Collection Model Usage"
        )
        
        # Script Generation
        self.check_code_pattern(
            self.services_dir / "text-generation" / "main.py",
            "generate",
            "Script Generation Endpoint"
        )
        
        # Audio Generation
        self.check_code_pattern(
            self.services_dir / "presenter" / "main.py",
            "generate-audio",
            "Audio Generation Endpoint"
        )
    
    def test_placeholder_code(self):
        """Check for placeholder code"""
        print_header("Scanning for Placeholder Code")
        
        placeholder_patterns = [
            "TODO",
            "FIXME",
            "PLACEHOLDER",
            "coming soon",
            "not implemented"
        ]
        
        found_placeholders = []
        
        for pattern in placeholder_patterns:
            for py_file in self.services_dir.rglob("*.py"):
                if "archive" in str(py_file) or "__pycache__" in str(py_file):
                    continue
                
                try:
                    content = py_file.read_text()
                    if pattern.lower() in content.lower():
                        found_placeholders.append(f"{py_file.name}: {pattern}")
                except:
                    pass
        
        if found_placeholders:
            print_warning(f"Found {len(found_placeholders)} placeholder markers:")
            for placeholder in found_placeholders[:10]:  # Show first 10
                print(f"  - {placeholder}")
            self.results["warnings"].extend(found_placeholders)
        else:
            print_success("No critical placeholder code found")
            self.results["passed"].append("No placeholder code")
    
    def test_configuration_files(self):
        """Test configuration and documentation"""
        print_header("Testing Configuration Files")
        
        config_files = [
            ("Docs/Current/Workflow.md", "Workflow Documentation"),
            ("Docs/Current/ReviewerEnhancement.md", "Reviewer Enhancement Spec"),
            ("Docs/Current/Missing-Functionality.md", "Missing Functionality Doc"),
            ("docker-compose.yml", "Docker Compose Config"),
            ("shared/models.py", "Shared Database Models"),
            ("shared/schemas.py", "Shared API Schemas"),
        ]
        
        for file_path, description in config_files:
            self.check_file_exists(self.workspace / file_path, description)
    
    def generate_report(self):
        """Generate final test report"""
        print_header("Test Report Summary")
        
        total_tests = len(self.results["passed"]) + len(self.results["failed"])
        passed = len(self.results["passed"])
        failed = len(self.results["failed"])
        warnings = len(self.results["warnings"])
        
        pass_rate = (passed / total_tests * 100) if total_tests > 0 else 0
        
        print(f"\n{Colors.BOLD}Total Tests Run:{Colors.END} {total_tests}")
        print(f"{Colors.GREEN}{Colors.BOLD}Passed:{Colors.END} {passed} ({pass_rate:.1f}%)")
        print(f"{Colors.RED}{Colors.BOLD}Failed:{Colors.END} {failed}")
        print(f"{Colors.YELLOW}{Colors.BOLD}Warnings:{Colors.END} {warnings}")
        
        if failed > 0:
            print(f"\n{Colors.RED}{Colors.BOLD}Failed Tests:{Colors.END}")
            for item in self.results["failed"][:20]:  # Show first 20
                print(f"  • {item}")
        
        if warnings > 0 and warnings <= 10:
            print(f"\n{Colors.YELLOW}{Colors.BOLD}Warnings:{Colors.END}")
            for item in self.results["warnings"]:
                print(f"  • {item}")
        
        print(f"\n{Colors.BOLD}Overall Status:{Colors.END}", end=" ")
        if pass_rate >= 90:
            print(f"{Colors.GREEN}EXCELLENT{Colors.END}")
        elif pass_rate >= 75:
            print(f"{Colors.GREEN}GOOD{Colors.END}")
        elif pass_rate >= 60:
            print(f"{Colors.YELLOW}FAIR{Colors.END}")
        else:
            print(f"{Colors.RED}NEEDS IMPROVEMENT{Colors.END}")
        
        # Save report to file
        report_file = self.workspace / "test_report.json"
        with open(report_file, "w") as f:
            json.dump({
                "timestamp": "2025-09-30",
                "total_tests": total_tests,
                "passed": passed,
                "failed": failed,
                "warnings": warnings,
                "pass_rate": pass_rate,
                "passed_tests": self.results["passed"],
                "failed_tests": self.results["failed"],
                "warnings_list": self.results["warnings"]
            }, f, indent=2)
        
        print(f"\n{Colors.BLUE}Full report saved to: {report_file}{Colors.END}")
    
    def run_all_tests(self):
        """Run all test suites"""
        print(f"\n{Colors.BOLD}{Colors.BLUE}")
        print("=" * 80)
        print("IMPLEMENTATION REVIEW TEST SUITE".center(80))
        print("=" * 80)
        print(f"{Colors.END}\n")
        
        self.test_reviewer_architecture()
        self.test_deduplication_system()
        self.test_cadence_management()
        self.test_dashboard_pages()
        self.test_api_endpoints()
        self.test_service_implementations()
        self.test_docker_configuration()
        self.test_workflow_components()
        self.test_placeholder_code()
        self.test_configuration_files()
        
        self.generate_report()

if __name__ == "__main__":
    tester = ImplementationReviewTest()
    tester.run_all_tests()