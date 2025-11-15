#!/usr/bin/env python3
"""
Converts OPA test results to JUnit XML report.

Usage:
    python opa_test_to_junit.py --test-json <test.json> --output-xml <test-results.xml>

Example:
    python opa_test_to_junit.py --test-json test.json --output-xml test-results.xml
"""

import argparse
import json
import socket
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime


def _nanos_to_seconds(nanos):
    """Convert nanoseconds to seconds"""
    return round(nanos / 1_000_000_000, 3)


def create_test_report(test_data):
    """Create test report with policies as test suites and individual tests as test cases"""
    # Group tests by policy
    policy_groups = defaultdict(
        lambda: {
            "tests": [],
            "package": None,
            "duration": 0,
            "failures": 0,
            "errors": 0,
            "skipped": 0,
        }
    )

    for test in test_data:
        # Extract policy file from package name
        package_parts = test["package"].split(".")
        if package_parts[0] == "data" and len(package_parts) > 1:
            package_parts = package_parts[1:]

        if package_parts and package_parts[-1].endswith("_test"):
            package_parts[-1] = package_parts[-1][:-5]

        policy_name = ".".join(package_parts)

        group = policy_groups[policy_name]
        group["tests"].append(test)
        group["package"] = policy_name
        group["duration"] += test["duration"]

        if test.get("fail", False):
            group["failures"] += 1
        if test.get("error"):
            group["errors"] += 1
        if test.get("skip"):
            group["skipped"] += 1

    # Calculate totals
    total_tests = len(test_data)
    total_failures = sum(g["failures"] for g in policy_groups.values())
    total_errors = sum(g["errors"] for g in policy_groups.values())
    total_skipped = sum(g["skipped"] for g in policy_groups.values())
    total_duration = sum(g["duration"] for g in policy_groups.values())

    # Create root testsuites element
    testsuites = ET.Element("testsuites")
    testsuites.set("name", "OPA Policy Test Report")
    testsuites.set("timestamp", datetime.now().isoformat())
    testsuites.set("tests", str(total_tests))
    testsuites.set("failures", str(total_failures))
    testsuites.set("errors", str(total_errors))
    testsuites.set("skipped", str(total_skipped))
    testsuites.set("time", str(_nanos_to_seconds(total_duration)))

    # Create a test suite for each policy
    for policy_name in sorted(policy_groups.keys()):
        group = policy_groups[policy_name]

        # Create testsuite
        testsuite = ET.Element("testsuite")
        testsuite.set("name", f"{policy_name}")
        testsuite.set("package", policy_name)
        testsuite.set("hostname", socket.gethostname())
        testsuite.set("timestamp", datetime.now().isoformat())
        testsuite.set("tests", str(len(group["tests"])))
        testsuite.set("failures", str(group["failures"]))
        testsuite.set("errors", str(group["errors"]))
        testsuite.set("skipped", str(group["skipped"]))
        testsuite.set("time", str(_nanos_to_seconds(group["duration"])))

        # Add properties
        properties = ET.SubElement(testsuite, "properties")
        ET.SubElement(
            properties,
            "property",
            {"name": "policy", "value": policy_name},
        )

        # Add individual test cases
        for test in group["tests"]:
            testcase = ET.SubElement(testsuite, "testcase")
            # testcase.set("classname", policy_name)
            testcase.set("name", test["name"])
            testcase.set("file", test["location"]["file"])
            testcase.set("line", str(test["location"]["row"]))
            testcase.set("time", str(_nanos_to_seconds(test["duration"])))

            # Add failure information if test failed
            if test.get("fail", False):
                failure = ET.SubElement(testcase, "failure")
                failure.set("message", f"Test {test['name']} failed")
                failure.set("type", "AssertionError")

            # Add error information if test had error
            if test.get("error"):
                error = ET.SubElement(testcase, "error")
                error.set("type", test["error"].get("code", "Error"))
                error.set("message", test["error"].get("message", "Test error"))

            # Add skipped information if test was skipped
            if test.get("skip"):
                skipped = ET.SubElement(testcase, "skipped")
                if isinstance(test["skip"], dict):
                    skipped.set("message", test["skip"].get("message", "Test skipped"))

        testsuites.append(testsuite)

    return testsuites


def main():
    parser = argparse.ArgumentParser(
        description="Convert OPA test results to JUnit XML report",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s --test-json test.json --output-xml test-results.xml
        """,
    )

    parser.add_argument(
        "--test-json",
        type=str,
        required=True,
        help="Path to OPA test results JSON file (from 'opa test --format=json')",
    )
    parser.add_argument(
        "--output-xml",
        type=str,
        required=True,
        help="Path to output JUnit XML file",
    )
    parser.add_argument("-v", "--version", action="version", version="%(prog)s 1.0.0")

    args = parser.parse_args()

    try:
        # Load test data
        with open(args.test_json, "r") as f:
            test_data = json.load(f)

        # Create JUnit XML report
        testsuites = create_test_report(test_data)

        # Write XML with proper formatting
        tree = ET.ElementTree(testsuites)
        ET.indent(tree, space="  ", level=0)
        tree.write(args.output_xml, encoding="utf-8", xml_declaration=True)

        # Calculate totals
        total_tests = len(test_data)
        total_failures = sum(1 for test in test_data if test.get("fail", False))
        total_errors = sum(1 for test in test_data if test.get("error"))
        total_skipped = sum(1 for test in test_data if test.get("skip"))

        # Print summary
        print(f"Test JUnit report created: {args.output_xml}")
        print("\nTest Summary:")
        print(f"- Total tests: {total_tests}")
        print(
            f"- Passed: {total_tests - total_failures - total_errors - total_skipped}"
        )
        print(f"- Failed: {total_failures}")
        print(f"- Errors: {total_errors}")
        print(f"- Skipped: {total_skipped}")

        # Print policy breakdown
        policy_groups = defaultdict(list)
        for test in test_data:
            package_parts = test["package"].split(".")
            if package_parts[0] == "data" and len(package_parts) > 1:
                package_parts = package_parts[1:]
            if package_parts and package_parts[-1].endswith("_test"):
                package_parts[-1] = package_parts[-1][:-5]
            policy_name = ".".join(package_parts)
            policy_groups[policy_name].append(test)

        print("\nPolicy Breakdown:")
        for policy_name in sorted(policy_groups.keys()):
            tests = policy_groups[policy_name]
            failures = sum(1 for t in tests if t.get("fail", False))
            errors = sum(1 for t in tests if t.get("error"))

            status_icon = "✅" if failures == 0 and errors == 0 else "❌"
            print(f"{status_icon} {policy_name}: {len(tests)} tests")

        sys.exit(0)

    except FileNotFoundError as e:
        print(f"Error: File not found - {e}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON format - {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
