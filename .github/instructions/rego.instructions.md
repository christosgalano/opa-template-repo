---
applyTo: "policy/**/*.rego"
---

# Rego Policy File Standards

Apply these conventions to every `.rego` policy file (non-test).

## Package Declaration

The package name must exactly mirror the directory path under `policy/`, using dots as separators.

```rego
# File: policy/terraform/azuredevops/git_repository/git_repository.rego
package terraform.azuredevops.git_repository
```

## Package-Level Metadata

Every policy file must open with a `# METADATA` block scoped to the package.

- **Entity and scenario packages**: include `entrypoint: true`.
- **Utility packages**: do not include `entrypoint: true`.

```rego
# METADATA
# scope: package
# description: A set of rules to enforce constraints on Azure DevOps Git repositories.
# entrypoint: true
package terraform.azuredevops.git_repository
```

## Imports

Order: `import data.*` utilities first, then `import input as <alias>`.

```rego
import data.terraform.util.resources
import data.terraform.util.tags
import input as tfplan
```

- Alias `input` as `tfplan` for Terraform plans (or a descriptive name matching the tool).
- Do not import what you do not use. Do not use `import rego.v1` in policy files.

## Deny Rules

All violation rules follow the `deny contains msg if` pattern. One rule per constraint — do not combine unrelated checks in a single rule body.

```rego
# METADATA
# title: Deny the creation of Azure DevOps projects with visibility other than private.
# description: Azure DevOps projects must have private visibility.
deny contains msg if {
    projects := resources.by_type("azuredevops_project", tfplan.resource_changes)
    some project in projects
    project.change.after.visibility != "private"
    annotation := rego.metadata.rule()
    msg := annotation.description
}
```

Never hardcode the error message string inline. Always use `rego.metadata.rule().description`.

## Rule-Level Metadata

Every `deny` rule and every exported helper must have a `# METADATA` block with `title:` and `description:`. The `description:` on a `deny` rule becomes the user-facing error message — write it as a complete, actionable sentence ending with a period.

```rego
# METADATA
# title: Short imperative phrase ≤ 80 characters.
# description: Full sentence stating what is required and why it matters.
```

Use `|` syntax for multi-line descriptions:

```rego
# METADATA
# title: Check if a string is a valid name.
# description: |
#   A valid name is a string that:
#   - starts with a letter
#   - followed by letters, numbers, or hyphens
#   - does not end with a hyphen
#   - is between 4 and 64 characters long
```

## Helper Functions

- Private helpers (not exported): use a leading underscore prefix `_helper_name`.
- Exported helpers: plain names with metadata.
- Keep helper bodies short (≤ 10 lines); extract nested logic into further helpers.

```rego
# Private — extracts tags object from a resource
_tags(resource) := resource.change.after.tags

# METADATA
# title: Check if all required tags are present.
# description: Returns true if all required tags are present, otherwise false.
has_all_tags(resource, required_tags) if {
    keys    := object.keys(_tags(resource))
    missing := required_tags - keys
    missing == set()
}
```

## Resource Filtering

Always use `data.terraform.util.resources` helpers. Never iterate `input.resource_changes` directly in entity policy rules (scenarios may do so only in cross-entity rules that have no utility equivalent).

```rego
# Correct
resources.by_type("azuredevops_project", tfplan.resource_changes)
resources.by_type_and_action("azuredevops_project", "create", tfplan.resource_changes)
```

## Scenario Policies

Scenarios combine entity policies. Re-export all entity `deny` sets with the union operator, then add scenario-specific cross-entity rules beneath.

```rego
import data.terraform.azuredevops.git_repository
import data.terraform.azuredevops.project

deny := git_repository.deny | project.deny

# METADATA
# title: Ensure project has at least one repository.
# description: Azure DevOps projects must contain at least one Git repository.
deny contains msg if {
    projects := [r | some r in input.resource_changes; r.type == "azuredevops_project"]
    repos    := [r | some r in input.resource_changes; r.type == "azuredevops_git_repository"]
    count(projects) > 0
    count(repos) == 0
    annotation := rego.metadata.rule()
    msg := annotation.description
}
```

## Iteration

Use `some <var> in <collection>`, not the legacy `some <var>; collection[var]`.

## Regex

Use backtick strings for regex patterns to avoid escaping:

```rego
regex.match(`^[a-zA-Z][a-zA-Z0-9-]*[a-zA-Z0-9]$`, name)
```

## General Style

- No trailing whitespace; files must end with a newline.
- Maximum rule body length: ~10 lines. Extract helpers if longer.
- Run `regal lint policy/` before committing and resolve all warnings.
