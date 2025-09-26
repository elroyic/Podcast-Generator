#!/usr/bin/env python3
"""
Comprehensive Test Runner - Run all tests in sequence with detailed reporting.
"""
import asyncio
import subprocess
import sys
import os
import logging
from datetime import datetime
from typing import Dict, List
import json

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Test files
TEST_FILES = [
    {
        "name": "Component Health Tests",
        "file": "test_component_health.py",
        "description": "Test individual service health and basic functionality"
    },
    {
        "name": "Reviewer Pipeline Tests",
        "file": "test_reviewer_pipeline.py",
        "description": "Test the two-tier review architecture"
    },
    {
        "name": "Collections Service Tests",
        "file": "test_collections_service.py",
        "description": "Test feed grouping and collection management"
    },
    {
        "name": "Full Workflow Tests",
        "file": "test_full_workflow.py",
        "description": "Test complete end-to-end podcast generation workflow"
    },
    {
        "name": "Performance and Load Tests",
        "file": "test_performance_load.py",
        "description": "Test system performance under various loads"
    }
]


class TestRunner:
    """Comprehensive test runner for all system tests."""
    
    def __init__(self):
        self.results = {}
        self.start_time = None
        self.end_time = None
    
    async def run_single_test(self, test_info: Dict) -> Dict:
        """Run a single test file."""
        test_name = test_info["name"]
        test_file = test_info["file"]
        description = test_info["description"]
        
        logger.info(f"🚀 Starting {test_name}...")
        logger.info(f"   Description: {description}")
        logger.info(f"   File: {test_file}")
        
        start_time = datetime.utcnow()
        
        try:
            # Run the test
            result = subprocess.run(
                [sys.executable, test_file],
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout per test
            )
            
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            if result.returncode == 0:
                logger.info(f"✅ {test_name} PASSED ({duration:.1f}s)")
                return {
                    "name": test_name,
                    "status": "PASSED",
                    "duration": duration,
                    "return_code": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr
                }
            else:
                logger.error(f"❌ {test_name} FAILED ({duration:.1f}s)")
                return {
                    "name": test_name,
                    "status": "FAILED",
                    "duration": duration,
                    "return_code": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr
                }
                
        except subprocess.TimeoutExpired:
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            logger.error(f"⏰ {test_name} TIMEOUT ({duration:.1f}s)")
            return {
                "name": test_name,
                "status": "TIMEOUT",
                "duration": duration,
                "return_code": -1,
                "stdout": "",
                "stderr": "Test timed out after 10 minutes"
            }
        except Exception as e:
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            logger.error(f"💥 {test_name} ERROR ({duration:.1f}s): {e}")
            return {
                "name": test_name,
                "status": "ERROR",
                "duration": duration,
                "return_code": -1,
                "stdout": "",
                "stderr": str(e)
            }
    
    async def run_all_tests(self) -> Dict:
        """Run all tests in sequence."""
        logger.info("🎯 Starting Comprehensive Test Suite...")
        logger.info(f"   Total Tests: {len(TEST_FILES)}")
        logger.info("")
        
        self.start_time = datetime.utcnow()
        
        for i, test_info in enumerate(TEST_FILES, 1):
            logger.info(f"📋 Test {i}/{len(TEST_FILES)}")
            result = await self.run_single_test(test_info)
            self.results[test_info["name"]] = result
            logger.info("")
        
        self.end_time = datetime.utcnow()
        
        return self.results
    
    def generate_summary_report(self) -> str:
        """Generate a summary report of all tests."""
        if not self.results:
            return "No test results available."
        
        total_duration = (self.end_time - self.start_time).total_seconds()
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results.values() if r["status"] == "PASSED")
        failed_tests = sum(1 for r in self.results.values() if r["status"] == "FAILED")
        timeout_tests = sum(1 for r in self.results.values() if r["status"] == "TIMEOUT")
        error_tests = sum(1 for r in self.results.values() if r["status"] == "ERROR")
        
        report = []
        report.append("=" * 80)
        report.append("COMPREHENSIVE TEST SUITE SUMMARY")
        report.append("=" * 80)
        report.append(f"Generated: {datetime.utcnow().isoformat()}")
        report.append(f"Total Duration: {total_duration:.1f} seconds")
        report.append("")
        
        # Overall Statistics
        report.append("OVERALL STATISTICS")
        report.append("-" * 40)
        report.append(f"Total Tests: {total_tests}")
        report.append(f"Passed: {passed_tests} ✅")
        report.append(f"Failed: {failed_tests} ❌")
        report.append(f"Timeout: {timeout_tests} ⏰")
        report.append(f"Error: {error_tests} 💥")
        report.append(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        report.append("")
        
        # Individual Test Results
        report.append("INDIVIDUAL TEST RESULTS")
        report.append("-" * 40)
        for test_name, result in self.results.items():
            status_icon = {
                "PASSED": "✅",
                "FAILED": "❌",
                "TIMEOUT": "⏰",
                "ERROR": "💥"
            }.get(result["status"], "❓")
            
            report.append(f"{status_icon} {test_name}: {result['status']} ({result['duration']:.1f}s)")
            
            if result["status"] != "PASSED":
                if result["stderr"]:
                    report.append(f"   Error: {result['stderr'][:100]}...")
                if result["return_code"] != 0:
                    report.append(f"   Return Code: {result['return_code']}")
        
        report.append("")
        
        # Performance Summary
        report.append("PERFORMANCE SUMMARY")
        report.append("-" * 40)
        total_test_time = sum(r["duration"] for r in self.results.values())
        avg_test_time = total_test_time / total_tests if total_tests > 0 else 0
        
        report.append(f"Total Test Time: {total_test_time:.1f}s")
        report.append(f"Average Test Time: {avg_test_time:.1f}s")
        report.append(f"Overhead Time: {total_duration - total_test_time:.1f}s")
        report.append("")
        
        # Recommendations
        report.append("RECOMMENDATIONS")
        report.append("-" * 40)
        if passed_tests == total_tests:
            report.append("🎉 All tests passed! System is ready for production.")
        elif passed_tests > total_tests * 0.8:
            report.append("⚠️  Most tests passed. Review failed tests before production.")
        else:
            report.append("🚨 Multiple test failures. System needs significant fixes.")
        
        if timeout_tests > 0:
            report.append("⏰ Some tests timed out. Consider increasing timeouts or optimizing performance.")
        
        if error_tests > 0:
            report.append("💥 Some tests had errors. Check system configuration and dependencies.")
        
        report.append("")
        
        return "\n".join(report)
    
    def generate_detailed_report(self) -> str:
        """Generate a detailed report with full output."""
        if not self.results:
            return "No test results available."
        
        report = []
        report.append("=" * 80)
        report.append("DETAILED TEST SUITE REPORT")
        report.append("=" * 80)
        report.append(f"Generated: {datetime.utcnow().isoformat()}")
        report.append("")
        
        for test_name, result in self.results.items():
            report.append(f"TEST: {test_name}")
            report.append("-" * 60)
            report.append(f"Status: {result['status']}")
            report.append(f"Duration: {result['duration']:.1f} seconds")
            report.append(f"Return Code: {result['return_code']}")
            report.append("")
            
            if result["stdout"]:
                report.append("STDOUT:")
                report.append(result["stdout"])
                report.append("")
            
            if result["stderr"]:
                report.append("STDERR:")
                report.append(result["stderr"])
                report.append("")
            
            report.append("=" * 80)
            report.append("")
        
        return "\n".join(report)
    
    def save_reports(self):
        """Save reports to files."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        
        # Save summary report
        summary_report = self.generate_summary_report()
        summary_filename = f"test_summary_{timestamp}.txt"
        with open(summary_filename, 'w') as f:
            f.write(summary_report)
        logger.info(f"📄 Summary report saved: {summary_filename}")
        
        # Save detailed report
        detailed_report = self.generate_detailed_report()
        detailed_filename = f"test_detailed_{timestamp}.txt"
        with open(detailed_filename, 'w') as f:
            f.write(detailed_report)
        logger.info(f"📄 Detailed report saved: {detailed_filename}")
        
        # Save JSON results
        json_filename = f"test_results_{timestamp}.json"
        with open(json_filename, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        logger.info(f"📄 JSON results saved: {json_filename}")
    
    def print_summary(self):
        """Print a summary to console."""
        summary = self.generate_summary_report()
        print(summary)


async def main():
    """Main test runner function."""
    # Change to the test directory
    test_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(test_dir)
    
    runner = TestRunner()
    
    try:
        # Run all tests
        await runner.run_all_tests()
        
        # Print summary
        runner.print_summary()
        
        # Save reports
        runner.save_reports()
        
        # Determine exit code
        total_tests = len(runner.results)
        passed_tests = sum(1 for r in runner.results.values() if r["status"] == "PASSED")
        
        if passed_tests == total_tests:
            logger.info("🎉 ALL TESTS PASSED!")
            return 0
        else:
            logger.error(f"⚠️  {total_tests - passed_tests} TESTS FAILED!")
            return 1
            
    except KeyboardInterrupt:
        logger.info("🛑 Test suite interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"💥 Test suite failed with error: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
