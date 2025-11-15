#!/usr/bin/env python3
"""
Converts OPA coverage data to JUnit XML report.

Usage:
    python opa_coverage_to_junit.py --coverage-json <coverage.json> --output-xml <coverage-results.xml> [--coverage-threshold <threshold>]

Example:
    python opa_coverage_to_junit.py --coverage-json coverage.json --output-xml coverage-results.xml --coverage-threshold 90.0
"""

import argparse
import json
import socket
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime


def _round_percentage(value):
    """Round percentage to 2 decimal places"""
    return round(value, 2)


def create_coverage_report(coverage_data, coverage_threshold):
    """Create coverage report with single overall test case"""
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

    # Filter out test files
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
        if "covered_lines" in file_data:
            covered = file_data["covered_lines"]
            not_covered = file_data.get("not_covered_lines", 0)
            total = covered + not_covered

            policy_groups[policy_area]["total_lines"] += total
            policy_groups[policy_area]["covered_lines"] += covered
            policy_groups[policy_area]["not_covered_lines"] += not_covered

    # Calculate overall metrics
    overall_coverage = _round_percentage(coverage_data["coverage"])
    total_lines = coverage_data["covered_lines"] + coverage_data["not_covered_lines"]

    # Create root testsuites element
    testsuites = ET.Element("testsuites")
    testsuites.set("name", "OPA Coverage Report")
    testsuites.set("timestamp", datetime.now().isoformat())

    # Create Coverage Summary suite
    coverage_suite = ET.Element("testsuite")
    coverage_suite.set("name", "Coverage")
    coverage_suite.set("package", "coverage")
    coverage_suite.set("timestamp", datetime.now().isoformat())
    coverage_suite.set("hostname", socket.gethostname())
    coverage_suite.set("tests", "1")  # Only one test case

    # Check if overall coverage meets threshold
    overall_meets_threshold = overall_coverage >= coverage_threshold

    # Set failures based on whether overall coverage meets threshold
    coverage_suite.set("failures", "0" if overall_meets_threshold else "1")
    coverage_suite.set("errors", "0")
    coverage_suite.set("skipped", "0")
    coverage_suite.set("time", "0")

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

    # Add single test case for overall coverage
    overall_testcase = ET.SubElement(coverage_suite, "testcase")
    # overall_testcase.set("classname", "coverage")
    overall_testcase.set("name", f"Overall Coverage: {overall_coverage}%")
    overall_testcase.set("time", "0")

    # Add failure if overall coverage is below threshold
    if not overall_meets_threshold:
        failure = ET.SubElement(overall_testcase, "failure")
        failure.set(
            "message",
            f"Overall coverage {overall_coverage}% is below {coverage_threshold}% threshold",
        )
        failure.set("type", "CoverageThreshold")

    # Add system-out with all file details
    system_out = ET.SubElement(overall_testcase, "system-out")
    output_lines = []

    # Add header
    output_lines.append(
        f"Coverage Report: {overall_coverage}% ({coverage_data['covered_lines']}/{total_lines} lines)"
    )
    output_lines.append(f"Threshold: {coverage_threshold}%")
    output_lines.append("=" * 80)

    # Add details for each policy area
    for policy_area in sorted(policy_groups.keys()):
        group = policy_groups[policy_area]
        avg_coverage = _round_percentage(group["total_coverage"] / group["file_count"])

        # Policy header
        if group["total_lines"] > 0:
            output_lines.append(
                f"\n{policy_area}: {avg_coverage}% ({group['covered_lines']}/{group['total_lines']} lines)"
            )
        else:
            output_lines.append(f"\n{policy_area}: {avg_coverage}%")

        # File details
        for file_path in sorted(group["files"]):
            file_data = coverage_data["files"][file_path]
            file_coverage = _round_percentage(file_data["coverage"])
            filename = file_path.split("/")[-1]

            status = "✅" if file_coverage == 100 else "❌"

            # Add file coverage info
            if "covered_lines" in file_data:
                covered = file_data["covered_lines"]
                not_covered = file_data.get("not_covered_lines", 0)
                total_file_lines = covered + not_covered

                output_lines.append(
                    f"  {status} {filename}: {file_coverage}% ({covered}/{total_file_lines} lines)"
                )

                # Add uncovered region details if file is below threshold
                if (
                    file_coverage < coverage_threshold
                    and "not_covered" in file_data
                    and file_data["not_covered"]
                ):
                    output_lines.append("     Uncovered regions:")
                    for region in file_data["not_covered"]:
                        start_line = region.get("start", {}).get("row", "?")
                        end_line = region.get("end", {}).get("row", "?")
                        if start_line == end_line:
                            output_lines.append(f"     - Line {start_line}")
                        else:
                            output_lines.append(f"     - Lines {start_line}-{end_line}")
            else:
                output_lines.append(f"  {status} {filename}: {file_coverage}%")

    system_out.text = "\n".join(output_lines)

    testsuites.append(coverage_suite)

    # Set totals on testsuites
    testsuites.set("tests", "1")
    testsuites.set("failures", "0" if overall_meets_threshold else "1")
    testsuites.set("errors", "0")
    testsuites.set("skipped", "0")

    return testsuites


def main():
    parser = argparse.ArgumentParser(
        description="Convert OPA coverage data to JUnit XML report",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s --coverage-json coverage.json --output-xml coverage-results.xml
    %(prog)s --coverage-json coverage.json --output-xml coverage-results.xml --coverage-threshold 80
        """,
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
        # Load coverage data
        with open(args.coverage_json, "r") as f:
            coverage_data = json.load(f)

        # Create JUnit XML report
        testsuites = create_coverage_report(coverage_data, args.coverage_threshold)

        # Write XML with proper formatting
        tree = ET.ElementTree(testsuites)
        ET.indent(tree, space="  ", level=0)
        tree.write(args.output_xml, encoding="utf-8", xml_declaration=True)

        # Print summary
        overall_coverage = _round_percentage(coverage_data["coverage"])
        total_lines = (
            coverage_data["covered_lines"] + coverage_data["not_covered_lines"]
        )

        print(f"Coverage JUnit report created: {args.output_xml}")
        print("\nCoverage Summary:")
        print(f"- Overall: {overall_coverage}%")
        print(f"- Threshold: {args.coverage_threshold}%")
        print(
            f"- Status: {'✅ PASS' if overall_coverage >= args.coverage_threshold else '❌ FAIL'}"
        )
        print(f"- Lines: {coverage_data['covered_lines']}/{total_lines}")

        policy_files = [
            f for f in coverage_data["files"] if not f.endswith("_test.rego")
        ]
        print(f"- Policy files: {len(policy_files)}")

        # Return exit code based on coverage threshold
        exit_code = 0 if overall_coverage >= args.coverage_threshold else 1
        sys.exit(exit_code)

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
