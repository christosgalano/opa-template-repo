---
applyTo: "policy/**/*_test.rego"
---

# Rego Test File Standards

Apply these conventions to every `_test.rego` file.

## Package Declaration

Append `_test` to the package of the policy under test:

```rego
# Tests for: policy/terraform/azuredevops/project/project.rego
package terraform.azuredevops.project_test
```

## Imports

Always include `import rego.v1` and import the policy under test with a short alias:

```rego
package terraform.azuredevops.project_test

import rego.v1

import data.terraform.azuredevops.project
```

For utility packages under test, use an alias to keep references short:

```rego
import data.terraform.util.tags as t
```

Do not import `input` in test files — use `with input as ...` inline in each test.

## Fixture Objects

Define a `valid_<resource>` constant that represents the **minimal valid** configuration for the resource type. This acts as the baseline for all tests.

```rego
valid_project := {
    "type": "azuredevops_project",
    "change": {"after": {
        "name":            "Valid-Project-Name",
        "visibility":      "private",
        "version_control": "Git",
    }},
}
```

## Factory Functions

Use factory functions to derive variations from the valid fixture without rewriting the full object. Name them `<resource>_with_<property>(value)`.

```rego
# Generic: override any set of properties
project_with_properties(properties) := object.union(
    valid_project,
    {"change": {"after": object.union(valid_project.change.after, properties)}},
)

# Specific shorthands — one per tested property
project_with_name(name)                     := project_with_properties({"name": name})
project_with_visibility(visibility)         := project_with_properties({"visibility": visibility})
project_with_version_control(version_control) := project_with_properties({"version_control": version_control})
```

## Input Helpers

Wrap resource objects into the correct input shape with helper functions:

```rego
input_with_project(project) := {"resource_changes": [project]}
input_with_name(name)        := input_with_project(project_with_name(name))
```

## Test Structure and Ordering

Tests in each file follow this order:

1. **Baseline test** — valid fixture must produce zero violations.
2. **Per-property sections** — group tests by the property/rule being exercised, with a comment header.
3. **Message tests** — verify the exact denial message for each rule.
4. **Multi-violation test** — when a policy has multiple rules, test all violations at once.

## Baseline Test

Always present, always first:

```rego
test_valid_project_baseline if {
    count(project.deny) == 0 with input as input_with_project(valid_project)
}
```

## Per-Property Tests

Group with a comment. Cover at minimum: one passing case, one or more failing cases, and boundary/edge cases.

```rego
# Visibility validation
test_private_visibility if {
    count(project.deny) == 0 with input as input_with_visibility("private")
}

test_public_visibility if {
    count(project.deny) > 0 with input as input_with_visibility("public")
}

test_internal_visibility if {
    count(project.deny) > 0 with input as input_with_visibility("internal")
}
```

## Message Tests

Verify the exact denial message string for each rule. This ensures metadata descriptions stay accurate.

```rego
test_visibility_deny_message if {
    expected_msg := "Azure DevOps projects must have private visibility."
    expected_msg in project.deny with input as input_with_visibility("public")
}
```

## Multi-Violation Test

When a policy has multiple `deny` rules, write one test that triggers all of them simultaneously and checks both the count and the set of messages.

```rego
test_multiple_violations if {
    invalid_project := project_with_properties({
        "name":            "Invalid-Name-",
        "visibility":      "public",
        "version_control": "Tfvc",
    })

    expected_messages := {
        "Azure DevOps projects must have private visibility.",
        "Azure DevOps projects must use Git for version control.",
        "Azure DevOps project names must be between 4 and 64 characters long, start with a letter, contain only letters, numbers, or hyphens, and not end with a hyphen.",
    }

    msgs := project.deny with input as input_with_project(invalid_project)
    count(msgs) == count(expected_messages)
    msgs == expected_messages
}
```

## Scenario Tests

For scenario policies, build multi-resource input and test both combined entity rules and scenario-specific cross-entity rules.

```rego
valid_input := {"resource_changes": [
    {
        "type":   "azuredevops_project",
        "change": {"after": {
            "name":            "Valid-Project",
            "visibility":      "private",
            "version_control": "Git",
        }},
    },
    {
        "type":   "azuredevops_git_repository",
        "change": {"after": {"name": "Valid-Repo"}},
    },
]}

test_valid_complete_project if {
    count(scenario.deny) == 0 with input as valid_input
}

test_project_without_repository if {
    partial_input := {"resource_changes": [valid_input.resource_changes[0]]}
    count(scenario.deny) > 0 with input as partial_input
}
```

## Test Naming

- Prefix every test with `test_`.
- Use snake_case.
- Name describes the scenario being validated, not the assertion: `test_project_name_ends_with_hyphen` not `test_deny_is_not_empty`.

## Coverage

Target **100% coverage** for every policy file. At minimum the CI requires **90%**. Each branch and rule expression in the policy should be exercised by at least one test.

## Running Tests Locally

```sh
# All tests
opa test --verbose policy/

# Specific tool — automatically includes tool utilities
opa test --verbose policy/terraform/

# Specific subset — must explicitly include all imported util directories
opa test --verbose policy/terraform/util/ policy/terraform/azuredevops/

# With coverage
opa test --coverage --format=json policy/terraform/ > coverage.json
```
