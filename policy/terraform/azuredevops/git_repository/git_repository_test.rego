package terraform.azuredevops.git_repository_test

import data.terraform.azuredevops.git_repository as repo

# Object representing a valid Azure DevOps Git repository
valid_repository := {
	"type": "azuredevops_git_repository",
	"change": {"after": {"name": "Valid-Repository-Name"}},
}

# Factory method to create repository with custom name
repository_with_name(name) := object.union(valid_repository, {"change": {"after": {"name": name}}})

# Helper to create input with repository
input_with_repository(repository) := {"resource_changes": [repository]}

# Helper to create input with repository name
input_with_name(name) := input_with_repository(repository_with_name(name))

# Baseline: Valid repository should pass all rules
test_valid_repository_baseline if {
	count(repo.deny) == 0 with input as input_with_repository(valid_repository)
}

# Name validation tests
test_valid_repository_name if {
	count(repo.deny) == 0 with input as input_with_name("Valid-Repository-Name")
}

test_repository_name_starts_with_number if {
	count(repo.deny) > 0 with input as input_with_name("1invalid-repo")
}

test_repository_name_ends_with_hyphen if {
	count(repo.deny) > 0 with input as input_with_name("invalid-repo-")
}

test_repository_name_contains_invalid_characters if {
	count(repo.deny) > 0 with input as input_with_name("invalid repo")
}

test_repository_name_contains_underscore if {
	count(repo.deny) > 0 with input as input_with_name("invalid_repo")
}

test_short_repository_name if {
	count(repo.deny) > 0 with input as input_with_name("abc")
}

test_long_repository_name if {
	very_long_name := "a-very-long-repository-name-that-exceeds-the-maximum-allowed-length"
	count(repo.deny) > 0 with input as input_with_name(very_long_name)
}

test_single_character_repository_name if {
	count(repo.deny) > 0 with input as input_with_name("a")
}

test_empty_repository_name if {
	count(repo.deny) > 0 with input as input_with_name("")
}

test_repository_name_only_letters if {
	count(repo.deny) == 0 with input as input_with_name("ValidRepo")
}

test_repository_name_with_numbers if {
	count(repo.deny) == 0 with input as input_with_name("Valid-Repo-123")
}

test_repository_name_with_hyphens if {
	count(repo.deny) == 0 with input as input_with_name("Valid-Repository-Name")
}

# Message validation tests
test_name_deny_message if {
	expected_msg := "Azure DevOps repository names must be between 4 and 64 characters long, start with a letter, contain only letters, numbers, or hyphens, and not end with a hyphen."
	expected_msg in repo.deny with input as input_with_name("invalid () repository")
}
