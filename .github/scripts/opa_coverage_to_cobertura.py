#!/usr/bin/env python3
"""
Converts OPA coverage data to Cobertura XML format for Azure DevOps Code Coverage tab.

Usage:
    python opa_coverage_to_cobertura.py --coverage-json <coverage.json> --output-xml <coverage.xml> --policy-directory <source-dir> [--coverage-threshold <threshold>]

Example:
    python opa_coverage_to_cobertura.py --coverage-json coverage.json --output-xml coverage.xml --policy-directory ./policy --coverage-threshold 90.0
"""

import argparse
import json
import os
import sys
import xml.etree.ElementTree as ET
from datetime import datetime


def _round_percentage(value):
    """Round percentage to 4 decimal places for Cobertura format"""
    return round(value / 100, 4)


def calculate_policy_only_coverage(coverage_data):
    """Calculate coverage metrics for policy files only (excluding test files)"""
    policy_covered = 0
    policy_uncovered = 0

    for file_path, file_data in coverage_data["files"].items():
        # Skip test files
        if file_path.endswith("_test.rego"):
            continue

        covered = file_data.get("covered_lines", 0)
        uncovered = file_data.get("not_covered_lines", 0)

        policy_covered += covered
        policy_uncovered += uncovered

    total_policy_lines = policy_covered + policy_uncovered

    if total_policy_lines > 0:
        policy_coverage = (policy_covered / total_policy_lines) * 100
    else:
        policy_coverage = 0

    return {
        "covered_lines": policy_covered,
        "not_covered_lines": policy_uncovered,
        "total_lines": total_policy_lines,
        "coverage": policy_coverage,
    }


def create_cobertura_report(coverage_data, policy_directory):
    """Create Cobertura XML report from OPA coverage data"""

    # Calculate metrics for policy files only
    policy_metrics = calculate_policy_only_coverage(coverage_data)

    total_lines = policy_metrics["total_lines"]
    line_rate = _round_percentage(policy_metrics["coverage"])

    # Create root coverage element
    coverage = ET.Element("coverage")
    coverage.set("line-rate", str(line_rate))
    coverage.set("branch-rate", "0")  # OPA doesn't report branch coverage
    coverage.set("lines-covered", str(policy_metrics["covered_lines"]))
    coverage.set("lines-valid", str(total_lines))
    coverage.set("branches-covered", "0")
    coverage.set("branches-valid", "0")
    coverage.set("complexity", "0")
    coverage.set("version", "0.1")
    coverage.set("timestamp", str(int(datetime.now().timestamp())))

    # Add sources
    sources = ET.SubElement(coverage, "sources")
    source = ET.SubElement(sources, "source")
    source.text = os.path.abspath(policy_directory)

    # Add packages
    packages = ET.SubElement(coverage, "packages")

    # Group files by package (directory structure)
    package_map = {}

    for file_path, file_data in coverage_data["files"].items():
        # Skip test files
        if file_path.endswith("_test.rego"):
            continue

        # Extract package name from file path
        parts = file_path.split("/")
        if len(parts) > 1:
            package_name = ".".join(parts[:-1])  # Everything except filename
        else:
            package_name = "default"

        if package_name not in package_map:
            package_map[package_name] = {
                "files": [],
                "line_rate": 0,
                "covered_lines": 0,
                "total_lines": 0,
            }

        package_map[package_name]["files"].append((file_path, file_data))

        # Calculate lines for this file
        covered_lines = file_data.get("covered_lines", 0)
        not_covered_lines = file_data.get("not_covered_lines", 0)
        total_file_lines = covered_lines + not_covered_lines

        package_map[package_name]["covered_lines"] += covered_lines
        package_map[package_name]["total_lines"] += total_file_lines

    # Create package elements
    for package_name, package_data in sorted(package_map.items()):
        package = ET.SubElement(packages, "package")
        package.set("name", package_name)

        # Calculate package line rate
        if package_data["total_lines"] > 0:
            package_line_rate = (
                package_data["covered_lines"] / package_data["total_lines"]
            )
        else:
            package_line_rate = 0

        package.set("line-rate", str(round(package_line_rate, 4)))
        package.set("branch-rate", "0")
        package.set("complexity", "0")

        # Add classes (files)
        classes = ET.SubElement(package, "classes")

        for file_path, file_data in package_data["files"]:
            class_elem = ET.SubElement(classes, "class")

            # Extract filename without extension for class name
            filename = os.path.basename(file_path)
            classname = filename.replace(".rego", "")

            class_elem.set("name", classname)
            class_elem.set("filename", file_path)
            class_elem.set("line-rate", str(_round_percentage(file_data["coverage"])))
            class_elem.set("branch-rate", "0")
            class_elem.set("complexity", "0")

            # Add methods (we'll create one method per file for simplicity)
            methods = ET.SubElement(class_elem, "methods")
            method = ET.SubElement(methods, "method")
            method.set("name", "evaluate")
            method.set("signature", "")
            method.set("line-rate", str(_round_percentage(file_data["coverage"])))
            method.set("branch-rate", "0")

            # Add lines
            lines = ET.SubElement(class_elem, "lines")

            # Track all line numbers
            line_coverage = {}

            # Add covered lines
            for region in file_data.get("covered", []):
                start_line = region["start"]["row"]
                end_line = region["end"]["row"]
                for line_num in range(start_line, end_line + 1):
                    line_coverage[line_num] = True

            # Add not covered lines
            for region in file_data.get("not_covered", []):
                start_line = region["start"]["row"]
                end_line = region["end"]["row"]
                for line_num in range(start_line, end_line + 1):
                    line_coverage[line_num] = False

            # Create line elements
            for line_num in sorted(line_coverage.keys()):
                line = ET.SubElement(lines, "line")
                line.set("number", str(line_num))
                line.set("hits", "1" if line_coverage[line_num] else "0")
                line.set("branch", "false")

    return coverage, policy_metrics


def main():
    parser = argparse.ArgumentParser(
        description="Convert OPA coverage data to Cobertura XML format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s --coverage-json coverage.json --output-xml coverage.xml --policy-directory ./policy
    %(prog)s --coverage-json coverage.json --output-xml coverage.xml --policy-directory . --coverage-threshold 80
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
        help="Path to output Cobertura XML file",
    )
    parser.add_argument(
        "--policy-directory",
        type=str,
        default=".",
        help="Source directory containing policy files (default: current directory)",
    )
    parser.add_argument(
        "--coverage-threshold",
        type=float,
        default=None,
        help="Minimum coverage percentage required (optional, e.g., 80.0)",
    )
    parser.add_argument("-v", "--version", action="version", version="%(prog)s 1.0.0")

    args = parser.parse_args()

    # Validate coverage threshold if provided
    if args.coverage_threshold is not None and not 0 <= args.coverage_threshold <= 100:
        parser.error("Coverage threshold must be between 0 and 100")

    try:
        # Load coverage data
        with open(args.coverage_json, "r") as f:
            coverage_data = json.load(f)

        # Create Cobertura XML report
        coverage_elem, policy_metrics = create_cobertura_report(
            coverage_data, args.policy_directory
        )

        # Write XML with proper formatting
        tree = ET.ElementTree(coverage_elem)
        ET.indent(tree, space="  ", level=0)

        # Add DOCTYPE declaration for Cobertura
        with open(args.output_xml, "wb") as f:
            f.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
            f.write(
                b'<!DOCTYPE coverage SYSTEM "http://cobertura.sourceforge.net/xml/coverage-04.dtd">\n'
            )
            tree.write(f, encoding="utf-8", xml_declaration=False)

        # Print summary
        overall_coverage = round(policy_metrics["coverage"], 2)
        total_lines = policy_metrics["total_lines"]

        print(f"Coverage report created: {args.output_xml}")
        print("\nCoverage Summary:")
        print(f"- Overall: {overall_coverage}%")

        if args.coverage_threshold:
            print(f"- Threshold: {args.coverage_threshold}%")
            if overall_coverage >= args.coverage_threshold:
                print("- Status: PASS (above threshold)")
            else:
                print("- Status: FAIL (below threshold)")

        print(f"- Lines: {policy_metrics['covered_lines']}/{total_lines}")

        policy_files = [
            f for f in coverage_data["files"] if not f.endswith("_test.rego")
        ]
        print(f"- Policy files: {len(policy_files)}")

        # Show files with low coverage
        low_coverage_files = [
            (f, data["coverage"])
            for f, data in coverage_data["files"].items()
            if not f.endswith("_test.rego") and data["coverage"] < 100
        ]

        if low_coverage_files:
            print("\nFiles with incomplete coverage:")
            for file_path, cov in sorted(low_coverage_files, key=lambda x: x[1]):
                file_data = coverage_data["files"][file_path]
                covered = file_data.get("covered_lines", 0)
                uncovered = file_data.get("not_covered_lines", 0)
                total = covered + uncovered
                print(f"- {file_path}: {round(cov, 2)}% ({covered}/{total} lines)")

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
