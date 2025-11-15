package terraform.azuredevops.project_test

import rego.v1

import data.terraform.azuredevops.project

# Object representing a valid Azure DevOps project
valid_project := {
	"type": "azuredevops_project",
	"change": {"after": {
		"name": "Valid-Project-Name",
		"visibility": "private",
		"version_control": "Git",
	}},
}

# Factory method to create project with custom properties
project_with_properties(properties) := object.union(valid_project, {"change": {"after": object.union(valid_project.change.after, properties)}})

# Factory method to create project with custom name
project_with_name(name) := project_with_properties({"name": name})

# Factory method to create project with custom visibility
project_with_visibility(visibility) := project_with_properties({"visibility": visibility})

# Factory method to create project with custom version control
project_with_version_control(version_control) := project_with_properties({"version_control": version_control})

# Helper to create input with project
input_with_project(project) := {"resource_changes": [project]}

# Helper to create input with project name
input_with_name(name) := input_with_project(project_with_name(name))

# Helper to create input with project visibility
input_with_visibility(visibility) := input_with_project(project_with_visibility(visibility))

# Helper to create input with project version control
input_with_version_control(version_control) := input_with_project(project_with_version_control(version_control))

# Baseline: Valid project should pass all rules
test_valid_project_baseline if {
	count(project.deny) == 0 with input as input_with_project(valid_project)
}

# Visibility validation tests
test_private_visibility if {
	count(project.deny) == 0 with input as input_with_visibility("private")
}

test_public_visibility if {
	count(project.deny) > 0 with input as input_with_visibility("public")
}

test_internal_visibility if {
	count(project.deny) > 0 with input as input_with_visibility("internal")
}

test_visibility_deny_message if {
	expected_msg := "Azure DevOps projects must have private visibility."
	expected_msg in project.deny with input as input_with_visibility("public")
}

# Version control validation tests
test_git_version_control if {
	count(project.deny) == 0 with input as input_with_version_control("Git")
}

test_tfvc_version_control if {
	count(project.deny) > 0 with input as input_with_version_control("Tfvc")
}

test_svn_version_control if {
	count(project.deny) > 0 with input as input_with_version_control("Svn")
}

test_version_control_deny_message if {
	expected_msg := "Azure DevOps projects must use Git for version control."
	expected_msg in project.deny with input as input_with_version_control("Tfvc")
}

# Name validation tests
test_valid_project_name if {
	count(project.deny) == 0 with input as input_with_name("Valid-Project-Name")
}

test_project_name_starts_with_number if {
	count(project.deny) > 0 with input as input_with_name("1invalid-project")
}

test_project_name_ends_with_hyphen if {
	count(project.deny) > 0 with input as input_with_name("invalid-project-")
}

test_project_name_contains_invalid_characters if {
	count(project.deny) > 0 with input as input_with_name("invalid_project")
}

test_project_name_contains_spaces if {
	count(project.deny) > 0 with input as input_with_name("invalid project")
}

test_short_project_name if {
	count(project.deny) > 0 with input as input_with_name("abc")
}

test_long_project_name if {
	very_long_name := "a-very-long-project-name-that-exceeds-the-maximum-allowed-length-limit"
	count(project.deny) > 0 with input as input_with_name(very_long_name)
}

test_single_character_project_name if {
	count(project.deny) > 0 with input as input_with_name("a")
}

test_empty_project_name if {
	count(project.deny) > 0 with input as input_with_name("")
}

test_project_name_only_letters if {
	count(project.deny) == 0 with input as input_with_name("ValidProject")
}

test_project_name_with_numbers if {
	count(project.deny) == 0 with input as input_with_name("Valid-Project-123")
}

test_project_name_with_hyphens if {
	count(project.deny) == 0 with input as input_with_name("Valid-Project-Name")
}

test_name_deny_message if {
	expected_msg := "Azure DevOps project names must be between 4 and 64 characters long, start with a letter, contain only letters, numbers, or hyphens, and not end with a hyphen."
	expected_msg in project.deny with input as input_with_name("invalid () project")
}

# Comprehensive test with multiple violations
test_multiple_violations if {
	invalid_project := project_with_properties({
		"name": "Invalid-Name-",
		"visibility": "public",
		"version_control": "Tfvc",
	})

	test_input := input_with_project(invalid_project)

	expected_messages := {
		"Azure DevOps projects must have private visibility.",
		"Azure DevOps projects must use Git for version control.",
		"Azure DevOps project names must be between 4 and 64 characters long, start with a letter, contain only letters, numbers, or hyphens, and not end with a hyphen.",
	}

	msgs := project.deny with input as test_input
	count(msgs) == count(expected_messages)
	msgs == expected_messages
}
