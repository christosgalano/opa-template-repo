# OPA Policy Repository — Copilot Instructions

This repository is a **template for managing and sharing Open Policy Agent (OPA) policies** for infrastructure-as-code (IaC) validation. Policies are written in Rego and evaluated against JSON output from tools such as Terraform or ARM templates.

## Purpose

Enforce organizational standards — governance, security, naming conventions, required tags — on IaC resources before deployment. The structure is tool-agnostic: any tool that produces JSON can be targeted.

## Directory Layout

```text
policy/
├── util/                          # Shared utilities (all tools)
├── <tool>/                        # e.g. terraform, arm
│   ├── util/                      # Tool-specific helper functions
│   │   └── <name>/
│   │       ├── <name>.rego
│   │       └── <name>_test.rego
│   ├── <org-level>/               # e.g. azuredevops, azurerm — varies by tool
│   │   ├── <entity>/              # One directory per resource type
│   │   │   ├── <entity>.rego
│   │   │   └── <entity>_test.rego
│   │   └── scenarios/
│   │       └── <scenario>/
│   │           ├── <scenario>.rego
│   │           └── <scenario>_test.rego
│   └── scenarios/                 # Tool-level cross-provider scenarios
└── ...
```

The hierarchy between tool and entity is **flexible and tool-specific**:

- **Terraform**: provider-based — `terraform/azuredevops/`, `terraform/azurerm/`
- **ARM**: resource-based — `arm/resources/`
- **Kubernetes**: API group-based — `kubernetes/apps/`, `kubernetes/networking/`

## Package Naming

Package names must exactly mirror the directory path under `policy/`:

| File path | Package |
|-----------|---------|
| `policy/terraform/azuredevops/project/project.rego` | `terraform.azuredevops.project` |
| `policy/terraform/util/tags/tags.rego` | `terraform.util.tags` |
| `policy/arm/resources/storage_account/storage_account.rego` | `arm.resources.storage_account` |
| `policy/terraform/azuredevops/scenarios/complete_project/complete_project.rego` | `terraform.azuredevops.scenarios.complete_project` |

Test packages append `_test`: e.g. `terraform.azuredevops.project_test`.

## Three Policy Types

### 1. Entity Policies

Target a single resource type. The core building block.

```rego
# METADATA
# scope: package
# description: A set of rules to enforce constraints on Azure DevOps projects.
# entrypoint: true
package terraform.azuredevops.project

import data.terraform.util.resources
import input as tfplan

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

### 2. Scenario Policies

Combine multiple entity policies for end-to-end validation. Re-export all entity `deny` rules using the union operator, then add cross-entity rules.

```rego
# METADATA
# scope: package
# description: Validates a complete Azure DevOps project with repository and settings.
# entrypoint: true
package terraform.azuredevops.scenarios.complete_project

import data.terraform.azuredevops.git_repository
import data.terraform.azuredevops.project

# Re-export all deny rules from included entity policies
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

### 3. Utility Packages

Pure helper functions — no `deny` rules, no `entrypoint`. Shared via `import data.<package>`.

```rego
# METADATA
# scope: package
# description: A set of helper functions to work with resources in Terraform plans.
package terraform.util.resources

by_type(type, resources) := [resource |
    some resource in resources
    resource.type == type
]
```

## Input Structures

### Terraform

Input is the Terraform plan JSON. Alias as `import input as tfplan`.

```json
{
  "resource_changes": [
    {
      "type": "azuredevops_project",
      "name": "my_project",
      "change": {
        "actions": ["create"],
        "after": { "name": "My-Project", "visibility": "private" }
      }
    }
  ]
}
```

Use `resources.by_type(type, tfplan.resource_changes)` — never iterate `input.resource_changes` directly.

### ARM

Input is the ARM deployment JSON. Resources live in `input.resources`.

```json
{
  "resources": [
    {
      "type": "Microsoft.Storage/storageAccounts",
      "name": "mystorageaccount",
      "location": "eastus",
      "properties": { "accountType": "Standard_LRS" }
    }
  ]
}
```

## Toolchain and Local Commands

| Tool | Purpose | Command |
|------|---------|---------|
| `opa test` | Run all tests | `opa test --verbose policy/` |
| `opa test` | Run tool subset | `opa test --verbose policy/terraform/util/ policy/terraform/azuredevops/` |
| `opa test --coverage` | Coverage report | `opa test --coverage --format=json policy/ > coverage.json` |
| `opa build` | Build a bundle | `opa build --bundle policy/ --output bundle.tar.gz` |
| `regal lint` | Lint policies | `regal lint policy/` |
| `conftest verify` | Verify tests pass | `conftest verify --policy policy` |
| `pre-commit` | All hooks | `pre-commit run --all-files` |

> **Important**: When testing a subset, always include all `util/` directories that those policies import. For example, to test `azuredevops` policies you must also pass `policy/terraform/util/`.

Minimum coverage threshold: **90%**.

## Key Conventions

- Every `.rego` policy file must have a `_test.rego` counterpart in the same directory.
- All `deny` rules source their message from `rego.metadata.rule().description` — never hardcode strings.
- Error messages are complete sentences ending with a period.
- Use `some <var> in <collection>` (not the older `some <var>; collection[var]`).
- Run `regal lint policy/` before committing and resolve all warnings.
- See `.github/instructions/` for detailed per-file-type coding standards.
- Use the skills in `.github/skills/` for guided task workflows.
