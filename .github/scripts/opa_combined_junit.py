#!/usr/bin/env python3
"""
Combines OPA test results and coverage data into a single JUnit XML report.

Usage:
    python opa_combined_junit.py --test-json <test.json> --coverage-json <coverage.json> --output-xml <combined-results.xml> [--coverage-threshold <threshold>]

Example:
    python opa_combined_junit.py --test-json test.json --coverage-json coverage.json --output-xml combined-results.xml --coverage-threshold 90.0
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


def _round_percentage(value):
    """Round percentage to 2 decimal places"""
    return round(value, 2)


def create_test_summary_and_suites(test_data):
    """Create a test summary suite with policies as test cases and tests in system-out"""
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

    testsuites = []

    # Calculate totals
    total_tests = len(test_data)
    total_failures = sum(g["failures"] for g in policy_groups.values())
    total_errors = sum(g["errors"] for g in policy_groups.values())
    total_skipped = sum(g["skipped"] for g in policy_groups.values())
    total_duration = sum(g["duration"] for g in policy_groups.values())

    # Create single "Test" suite with policies as test cases
    test_suite = ET.Element("testsuite")
    test_suite.set("name", f"Test ({total_tests} tests, {total_failures} failures)")
    test_suite.set("package", "tests")
    test_suite.set("hostname", socket.gethostname())
    test_suite.set("timestamp", datetime.now().isoformat())
    test_suite.set("tests", str(len(policy_groups)))  # Number of policies
    test_suite.set(
        "failures",
        str(
            sum(
                1
                for g in policy_groups.values()
                if g["failures"] > 0 or g["errors"] > 0
            )
        ),
    )
    test_suite.set("errors", "0")
    test_suite.set("skipped", "0")
    test_suite.set("time", str(_nanos_to_seconds(total_duration)))

    # Add properties with summary info
    properties = ET.SubElement(test_suite, "properties")
    ET.SubElement(
        properties,
        "property",
        {"name": "total_policies", "value": str(len(policy_groups))},
    )
    ET.SubElement(
        properties,
        "property",
        {"name": "total_tests", "value": str(total_tests)},
    )
    ET.SubElement(
        properties,
        "property",
        {
            "name": "passed_tests",
            "value": str(total_tests - total_failures - total_errors),
        },
    )

    # Create a test case for each policy
    for policy_name in sorted(policy_groups.keys()):
        group = policy_groups[policy_name]

        # Create a testcase for this policy
        policy_testcase = ET.SubElement(test_suite, "testcase")
        policy_testcase.set("classname", "tests")
        policy_testcase.set(
            "name",
            f"{policy_name}: {len(group['tests'])} tests, {group['failures']} failures, {group['errors']} errors, {group['skipped']} skipped",
        )
        policy_testcase.set("time", str(_nanos_to_seconds(group["duration"])))

        # If there are failures or errors in this policy, mark it as failed
        if group["failures"] > 0 or group["errors"] > 0:
            failure = ET.SubElement(policy_testcase, "failure")
            failure.set(
                "message",
                f"Policy has {group['failures']} failures and {group['errors']} errors",
            )
            failure.set("type", "PolicyTestFailure")

        # Add system-out with individual test details
        system_out = ET.SubElement(policy_testcase, "system-out")
        test_details = []

        for test in group["tests"]:
            status = "✅"
            if test.get("fail", False):
                status = "❌"
            elif test.get("error"):
                status = "⚠️"
            elif test.get("skip"):
                status = "⏭️"

            test_details.append(
                f"{status} {test['name']} ({_nanos_to_seconds(test['duration'])}s)"
            )

            if test.get("fail", False) or test.get("error"):
                # Add failure/error details
                if test.get("error"):
                    test_details.append(
                        f"   Error: {test['error'].get('message', 'Unknown error')}"
                    )

        system_out.text = "\n".join(test_details)

    testsuites.append(test_suite)

    return testsuites


def create_coverage_summary_and_suites(coverage_data, coverage_threshold):
    """Create a single coverage summary suite with policies as test cases"""
    # Group files by policy area
    policy_groups = defaultdict(
        lambda: {
            "files": [],
            "total_coverage": 0,
            "file_count": 0,
            "total_lines": 0,
            "covered_lines": 0,
            "not_covered_lines": 0,
        }
    )
    policy_files = [f for f in coverage_data["files"] if not f.endswith("_test.rego")]

    for file_path in policy_files:
        parts = file_path.split("/")
        if len(parts) >= 3 and parts[0] == "policy":
            policy_area = ".".join(parts[1:-1])
        else:
            policy_area = "other"

        file_data = coverage_data["files"][file_path]
        policy_groups[policy_area]["files"].append(file_path)
        policy_groups[policy_area]["total_coverage"] += file_data["coverage"]
        policy_groups[policy_area]["file_count"] += 1

        # Calculate line totals for the policy
        if "covered_lines" in file_data and "not_covered_lines" in file_data:
            policy_groups[policy_area]["total_lines"] += (
                file_data["covered_lines"] + file_data["not_covered_lines"]
            )
            policy_groups[policy_area]["covered_lines"] += file_data["covered_lines"]
            policy_groups[policy_area]["not_covered_lines"] += file_data[
                "not_covered_lines"
            ]

    # Calculate overall metrics
    overall_coverage = _round_percentage(coverage_data["coverage"])
    total_lines = coverage_data["covered_lines"] + coverage_data["not_covered_lines"]

    coverage_suites = []

    # Create single Coverage Summary suite with policies as test cases
    coverage_suite = ET.Element("testsuite")
    coverage_suite.set(
        "name",
        f"Coverage: {overall_coverage}% ({coverage_data['covered_lines']}/{total_lines} lines)",
    )
    coverage_suite.set("package", "coverage")
    coverage_suite.set("timestamp", datetime.now().isoformat())
    coverage_suite.set("hostname", socket.gethostname())

    # Don't include test/failure/error/skipped attributes to avoid showing them in output
    # Azure DevOps will still process the test cases inside

    # Add properties
    properties = ET.SubElement(coverage_suite, "properties")
    ET.SubElement(
        properties,
        "property",
        {"name": "coverage_threshold", "value": f"{coverage_threshold}%"},
    )
    ET.SubElement(
        properties,
        "property",
        {"name": "overall_coverage", "value": f"{overall_coverage}%"},
    )
    ET.SubElement(
        properties, "property", {"name": "total_lines", "value": str(total_lines)}
    )
    ET.SubElement(
        properties,
        "property",
        {"name": "covered_lines", "value": str(coverage_data["covered_lines"])},
    )
    ET.SubElement(
        properties,
        "property",
        {"name": "uncovered_lines", "value": str(coverage_data["not_covered_lines"])},
    )

    # Add test case for each policy
    for policy_area in sorted(policy_groups.keys()):
        group = policy_groups[policy_area]
        avg_coverage = _round_percentage(group["total_coverage"] / group["file_count"])

        # Calculate total lines for this policy
        policy_total_lines = group["total_lines"]
        policy_covered_lines = group["covered_lines"]

        # Check if any file in this policy has less than 100% coverage
        has_incomplete_coverage = any(
            coverage_data["files"][f]["coverage"] < 100 for f in group["files"]
        )

        # Create policy test case
        policy_testcase = ET.SubElement(coverage_suite, "testcase")
        # policy_testcase.set("classname", "coverage")

        # Always show line coverage in the name
        if policy_total_lines > 0:
            policy_testcase.set(
                "name",
                f"{policy_area}: {avg_coverage}% ({policy_covered_lines}/{policy_total_lines} lines)",
            )
        else:
            # If we don't have line data, just get it from the first file
            if group["files"]:
                first_file = group["files"][0]
                file_data = coverage_data["files"][first_file]
                if "covered_lines" in file_data and "not_covered_lines" in file_data:
                    file_total = (
                        file_data["covered_lines"] + file_data["not_covered_lines"]
                    )
                    file_covered = file_data["covered_lines"]
                    policy_testcase.set(
                        "name",
                        f"{policy_area}: {avg_coverage}% ({file_covered}/{file_total} lines)",
                    )
                else:
                    policy_testcase.set("name", f"{policy_area}: {avg_coverage}%")
            else:
                policy_testcase.set("name", f"{policy_area}: {avg_coverage}%")

        # Add failure if any file has less than 100% coverage
        if has_incomplete_coverage:
            failure = ET.SubElement(policy_testcase, "failure")
            failure.set(
                "message",
                f"One or more files in {policy_area} have coverage below 100%",
            )
            failure.set("type", "CoverageThreshold")

        # Add system-out with file details
        system_out = ET.SubElement(policy_testcase, "system-out")
        file_details = []

        for file_path in sorted(group["files"]):
            file_data = coverage_data["files"][file_path]
            file_coverage = _round_percentage(file_data["coverage"])
            filename = file_path.split("/")[-1]

            status = "✅" if file_coverage == 100 else "❌"

            # Add file coverage info
            if "covered_lines" in file_data and "not_covered_lines" in file_data:
                total_file_lines = (
                    file_data["covered_lines"] + file_data["not_covered_lines"]
                )
                file_details.append(
                    f"{status} {filename}: {file_coverage}% ({file_data['covered_lines']}/{total_file_lines} lines)"
                )

                # Add uncovered region details if file is not 100% covered
                if (
                    file_coverage < 100
                    and "not_covered" in file_data
                    and file_data["not_covered"]
                ):
                    file_details.append("   Uncovered regions:")
                    for region in file_data["not_covered"][
                        :3
                    ]:  # Show first 3 uncovered regions
                        start_line = region.get("start", {}).get("row", "?")
                        end_line = region.get("end", {}).get("row", "?")
                        file_details.append(f"   - Lines {start_line}-{end_line}")
                    if len(file_data["not_covered"]) > 3:
                        file_details.append(
                            f"   - ... and {len(file_data['not_covered']) - 3} more regions"
                        )
            else:
                file_details.append(f"{status} {filename}: {file_coverage}%")

        system_out.text = "\n".join(file_details)

    coverage_suites.append(coverage_suite)

    return coverage_suites


def create_combined_report(
    test_json_path, coverage_json_path, output_path, coverage_threshold
):
    """Create combined JUnit XML report from test and coverage JSON files"""

    # Load JSON data
    with open(test_json_path, "r") as f:
        test_data = json.load(f)

    with open(coverage_json_path, "r") as f:
        coverage_data = json.load(f)

    # Create root testsuites element
    testsuites = ET.Element("testsuites")
    testsuites.set("name", "OPA Policy Test and Coverage Report")
    testsuites.set("timestamp", datetime.now().isoformat())

    # Create test summary and suites
    test_suites = create_test_summary_and_suites(test_data)
    for suite in test_suites:
        testsuites.append(suite)

    # Create coverage summary and suites
    coverage_suites = create_coverage_summary_and_suites(
        coverage_data, coverage_threshold
    )
    for suite in coverage_suites:
        testsuites.append(suite)

    # Calculate combined totals from test data
    total_tests = len(test_data)
    total_failures = 0
    total_errors = 0
    total_skipped = 0

    # Count failures and errors from test data
    for test in test_data:
        if test.get("fail", False):
            total_failures += 1
        if test.get("error"):
            total_errors += 1
        if test.get("skip"):
            total_skipped += 1

    # Also check if coverage is below threshold
    overall_coverage = _round_percentage(coverage_data["coverage"])
    if overall_coverage < coverage_threshold:
        total_failures += 1

    testsuites.set("tests", str(total_tests))
    testsuites.set("failures", str(total_failures))
    testsuites.set("errors", str(total_errors))
    testsuites.set("skipped", str(total_skipped))

    # Write XML with proper formatting
    tree = ET.ElementTree(testsuites)
    ET.indent(tree, space="  ", level=0)
    tree.write(output_path, encoding="utf-8", xml_declaration=True)

    # Print summary
    print(f"✅ Combined JUnit report created: {output_path}")
    print("\n📊 Test Summary:")

    print(f"   - Total tests: {total_tests}")
    print(f"   - Passed: {total_tests - total_failures - total_errors}")
    print(f"   - Failed: {total_failures}")
    print(f"   - Errors: {total_errors}")

    print("\n📈 Coverage Summary:")
    print(f"   - Overall: {overall_coverage}%")
    print(f"   - Threshold: {coverage_threshold}%")
    print(
        f"   - Status: {'✅ PASS' if overall_coverage >= coverage_threshold else '❌ FAIL'}"
    )
    print(
        f"   - Lines: {coverage_data['covered_lines']}/{coverage_data['covered_lines'] + coverage_data['not_covered_lines']}"
    )

    policy_files = [f for f in coverage_data["files"] if not f.endswith("_test.rego")]
    print(f"   - Policy files: {len(policy_files)}")

    files_with_full_coverage = sum(
        1 for f in policy_files if coverage_data["files"][f]["coverage"] == 100
    )
    print(
        f"   - Files with 100% coverage: {files_with_full_coverage}/{len(policy_files)}"
    )

    print("\n📋 Combined Report:")
    print(f"   - Total items: {total_tests}")
    print(f"   - Total issues: {total_failures}")

    # Return exit code based on failures or coverage threshold
    return 1 if total_failures > 0 or overall_coverage < coverage_threshold else 0


def main():
    parser = argparse.ArgumentParser(
        description="Combine OPA test results and coverage data into a single JUnit XML report",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s --test-json test.json --coverage-json coverage.json --output-xml output.xml
    %(prog)s --test-json test.json --coverage-json coverage.json --output-xml output.xml --coverage-threshold 80
        """,
    )

    parser.add_argument(
        "--test-json",
        type=str,
        required=True,
        help="Path to OPA test results JSON file (from 'opa test --format=json')",
    )
    parser.add_argument(
        "--coverage-json",
        type=str,
        required=True,
        help="Path to OPA coverage JSON file (from 'opa test --coverage --format=json')",
    )
    parser.add_argument(
        "--output-xml",
        type=str,
        required=True,
        help="Path to output JUnit XML file",
    )
    parser.add_argument(
        "--coverage-threshold",
        type=float,
        default=95.0,
        help="Overall coverage threshold percentage (default: 95.0)",
    )
    parser.add_argument("-v", "--version", action="version", version="%(prog)s 1.0.0")

    args = parser.parse_args()

    # Validate coverage threshold
    if not 0 <= args.coverage_threshold <= 100:
        parser.error("Coverage threshold must be between 0 and 100")

    try:
        exit_code = create_combined_report(
            args.test_json, args.coverage_json, args.output_xml, args.coverage_threshold
        )
        sys.exit(exit_code)
    except FileNotFoundError as e:
        print(f"❌ Error: File not found - {e}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON format - {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
