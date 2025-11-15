# Policy Development Guide

## Introduction

This guide describes how to develop, structure, and test policies using the [Rego language](https://www.openpolicyagent.org/docs/latest/policy-language/). Policies are evaluated against **JSON input** from any source.

Common use cases:

- Infrastructure-as-code plans (Terraform, ARM, CloudFormation)
- CI/CD pipeline configurations
- Kubernetes manifests
- API payloads
- Any structured JSON requiring validation

For more information, see the [OPA documentation](https://www.openpolicyagent.org/docs/latest/) and try the [OPA Playground](https://play.openpolicyagent.org/).

---

## Policy File Structure

A well-structured policy file contains:

### 1. File Metadata

Describe the policy's purpose at the top:

```rego
# METADATA
# scope: package
# description: Validates resource naming conventions and required properties
```

### 2. Package Declaration

Package names must mirror the folder structure:

**For single-resource policies**:

```rego
package <tool>.provider.<provider>.resources.<resource_type>
```

**For provider-level scenarios**:

```rego
package <tool>.provider.<provider>.scenarios.<scenario_name>
```

**For cross-provider scenarios**:

```rego
package <tool>.scenarios.<scenario_name>
```

**Examples**:

```rego
# Terraform Azure Storage Account
package terraform.provider.azurerm.resources.storage_account

# ARM Storage Resource
package arm.resources.Microsoft.Storage.storageAccounts

# Terraform Multi-Cloud Scenario
package terraform.scenarios.multicloud_backups
```

### 3. Imports

Import the input document and utility modules:

```rego
# Import input with descriptive alias
import input as tfplan  # or: armtemplate, k8smanifest, etc.

# Import tool-specific helpers
import data.terraform.util.plan_helpers as plan

# Import other resource policies (for scenarios)
import data.terraform.provider.azurerm.resources.storage_account as sa
import data.terraform.provider.azurerm.resources.network_security_group as nsg
```

### 4. Rule Definitions

Define policy rules with metadata:

```rego
# METADATA
# title: Storage accounts must have encryption enabled
# description: All storage accounts must enable encryption at rest for security compliance

deny contains msg if {
  storage := plan.storage_accounts(tfplan)[_]
  not storage.properties.encryption.enabled
  annotation := rego.metadata.rule()
  msg := sprintf("%s: %s (Resource: %s)", [
    annotation.title,
    annotation.description,
    storage.name
  ])
}
```

### 5. Helper Functions

Define reusable helpers in the policy file or utility modules:

```rego
# Check if resource has required tags
has_required_tags(resource) if {
  required := {"Environment", "Owner", "CostCenter"}
  tags := {tag | resource.tags[tag]}
  required == tags & required
}

# Get storage accounts from plan
storage_accounts(plan) = [sa |
  sa := plan.resource_changes[_]
  sa.type == "azurerm_storage_account"
  sa.change.after != null
]
```

---

## Complete Policy Examples

### Single-Resource Policy (Terraform Azure Storage Account)

**File**: `policy/terraform/provider/azurerm/resources/storage_account/policy.rego`

```rego
# METADATA
# scope: package
# description: Validation rules for Azure Storage Accounts

package terraform.provider.azurerm.resources.storage_account

import input as tfplan
import data.terraform.util.plan_helpers as plan

# METADATA
# title: Storage accounts must have encryption enabled
# description: All storage accounts must enable encryption at rest

deny contains msg if {
  sa := storage_accounts(tfplan)[_]
  not sa.change.after.encryption_enabled
  annotation := rego.metadata.rule()
  msg := sprintf("%s: %s", [annotation.title, sa.address])
}

# METADATA
# title: Storage accounts must not allow public access
# description: Public network access must be disabled for security

deny contains msg if {
  sa := storage_accounts(tfplan)[_]
  sa.change.after.public_network_access_enabled == true
  annotation := rego.metadata.rule()
  msg := sprintf("%s: %s", [annotation.title, sa.address])
}

# Helper: Get all storage accounts from plan
storage_accounts(tfplan) = plan.resources_of_type(tfplan, "azurerm_storage_account")

# Helper: Check if storage account is private
is_private(sa) if {
  sa.change.after.public_network_access_enabled == false
}
```

### Provider-Level Scenario (Secure Storage with NSG)

**File**: `policy/terraform/provider/azurerm/scenarios/secure_storage/policy.rego`

```rego
# METADATA
# scope: package
# description: Ensures storage accounts are secured with network security groups

package terraform.provider.azurerm.scenarios.secure_storage

import input as tfplan
import data.terraform.util.plan_helpers as plan
import data.terraform.provider.azurerm.resources.storage_account as sa
import data.terraform.provider.azurerm.resources.network_security_group as nsg

# METADATA
# title: Storage must be protected by NSG rules
# description: Non-private storage accounts require restrictive NSG rules

deny contains msg if {
  storage := sa.storage_accounts(tfplan)[_]
  not sa.is_private(storage)
  not has_protecting_nsg(storage, tfplan)
  annotation := rego.metadata.rule()
  msg := sprintf("%s: %s", [annotation.title, storage.address])
}

# Helper: Check if storage has protecting NSG
has_protecting_nsg(storage, tfplan) if {
  nsg_rules := nsg.rules_for_subnet(storage.change.after.subnet_id, tfplan)
  count(nsg_rules) > 0
  nsg.all_rules_restrictive(nsg_rules)
}
```

### Cross-Provider Scenario (Multi-Cloud Backups)

**File**: `policy/terraform/scenarios/multicloud_backups/policy.rego`

```rego
# METADATA
# scope: package
# description: Ensures critical data is backed up across multiple clouds

package terraform.scenarios.multicloud_backups

import input as tfplan
import data.terraform.util.plan_helpers as plan
import data.terraform.provider.azurerm.resources.storage_account as azure_sa
import data.terraform.provider.aws.resources.s3_bucket as aws_s3

# METADATA
# title: Critical Azure storage must have AWS backup
# description: Production storage accounts must have corresponding S3 backup buckets

deny contains msg if {
  azure_storage := critical_azure_storage(tfplan)[_]
  not has_aws_backup(azure_storage, tfplan)
  annotation := rego.metadata.rule()
  msg := sprintf("%s: %s", [annotation.title, azure_storage.address])
}

# Helper: Get critical Azure storage accounts
critical_azure_storage(tfplan) = [sa |
  sa := azure_sa.storage_accounts(tfplan)[_]
  sa.change.after.tags["Criticality"] == "High"
]

# Helper: Check if Azure storage has AWS backup
has_aws_backup(azure_storage, tfplan) if {
  backup_tag := sprintf("%s-backup", [azure_storage.change.after.name])
  backup := aws_s3.s3_buckets(tfplan)[_]
  backup.change.after.tags["BackupFor"] == backup_tag
}
```

---

## Understanding Imports in Rego

### Data Imports

The `data` keyword provides access to all loaded policies and utility functions:

```rego
# Access utility functions
import data.terraform.util.plan_helpers as plan

# Access other resource policies
import data.terraform.provider.azurerm.resources.storage_account as sa

# Access other provider policies
import data.terraform.provider.aws.resources.s3_bucket as s3
```

**How it works**:

- A file with `package terraform.util.plan_helpers` creates `data.terraform.util.plan_helpers`
- Import creates a local alias for easier access
- All public functions from that package become available

### Input Imports

The `input` variable represents external JSON data being evaluated:

```rego
# Descriptive alias improves readability
import input as tfplan      # Terraform plan
import input as armtemplate  # ARM template
import input as k8smanifest  # Kubernetes manifest
import input as pipeline     # CI/CD pipeline config
```

**Best practice**: Use descriptive aliases to make policy intent immediately clear.

---

## Tool-Specific Input Structures

### Terraform Plan JSON

Understand the structure before writing policies:

```bash
terraform plan -out=plan.tfplan
terraform show -json plan.tfplan > plan.json
```

**Key paths**:

```rego
tfplan.resource_changes[_]           # All resource changes
tfplan.resource_changes[_].type      # Resource type
tfplan.resource_changes[_].change.after  # New state
tfplan.resource_changes[_].change.before # Old state
tfplan.configuration                 # Module configuration
```

### ARM Template JSON

**Key paths**:

```rego
armtemplate.resources[_]             # All resources
armtemplate.resources[_].type        # Resource type
armtemplate.resources[_].properties  # Resource properties
armtemplate.parameters               # Template parameters
```

### Kubernetes Manifest

**Key paths**:

```rego
k8smanifest.kind                     # Resource kind
k8smanifest.metadata                 # Resource metadata
k8smanifest.spec                     # Resource specification
k8smanifest.metadata.labels          # Resource labels
```

---

## Rule Metadata Best Practices

Always include clear metadata for rules:

```rego
# METADATA
# title: Short, actionable title (< 80 chars)
# description: Detailed explanation of the requirement and why it matters

deny contains msg if {
  # Rule logic
  annotation := rego.metadata.rule()
  msg := sprintf("%s: %s", [annotation.title, resource.id])
}
```

**Good titles**:

- ✅ "Storage accounts must have encryption enabled"
- ✅ "Public access must be disabled"
- ✅ "Resources must have required tags"

**Poor titles**:

- ❌ "Check encryption"
- ❌ "Validation rule"
- ❌ "Error"

For more details, see [OPA Metadata Documentation](https://www.openpolicyagent.org/docs/policy-language#metadata).

---

## Best Practices

### 1. Prefer Deny Rules Over Allow Rules

**Why deny?**

- Explicit about what's wrong (natural for code review)
- Allows everything by default, blocks violations
- Simpler logic, fewer edge cases
- Aligns with fail-fast CI/CD pipelines

**Why not allow?**

- Requires enumerating all valid conditions
- Brittle and complex as scenarios grow
- Misses edge cases more easily

### 2. Keep Policies Focused

Each policy file should address one specific concern:

✅ **Good**: One file validates encryption, another validates networking
❌ **Bad**: One file validates everything about storage accounts

### 3. Create Reusable Components

Extract common logic to utility modules:

```rego
# In util/tags.rego
package terraform.util.tags

has_required_tags(resource, required) if {
  tags := {tag | resource.tags[tag]}
  required == tags & required
}

# In resource policy
import data.terraform.util.tags as tag_util

deny contains msg if {
  resource := resources[_]
  not tag_util.has_required_tags(resource, {"Owner", "CostCenter"})
  msg := sprintf("Missing required tags: %s", [resource.address])
}
```

### 4. Write Helper Functions for Selection

Don't repeat resource selection logic:

```rego
# In util/plan_helpers.rego
resources_of_type(plan, type) = [r |
  r := plan.resource_changes[_]
  r.type == type
  r.change.after != null
]

# In resource policies
storage_accounts(plan) = resources_of_type(plan, "azurerm_storage_account")
s3_buckets(plan) = resources_of_type(plan, "aws_s3_bucket")
```

### 5. Test Thoroughly

Write tests for:

- ✅ Valid configurations (should pass)
- ✅ Invalid configurations (should fail)
- ✅ Edge cases (empty values, null, missing fields)
- ✅ Boundary conditions

### 6. Document Complex Logic

Add comments for non-obvious logic:

```rego
# Check if storage is in a hub VNet (critical infrastructure)
# Hub VNets are identified by the "NetworkTier" tag
is_in_hub_vnet(storage, plan) if {
  subnet := find_subnet(storage.change.after.subnet_id, plan)
  vnet := find_vnet(subnet.vnet_id, plan)
  vnet.tags["NetworkTier"] == "Hub"
}
```

### 7. Plan for Scale

- Optimize for maintainability over cleverness
- Reuse patterns across similar resources
- Avoid deep nesting (extract to helpers)
- Use consistent naming conventions

### 8. Optimize for Performance

As policies grow, consider performance:

**❌ Avoid**: Repeated iteration in nested loops

```rego
# Inefficient - iterates resource_changes multiple times
deny contains msg if {
  storage := input.resource_changes[_]  # First iteration
  storage.type == "azurerm_storage_account"
  nsg := input.resource_changes[_]      # Nested iteration - expensive!
  nsg.type == "azurerm_network_security_group"
  # Complex logic...
}
```

**✅ Prefer**: Pre-filtered helper functions

```rego
# Efficient - iterate once, filter in helpers
deny contains msg if {
  storage := plan.storage_accounts(tfplan)[_]  # Pre-filtered
  nsg := plan.network_security_groups(tfplan)[_]  # Pre-filtered
  # Complex logic...
}

# Helper does filtering once
storage_accounts(plan) = [r |
  r := plan.resource_changes[_]
  r.type == "azurerm_storage_account"
]
```

**Performance tips**:

- Filter early with helper functions
- Avoid deep nesting of iterations
- Cache expensive lookups in local variables
- Use `some` keyword for existential checks when possible

### 9. Use Metadata Consistently

Always include `rego.metadata.rule()` in deny messages for CI readability:

```rego
# METADATA
# title: Storage encryption required
# description: All storage accounts must have encryption enabled

deny contains msg if {
  storage := resources[_]
  not storage.encryption_enabled
  annotation := rego.metadata.rule()
  # CI tools can parse this structured format
  msg := sprintf("%s: %s (Resource: %s)", [
    annotation.title,
    annotation.description,
    storage.address
  ])
}
```

This ensures:

- ✅ Consistent error message format
- ✅ CI/CD tools can extract metadata
- ✅ Reports are more readable
- ✅ Easy to filter/search violations

### 10. Review Regularly

Schedule periodic reviews:

- Remove obsolete rules
- Refactor complex logic
- Add policies for new resource types
- Update for tool schema changes

---

## Common Patterns

### Pattern: Resource Must Have Property

```rego
deny contains msg if {
  resource := resources[_]
  not resource.change.after.required_property
  msg := sprintf("Missing required property: %s", [resource.address])
}
```

### Pattern: Resource Must Not Have Property

```rego
deny contains msg if {
  resource := resources[_]
  resource.change.after.forbidden_property
  msg := sprintf("Forbidden property present: %s", [resource.address])
}
```

### Pattern: Property Must Match Pattern

```rego
deny contains msg if {
  resource := resources[_]
  not regex.match(`^[a-z][a-z0-9-]{3,24}$`, resource.change.after.name)
  msg := sprintf("Invalid name format: %s", [resource.address])
}
```

### Pattern: Resource Must Have Related Resource

```rego
deny contains msg if {
  storage := storage_accounts[_]
  not has_backup_policy(storage, plan)
  msg := sprintf("No backup policy: %s", [storage.address])
}

has_backup_policy(storage, plan) if {
  policy := backup_policies(plan)[_]
  policy.change.after.target_resource_id == storage.change.after.id
}
```

---

## Resources

- [OPA Documentation](https://www.openpolicyagent.org/docs/latest/)
- [Rego Language Reference](https://www.openpolicyagent.org/docs/latest/policy-reference/)
- [OPA Playground](https://play.openpolicyagent.org/)
- [Regal Style Guide](https://docs.styra.com/regal)
- [Policy Testing Guide](policy-testing.md)
- [Folder Structure Guide](policy-folder-structure.md)

---

By following this guide, you ensure policies remain robust, maintainable, and effective as your infrastructure evolves.
