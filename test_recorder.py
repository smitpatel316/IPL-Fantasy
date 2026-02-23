#!/usr/bin/env python3
"""
Test Recorder and Analyzer
Records test execution and analyzes results to provide app improvement feedback.
"""

import os
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

class TestRecorder:
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.test_results_dir = self.project_root / "test-results"
        self.test_results_dir.mkdir(exist_ok=True)
        self.videos_dir = self.test_results_dir / "videos"
        self.videos_dir.mkdir(exist_ok=True)
        self.screenshots_dir = self.test_results_dir / "screenshots"
        self.screenshots_dir.mkdir(exist_ok=True)

    def run_xcuitests(self, scheme: str = "IPLFantasyPro", device: str = "iPhone 15") -> Dict:
        """Run XCUITests and capture results"""
        print(f"Running XCUITests for {scheme}...")

        cmd = [
            "xcodebuild",
            "test",
            "-scheme", scheme,
            "-destination", f"platform=iOS Simulator,name={device}",
            "-derivedDataPath", str(self.project_root / "build"),
            "-resultBundlePath", str(self.test_results_dir / f"XCTest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xcresult")
        ]

        start_time = datetime.now()

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            duration = (datetime.now() - start_time).total_seconds()

            return {
                "success": result.returncode == 0,
                "duration": duration,
                "output": result.stdout[-5000:],  # Last 5000 chars
                "errors": result.stderr[-2000:] if result.stderr else None,
                "timestamp": datetime.now().isoformat()
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "duration": 600,
                "error": "Test timeout",
                "timestamp": datetime.now().isoformat()
            }

    def run_playwright_tests(self) -> Dict:
        """Run Playwright E2E tests"""
        print("Running Playwright E2E tests...")

        e2e_dir = self.project_root / "e2e"
        if not e2e_dir.exists():
            return {"success": False, "error": "E2E directory not found"}

        cmd = ["npx", "playwright", "test", "--reporter=json"]

        start_time = datetime.now()

        try:
            result = subprocess.run(
                cmd,
                cwd=str(e2e_dir),
                capture_output=True,
                text=True,
                timeout=300
            )

            duration = (datetime.now() - start_time).total_seconds()

            # Try to find test results
            test_results = []
            for file in e2e_dir.glob("playwright-report/*.json"):
                try:
                    with open(file) as f:
                        test_results.extend(json.load(f))
                except:
                    pass

            return {
                "success": result.returncode == 0,
                "duration": duration,
                "test_count": len(test_results),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {"success": False, "error": str(e), "timestamp": datetime.now().isoformat()}

    def run_backend_tests(self) -> Dict:
        """Run backend tests"""
        print("Running backend tests...")

        backend_dir = self.project_root / "backend"
        if not backend_dir.exists():
            return {"success": False, "error": "Backend directory not found"}

        cmd = ["npm", "test", "--", "--json"]

        start_time = datetime.now()

        try:
            result = subprocess.run(
                cmd,
                cwd=str(backend_dir),
                capture_output=True,
                text=True,
                timeout=120
            )

            duration = (datetime.now() - start_time).total_seconds()

            # Parse coverage if available
            coverage = self._parse_coverage(result.stdout)

            return {
                "success": result.returncode == 0,
                "duration": duration,
                "coverage": coverage,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {"success": False, "error": str(e), "timestamp": datetime.now().isoformat()}

    def _parse_coverage(self, output: str) -> Optional[Dict]:
        """Parse coverage from test output"""
        lines = output.split('\n')
        coverage = {}

        for line in lines:
            if 'All files' in line:
                parts = line.split('|')
                if len(parts) >= 6:
                    try:
                        coverage['lines'] = parts[4].strip().replace('%', '')
                        coverage['branches'] = parts[3].strip().replace('%', '')
                        coverage['functions'] = parts[5].strip().replace('%', '')
                    except:
                        pass

        return coverage if coverage else None

    def analyze_improvements(self, test_results: Dict) -> List[Dict]:
        """Analyze test results and suggest improvements"""
        suggestions = []

        # Analyze XCUITest results
        if 'errors' in test_results.get('xcuitests', {}):
            errors = test_results['xcuitests']['errors']
            if errors:
                suggestions.append({
                    "category": "iOS Tests",
                    "issue": "Test failures detected",
                    "suggestion": "Review failed tests and fix UI elements",
                    "priority": "high"
                })

        # Analyze E2E results
        e2e = test_results.get('e2e', {})
        if not e2e.get('success', True):
            suggestions.append({
                "category": "E2E Tests",
                "issue": "End-to-end tests failing",
                "suggestion": "Check API connectivity and UI responsiveness",
                "priority": "high"
            })

        # Analyze backend coverage
        backend = test_results.get('backend', {})
        coverage = backend.get('coverage', {})

        if coverage:
            try:
                line_coverage = float(coverage.get('lines', 0))
                if line_coverage < 50:
                    suggestions.append({
                        "category": "Backend",
                        "issue": f"Low test coverage: {line_coverage}%",
                        "suggestion": "Add more unit tests for uncovered routes",
                        "priority": "medium"
                    })
            except:
                pass

        # Default suggestions
        if not suggestions:
            suggestions.append({
                "category": "General",
                "issue": "Tests passing",
                "suggestion": "Consider adding more edge case tests",
                "priority": "low"
            })

        return suggestions

    def run_all_tests(self) -> Dict:
        """Run all tests and generate report"""
        print("=" * 50)
        print("Running All Tests with Recording")
        print("=" * 50)

        results = {
            "timestamp": datetime.now().isoformat(),
            "xcuitests": self.run_xcuitests(),
            "e2e": self.run_playwright_tests(),
            "backend": self.run_backend_tests()
        }

        # Analyze and suggest improvements
        results['suggestions'] = self.analyze_improvements(results)

        # Save results
        results_file = self.test_results_dir / f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)

        print("\n" + "=" * 50)
        print("Test Analysis Results")
        print("=" * 50)

        for suggestion in results['suggestions']:
            print(f"\n[{suggestion['priority'].upper()}] {suggestion['category']}")
            print(f"  Issue: {suggestion['issue']}")
            print(f"  Suggestion: {suggestion['suggestion']}")

        print(f"\nResults saved to: {results_file}")

        return results


def main():
    # Get the IPL-Fantasy directory
    current_file = os.path.abspath(__file__)
    project_root = os.path.dirname(current_file)  # test_recorder.py is at root level

    recorder = TestRecorder(project_root)

    if len(sys.argv) > 1:
        if sys.argv[1] == 'xcuitest':
            result = recorder.run_xcuitests()
            print(json.dumps(result, indent=2))
        elif sys.argv[1] == 'e2e':
            result = recorder.run_playwright_tests()
            print(json.dumps(result, indent=2))
        elif sys.argv[1] == 'backend':
            result = recorder.run_backend_tests()
            print(json.dumps(result, indent=2))
    else:
        # Run all tests
        recorder.run_all_tests()


if __name__ == "__main__":
    main()
