---
name: create-policy
description: >
  Scaffold a new OPA entity policy or scenario policy together with its test
  file. Use this skill when a user asks to add a new policy, create a new rule,
  or start a new validation for a resource type.
---

# Create Policy Skill

Use this skill to scaffold a complete, standards-compliant policy pair:
a policy file (`<entity>.rego`) and its test file (`<entity>_test.rego`).

## Workflow

### Step 1 — Gather requirements

Ask the user for the following if not already provided:

1. **Policy type**: entity (single resource) or scenario (combines multiple resources)?
2. **Tool**: e.g. `terraform`, `arm`, `kubernetes`
3. **Org-level / hierarchy**: e.g. `azuredevops`, `azurerm`, `resources` — depends on the tool's natural grouping
4. **Entity name**: snake_case name matching the Terraform resource type or equivalent (e.g. `storage_account`, `virtual_network`)
5. **Terraform resource type** (if Terraform): e.g. `azurerm_storage_account`
6. **Constraints to enforce**: list each rule the policy must implement with its description message
7. **For scenarios**: which existing entity packages to import and re-export

### Step 2 — Determine paths

Compute the paths before writing any files:

```text
Directory : policy/<tool>/<org-level>/<entity>/
Policy    : policy/<tool>/<org-level>/<entity>/<entity>.rego
Test      : policy/<tool>/<org-level>/<entity>/<entity>_test.rego
Package   : <tool>.<org-level>.<entity>
Test pkg  : <tool>.<org-level>.<entity>_test
```

For scenarios:

```text
Directory : policy/<tool>/<org-level>/scenarios/<scenario>/
Package   : <tool>.<org-level>.scenarios.<scenario>
```

### Step 3 — Write the policy file

Follow `rego.instructions.md` exactly. Template:

```rego
# METADATA
# scope: package
# description: A set of rules to enforce constraints on <resource_type>.
# entrypoint: true
package <tool>.<org-level>.<entity>

import data.terraform.util.resources
import input as tfplan

# METADATA
# title: <Short imperative title for rule 1>.
# description: <Full sentence — this becomes the error message.>
deny contains msg if {
    <resources> := resources.by_type("<terraform_resource_type>", tfplan.resource_changes)
    some <resource> in <resources>
    <resource>.change.after.<property> <condition>
    annotation := rego.metadata.rule()
    msg := annotation.description
}

# Add one deny rule per constraint — do not combine unrelated checks
```

For scenarios, re-export before adding cross-entity rules:

```rego
import data.<package_a>
import data.<package_b>

deny := <package_a>.deny | <package_b>.deny

# Then add scenario-specific deny rules below
```

### Step 4 — Write the test file

Follow `rego-test.instructions.md` exactly. Template:

```rego
package <tool>.<org-level>.<entity>_test

import rego.v1

import data.<tool>.<org-level>.<entity>

# Minimal valid fixture
valid_<entity> := {
    "type": "<terraform_resource_type>",
    "change": {"after": {
        # ... all required fields with valid values
    }},
}

# Factory functions — one per tested property
<entity>_with_properties(properties) := object.union(
    valid_<entity>,
    {"change": {"after": object.union(valid_<entity>.change.after, properties)}},
)

<entity>_with_<property>(value) := <entity>_with_properties({"<property>": value})

# Input helpers
input_with_<entity>(<entity>) := {"resource_changes": [<entity>]}
input_with_<property>(value)  := input_with_<entity>(<entity>_with_<property>(value))

# --- Baseline ---
test_valid_<entity>_baseline if {
    count(<entity>.deny) == 0 with input as input_with_<entity>(valid_<entity>)
}

# --- <Property> validation ---
test_valid_<property> if {
    count(<entity>.deny) == 0 with input as input_with_<property>(<valid_value>)
}

test_invalid_<property> if {
    count(<entity>.deny) > 0 with input as input_with_<property>(<invalid_value>)
}

# Message validation
test_<property>_deny_message if {
    expected_msg := "<exact description from metadata>"
    expected_msg in <entity>.deny with input as input_with_<property>(<invalid_value>)
}
```

### Step 5 — Validate

After writing both files, run:

```bash
# Include util dirs so imports resolve
opa test --verbose policy/<tool>/util/ policy/<tool>/<org-level>/

# Lint
regal lint policy/<tool>/<org-level>/<entity>/
```

Fix any test failures or lint warnings before handing back.

## Quality Checklist

Before completing, verify:

- [ ] Package name exactly matches the directory path under `policy/`
- [ ] Package-level `# METADATA` is present with `description:` and `entrypoint: true`
- [ ] Every `deny` rule has rule-level `# METADATA` with `title:` and `description:`
- [ ] Every `deny` rule sources its message via `rego.metadata.rule().description`
- [ ] Error messages are full sentences ending with a period
- [ ] Test file has `import rego.v1`
- [ ] A `valid_<entity>` baseline fixture is defined
- [ ] Factory functions cover every tested property
- [ ] At least one passing and one failing test per `deny` rule
- [ ] At least one message test per `deny` rule
- [ ] A multi-violation test (if more than one `deny` rule)
- [ ] `opa test` passes with zero failures
- [ ] `regal lint` returns no warnings
