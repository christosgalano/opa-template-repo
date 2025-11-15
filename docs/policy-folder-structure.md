# Policy Folder Structure

Policies are organized by **Tool**, **Provider/Domain**, and **Policy Type** to create a scalable, maintainable hierarchy that works across any infrastructure-as-code tool or JSON input source.

## Organizational Principles

The structure follows three layers:

1. **Tool** – What produces the JSON (terraform, arm, ansible, etc.)
2. **Provider/Domain** – Tool-specific grouping (e.g., Terraform provider, ARM namespace)
3. **Policy Type** – Single-resource vs multi-resource scenarios

## Standard Layout

```text
policy/
  <tool>/
    util/
      helpers.rego
      common.rego

    provider/
      <provider_name>/
        resources/
          <resource_type>/
            policy.rego
            policy_test.rego

        scenarios/
          <scenario_name>/
            policy.rego
            policy_test.rego

    scenarios/
      <cross_provider_scenario>/
        policy.rego
        policy_test.rego
```

## Complete Example

```text
policy/
  terraform/
    util/
      plan_helpers.rego
      tags.rego

    provider/
      azurerm/
        resources/
          storage_account/
            policy.rego
            policy_test.rego
          network_security_group/
            policy.rego
            policy_test.rego

        scenarios/
          secure_storage/
            policy.rego
            policy_test.rego

      aws/
        resources/
          s3_bucket/
            policy.rego
            policy_test.rego

        scenarios/
          public_s3_blocking/
            policy.rego
            policy_test.rego

    scenarios/
      multicloud_backups/
        policy.rego
        policy_test.rego

  arm/
    util/
      template_helpers.rego
    resources/
      storage/
        policy.rego
        policy_test.rego
    scenarios/

  ansible/
    util/
      playbook_helpers.rego
    resources/
    scenarios/
```

---

## Layer 1: Tool

Each top-level folder assumes a specific JSON schema for input:

- `policy/terraform/` → Terraform plan JSON
- `policy/arm/` → ARM deployment JSON
- `policy/ansible/` → Ansible-related JSON
- `policy/kubernetes/` → Kubernetes manifests

**Key principle**: All policies under a tool folder can safely assume that specific JSON schema, allowing tool-specific helpers and patterns.

### When to Create a New Tool Folder

- Different JSON input schema
- Different evaluation context
- Different toolchain (e.g., CloudFormation, Pulumi, Crossplane)

---

## Layer 2: Provider/Domain

Within each tool, organize by provider or domain:

### For Terraform

Group by Terraform provider names:

```text
policy/terraform/provider/azurerm/
policy/terraform/provider/aws/
policy/terraform/provider/google/
policy/terraform/provider/kubernetes/
```

### For ARM

Group by resource provider namespace:

```text
policy/arm/provider/Microsoft.Storage/
policy/arm/provider/Microsoft.Network/
policy/arm/provider/Microsoft.Compute/
```

### For Ansible

Group by role or module namespace:

```text
policy/ansible/roles/webserver/
policy/ansible/roles/database/
policy/ansible/modules/cloud/
```

**Flexibility**: Adapt this layer to your tool's natural organization. The goal is clear, predictable grouping.

---

## Layer 3: Resources vs Scenarios

Within each provider/domain, separate single-resource and multi-resource policies:

### `resources/` – Single-Resource Policies

One folder per resource type. These policies answer:

> "Is this one resource valid on its own?"

**Example**: Terraform Azure Storage Account

```text
policy/terraform/provider/azurerm/resources/storage_account/
  policy.rego
  policy_test.rego
```

**Package pattern**:

```rego
package terraform.provider.azurerm.resources.storage_account

import input as tfplan
import data.terraform.util.plan_helpers as plan

# METADATA
# title: Storage accounts must have encryption enabled
# description: Enforces encryption for all storage accounts

deny contains msg if {
  sa := plan.storage_accounts(tfplan)[_]
  not sa.properties.encryption.enabled
  msg := sprintf("Storage account %s must have encryption enabled", [sa.name])
}
```

### `scenarios/` – Provider-Level Scenarios

Provider-scoped scenarios combine multiple resources within the same provider:

**Example**: Terraform Azure Secure Storage Scenario

```text
policy/terraform/provider/azurerm/scenarios/secure_storage/
  policy.rego
  policy_test.rego
```

**Package pattern**:

```rego
package terraform.provider.azurerm.scenarios.secure_storage

import input as tfplan
import data.terraform.util.plan_helpers as plan
import data.terraform.provider.azurerm.resources.storage_account as sa
import data.terraform.provider.azurerm.resources.network_security_group as nsg

# METADATA
# title: Storage must be secured with NSG rules
# description: Storage accounts must have restrictive network security group rules

deny contains msg if {
  storage := plan.storage_accounts(tfplan)[_]
  not sa.is_private(storage)
  not nsg.has_restrictive_rules_for(storage, tfplan)
  msg := sprintf("Storage account %s is not securely exposed", [storage.name])
}
```

---

## Tool-Level Scenarios (Cross-Provider)

For scenarios that span multiple providers or require tool-wide context, use tool-level `scenarios/`:

```text
policy/terraform/scenarios/
  multicloud_backups/
    policy.rego
    policy_test.rego
  shared_tagging_standard/
    policy.rego
    policy_test.rego
```

**When to use**:

- Cross-provider scenarios (Azure + AWS)
- Environment-wide patterns
- Tool-level conventions (tagging, naming)

**Example**: Cross-Cloud Backup Scenario

```rego
package terraform.scenarios.multicloud_backups

import input as tfplan
import data.terraform.util.plan_helpers as plan
import data.terraform.provider.azurerm.resources.storage_account as sa
import data.terraform.provider.aws.resources.s3_bucket as s3

# METADATA
# title: Ensure multicloud backup strategy
# description: Critical data must be backed up across Azure and AWS

deny contains msg if {
  azure_sa := sa.critical_storage_accounts(tfplan)[_]
  not s3.has_backup_for(azure_sa, tfplan)
  msg := sprintf("No AWS backup for critical storage account %s", [azure_sa.name])
}
```

**Clear line**:

- Provider-level scenarios → `policy/<tool>/provider/<provider>/scenarios/`
- Cross-provider scenarios → `policy/<tool>/scenarios/`

---

## Utility Modules

Each tool has its own `util/` folder for shared helpers:

```text
policy/<tool>/util/
  helpers.rego
  common.rego
```

**Example**: Terraform Plan Helpers

```rego
package terraform.util.plan_helpers

import input as tfplan

resources_of_type(tfplan, type) = [r |
  r := tfplan.resource_changes[_]
  r.type == type
  r.change.after != null
]

storage_accounts(tfplan) = resources_of_type(tfplan, "azurerm_storage_account")
```

**Usage**: Both `resources/` and `scenarios/` import from `util/` instead of reimplementing selection logic.

---

## Decision Matrix

| Scenario | Location | Reason |
|----------|----------|--------|
| Single Azure storage account validation | `terraform/provider/azurerm/resources/storage_account/` | Single resource, one provider |
| Azure storage + NSG together | `terraform/provider/azurerm/scenarios/secure_storage/` | Multiple resources, one provider |
| Azure storage + AWS S3 backup | `terraform/scenarios/multicloud_backups/` | Multiple providers |
| Terraform plan helper functions | `terraform/util/` | Reusable across all Terraform policies |
| ARM template validation | `arm/resources/<resource_type>/` | Different tool, different schema |

---

## Adding New Policies

### New Single-Resource Policy

1. Create folder: `policy/<tool>/provider/<provider>/resources/<resource_type>/`
2. Add `policy.rego` with package `<tool>.provider.<provider>.resources.<resource_type>`
3. Add `policy_test.rego` with unit tests
4. Import helpers from `<tool>/util/` as needed

### New Provider-Level Scenario

1. Create folder: `policy/<tool>/provider/<provider>/scenarios/<scenario_name>/`
2. Add `policy.rego` with package `<tool>.provider.<provider>.scenarios.<scenario_name>`
3. Import resource policies: `import data.<tool>.provider.<provider>.resources.<type> as <alias>`
4. Add `policy_test.rego` with scenario tests

### New Cross-Provider Scenario

1. Create folder: `policy/<tool>/scenarios/<scenario_name>/`
2. Add `policy.rego` with package `<tool>.scenarios.<scenario_name>`
3. Import from multiple providers as needed
4. Add `policy_test.rego` with integration tests

### New Tool

1. Create folder: `policy/<new_tool>/`
2. Add `util/` with tool-specific helpers
3. Create provider/domain structure appropriate for the tool
4. Follow the same resources/scenarios pattern

---

## Benefits of This Structure

✅ **Clear Scope** – Package name immediately tells you what's being validated
✅ **No Conflicts** – Multiple tools/providers coexist cleanly
✅ **Reusability** – Scenarios import resource policies, avoid duplication
✅ **Scalability** – Add new tools, providers, resources without restructuring
✅ **Discoverability** – Predictable paths make policies easy to find
✅ **Testability** – Each policy has its own test file in the same folder
✅ **Tool-Agnostic** – Pattern works for any JSON-based validation

---

This structure grows with your infrastructure, maintains clarity at scale, and supports reliable policy bundling and testing automation.
