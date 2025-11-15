# Policy Testing Guide

## Overview

This guide covers comprehensive policy testing approaches:

1. **Unit Testing** – Rego-based tests with mock data
2. **Integration Testing** – Real tool output validation
3. **CI/CD Integration** – Automated testing workflows

Both unit and integration tests ensure policies work correctly and provide confidence when making changes.

---

## Unit Testing

Unit tests are written in Rego and placed alongside policy files using the `*_test.rego` naming convention.

### Structure

```text
policy/<tool>/provider/<provider>/resources/<resource>/
  policy.rego
  policy_test.rego
```

### Example: Testing a Terraform Storage Account Policy

**File**: `policy/terraform/provider/azurerm/resources/storage_account/policy_test.rego`

```rego
package terraform.provider.azurerm.resources.storage_account_test

import rego.v1
import data.terraform.provider.azurerm.resources.storage_account as policy

# Test: Encryption enabled - should pass
test_encryption_enabled_passes if {
  result := policy.deny with input as mock_plan_with_encryption
  count(result) == 0
}

# Test: Encryption disabled - should deny
test_encryption_disabled_denies if {
  result := policy.deny with input as mock_plan_without_encryption
  count(result) == 1
  contains(result[_], "encryption enabled")
}

# Test: Public access enabled - should deny
test_public_access_denies if {
  result := policy.deny with input as mock_plan_with_public_access
  count(result) == 1
  contains(result[_], "public access")
}

# Test: Multiple violations - should deny multiple
test_multiple_violations if {
  result := policy.deny with input as mock_plan_multiple_issues
  count(result) == 2
}

# Mock data: Valid storage account
mock_plan_with_encryption := {
  "resource_changes": [
    {
      "address": "azurerm_storage_account.example",
      "type": "azurerm_storage_account",
      "change": {
        "after": {
          "name": "examplestorage",
          "encryption_enabled": true,
          "public_network_access_enabled": false
        }
      }
    }
  ]
}

# Mock data: Storage without encryption
mock_plan_without_encryption := {
  "resource_changes": [
    {
      "address": "azurerm_storage_account.bad",
      "type": "azurerm_storage_account",
      "change": {
        "after": {
          "name": "badstorage",
          "encryption_enabled": false,
          "public_network_access_enabled": false
        }
      }
    }
  ]
}

# Mock data: Storage with public access
mock_plan_with_public_access := {
  "resource_changes": [
    {
      "address": "azurerm_storage_account.public",
      "type": "azurerm_storage_account",
      "change": {
        "after": {
          "name": "publicstorage",
          "encryption_enabled": true,
          "public_network_access_enabled": true
        }
      }
    }
  ]
}

# Mock data: Multiple issues
mock_plan_multiple_issues := {
  "resource_changes": [
    {
      "address": "azurerm_storage_account.worst",
      "type": "azurerm_storage_account",
      "change": {
        "after": {
          "name": "worststorage",
          "encryption_enabled": false,
          "public_network_access_enabled": true
        }
      }
    }
  ]
}
```

### Running Unit Tests

**Always run from policy root** to include utility dependencies:

```bash
# Run all tests
opa test policy/ --verbose

# Run tests for specific tool
opa test policy/terraform/ --verbose

# Run tests for specific provider
opa test policy/terraform/provider/azurerm/ --verbose

# Run tests for specific resource
opa test policy/ --verbose --run "storage_account"

# Run with Conftest
conftest verify --policy policy/
```

**Why from root?** Policies import utilities from `policy/<tool>/util/`. Running tests on individual folders fails with "undefined function" errors.

### Ad-Hoc Policy Queries

For quick manual testing without formal test files:

```bash
# Test a single policy against input
opa eval \
  --data policy/ \
  --input testdata/terraform/azurerm/storage_account/tfplan.json \
  --format pretty \
  'data.terraform.provider.azurerm.resources.storage_account.deny'

# Check if any denies exist (exit code based)
opa eval \
  --data policy/ \
  --input tfplan.json \
  --fail-defined \
  'data.terraform.provider.azurerm.resources.storage_account.deny'

# Evaluate multiple packages
opa eval \
  --data policy/ \
  --input tfplan.json \
  --format pretty \
  'data.terraform.provider.azurerm'
```

**Use cases**: Quick validation during development, debugging policies, testing against production plans.

---

## Integration Testing

Integration tests use real tool output to validate policies against actual configurations.

### Structure

```text
testdata/
  <tool>/
    <provider>/
      <resource_or_scenario>/
        main.tf                    # Example configuration
        provider.tf                # Provider setup
        README.md                  # Test documentation
```

### Example: Terraform Integration Test

**File**: `testdata/terraform/azurerm/storage_account/main.tf`

```hcl
# Compliant storage account
resource "azurerm_storage_account" "compliant" {
  name                          = "compliantstorage"
  resource_group_name           = "rg-test"
  location                      = "eastus"
  account_tier                  = "Standard"
  account_replication_type      = "LRS"

  # Compliant settings
  encryption_enabled            = true
  public_network_access_enabled = false

  tags = {
    Environment = "Test"
    Owner       = "Platform Team"
    CostCenter  = "IT"
  }
}

# Non-compliant storage account (intentional)
resource "azurerm_storage_account" "non_compliant" {
  name                          = "noncompliantstorage"
  resource_group_name           = "rg-test"
  location                      = "eastus"
  account_tier                  = "Standard"
  account_replication_type      = "LRS"

  # Non-compliant settings (should trigger denies)
  encryption_enabled            = false  # VIOLATION
  public_network_access_enabled = true   # VIOLATION

  tags = {
    Environment = "Test"
  }
  # Missing required tags: Owner, CostCenter  # VIOLATION
}
```

### Running Integration Tests

#### For Terraform

```bash
# 1. Navigate to test directory
cd testdata/terraform/azurerm/storage_account

# 2. Initialize and generate plan
terraform init -backend=false
terraform plan -out=tfplan
terraform show -json tfplan > tfplan.json

# 3. Test with Conftest (recommended - better output)
cd ../../../..  # Back to repo root
conftest test \
  --policy policy/ \
  --namespace terraform.provider.azurerm.resources.storage_account \
  testdata/terraform/azurerm/storage_account/tfplan.json
```

**Note**: Set `ARM_SUBSCRIPTION_ID` and `ARM_TENANT_ID` environment variables if provider requires authentication.

#### For ARM Templates

```bash
# 1. Navigate to test directory
cd testdata/arm/storage_account

# 2. Template is already JSON, use directly
cd ../../..

# 3. Test with Conftest
conftest test \
  --policy policy/ \
  --namespace arm.resources.Microsoft.Storage.storageAccounts \
  testdata/arm/storage_account/template.json
```

#### For Kubernetes Manifests

```bash
conftest test \
  --policy policy/ \
  --namespace kubernetes.resources.pod \
  testdata/kubernetes/pod/manifest.yaml
```

---

## Testing Scenarios

### Provider-Level Scenarios

Test scenarios that combine multiple resources:

```bash
# Generate plan with multiple resources
cd testdata/terraform/azurerm/scenarios/secure_storage
terraform plan -out=tfplan
terraform show -json tfplan > tfplan.json

# Test scenario policy
cd ../../../../..
conftest test \
  --policy policy/ \
  --namespace terraform.provider.azurerm.scenarios.secure_storage \
  testdata/terraform/azurerm/scenarios/secure_storage/tfplan.json
```

### Cross-Provider Scenarios

Test scenarios spanning multiple providers:

```bash
# Test multi-cloud backup scenario
conftest test \
  --policy policy/ \
  --namespace terraform.scenarios.multicloud_backups \
  testdata/terraform/scenarios/multicloud_backups/tfplan.json
```

---

## CI/CD Integration

### GitHub Actions CI Pipeline

The CI pipeline automatically:

- ✅ Lints policies with Regal
- ✅ Runs all unit tests
- ✅ Generates coverage reports
- ✅ Publishes test results

**Configuration**: See `.github/workflows/ci.yaml`

```yaml
jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Lint
        uses: ./.github/actions/lint
        with:
          policy_directory: policy

      - name: Test
        uses: ./.github/actions/test
        with:
          policy_directory: policy
          threshold: 90
```

### Running Tests Locally

```bash
# Lint with Regal
regal lint policy

# Run unit tests
opa test policy/ --verbose

# Run tests with coverage
opa test policy/ --coverage --threshold 90

# Generate detailed reports
opa test --format json policy/ > test.json
opa test --coverage --threshold 90 --format json policy/ > coverage.json

# Convert to JUnit/Cobertura
python .github/scripts/opa_test_to_junit.py \
  --test-json test.json \
  --output-xml test-results.xml

python .github/scripts/opa_coverage_to_cobertura.py \
  --coverage-json coverage.json \
  --output-xml coverage.xml \
  --policy-directory policy
```

---

## Best Practices

### Unit Testing

✅ **Test both valid and invalid scenarios** for comprehensive coverage
✅ **Use descriptive test names** that explain expected behavior
✅ **Mock realistic data structures** matching actual tool output
✅ **Verify specific error messages** to ensure helpful feedback
✅ **Group related tests** with consistent naming patterns
✅ **Test edge cases** (empty values, null, missing fields, boundaries)
✅ **Test one thing per test** for clarity and debuggability

### Integration Testing

✅ **Keep test configs focused** on specific policy scenarios
✅ **Include both compliant and non-compliant resources**
✅ **Document expected violations** in comments
✅ **Regularly regenerate plans** to catch schema changes
✅ **Use realistic configurations** mirroring production patterns
✅ **Test with different tool versions** when possible
✅ **Clean up generated files** (don't commit plans/state)

### CI/CD Integration

✅ **Run unit tests in CI** for fast feedback
✅ **Run integration tests separately** (credentials, cleanup needed)
✅ **Enforce coverage thresholds** to maintain quality
✅ **Fail fast** on policy violations
✅ **Publish test results** for visibility
✅ **Cache tool installations** for faster builds

---

## Test Coverage

Measure and track test coverage:

```bash
# Generate coverage report
opa test policy/ --coverage --format json > coverage.json

# View coverage summary
jq '.coverage' coverage.json

# View per-file coverage
jq '.files' coverage.json

# Enforce coverage threshold
opa test policy/ --coverage --threshold 90
```

**Coverage goals**:

- 🎯 **90%+ overall** for production policies
- 🎯 **100%** for critical security/compliance policies
- 🎯 **80%+** for helper utilities

---

## Troubleshooting

### "Undefined function" errors

**Problem**: Running tests from subdirectories

**Solution**: Always run from policy root:

```bash
# ❌ Wrong
cd policy/terraform/provider/azurerm/resources/storage_account
opa test .

# ✅ Correct
cd <repo-root>
opa test policy/
```

### Tests pass locally but fail in CI

**Problem**: Local environment differs from CI

**Solution**: Run tests exactly as CI does:

```bash
regal lint policy
opa test policy/ --verbose
opa test policy/ --coverage --threshold 90
```

### Integration tests don't detect violations

**Problem**: Wrong namespace or policy path

**Solution**: Verify namespace matches package:

```bash
# Package in policy file
package terraform.provider.azurerm.resources.storage_account

# Must match namespace in conftest
conftest test --namespace terraform.provider.azurerm.resources.storage_account
```

---

## Resources

### Internal Documentation

- [Policy Development Guide](policy-development.md)
- [Policy Folder Structure](policy-folder-structure.md)

### External Resources

- [OPA Testing Documentation](https://www.openpolicyagent.org/docs/latest/policy-testing/)
- [Conftest Documentation](https://www.conftest.dev/)
- [Regal Testing Rules](https://docs.styra.com/regal/rules/testing)
- [Terraform JSON Format](https://developer.hashicorp.com/terraform/internals/json-format)
- [ARM Template Structure](https://learn.microsoft.com/en-us/azure/azure-resource-manager/templates/syntax)
- [Kubernetes API Reference](https://kubernetes.io/docs/reference/kubernetes-api/)

---

Comprehensive testing ensures policies remain reliable, maintainable, and effective as your infrastructure and governance requirements evolve.
