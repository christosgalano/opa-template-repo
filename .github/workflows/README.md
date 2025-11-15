# GitHub Actions Workflows

This directory contains CI/CD workflows for OPA policy validation and bundle management.

## Workflows

### CI - Rego Policy Validation (`ci.yaml`)

Automatically validates Rego policies on every push and pull request to main.

**Features:**

- Regal-based linting for Rego policies
- Comprehensive OPA testing with JSON reports
- JUnit XML test result publishing
- Cobertura XML coverage reporting (90% threshold)
- Test and coverage artifact uploads

**Triggers:**

- Push to any branch
- Pull requests to main

### Push Policy Bundle (`push-policy-bundle.yaml`)

Manually triggered workflow to push policy bundles to Azure Container Registry.

**Features:**

- Policy validation before push (with full test suite)
- Azure authentication with OIDC
- Bundle versioning
- Support for multiple policy directories

**Triggers:**

- Manual dispatch only

**Required Secrets:**
Configure these secrets in your repository settings for Azure authentication:

- `AZURE_CLIENT_ID` - Service Principal Client ID
- `AZURE_TENANT_ID` - Azure Tenant ID
- `AZURE_SUBSCRIPTION_ID` - Azure Subscription ID

**Required Permissions:**

- The workflow uses OIDC for Azure authentication
- Configure federated credentials in Azure AD for the GitHub Actions workflow

## Composite Actions

The workflows use reusable composite actions for modularity:

### `.github/actions/setup-regal`

Installs the Regal OPA linter with caching.

### `.github/actions/setup-conftest`

Installs Conftest for policy bundling with caching.

### `.github/actions/lint`

Lints Rego files using Regal and OPA.

**Inputs:**

- `policy_directory` - Directory to lint (default: `policy`)

### `.github/actions/test`

Runs comprehensive OPA tests with coverage and generates detailed reports.

**Inputs:**

- `policy_directory` - Directory to test (default: `policy`)
- `threshold` - Coverage threshold percentage (default: `90`)
- `no_fail_test` - Don't fail on test failures (default: `false`)
- `no_fail_coverage` - Don't fail on coverage threshold (default: `false`)
- `test_report_file` - Test report output file (default: `test.xml`)
- `coverage_report_file` - Coverage report output file (default: `coverage.xml`)

## Marketplace Actions Used

- `actions/checkout@v4` - Repository checkout
- `actions/cache@v4` - Caching for faster builds
- `actions/setup-python@v5` - Python setup for report conversion
- `actions/upload-artifact@v4` - Artifact uploads
- `open-policy-agent/setup-opa@v2` - OPA installation
- `azure/login@v2` - Azure authentication with OIDC
- `oras-project/setup-oras@v1` - ORAS CLI for OCI artifacts
- `EnricoMi/publish-unit-test-result-action@v2` - Test result publishing

## Report Conversion Scripts

Python scripts in `.github/scripts/` convert OPA JSON output to standard formats:

- `opa_test_to_junit.py` - Converts test results to JUnit XML
- `opa_coverage_to_cobertura.py` - Converts coverage to Cobertura XML

## Differences from Azure Pipelines

The GitHub Actions workflows achieve feature parity with Azure Pipelines but with these improvements:

1. **Modern Actions**: Uses official marketplace actions for tool installation
2. **Composite Actions**: Modular, reusable actions instead of templates
3. **OIDC Authentication**: Federated credentials for secure Azure access
4. **Better Caching**: Actions automatically cache installed tools
5. **Native Artifacts**: Uses GitHub Actions artifact system
6. **Enhanced Reporting**: Rich test and coverage visualization in PRs

## Local Testing

To test the policies locally before pushing:

```bash
# Lint with Regal
regal lint policy

# Run tests
opa test policy

# Run tests with coverage
opa test --coverage --threshold 90 policy

# Generate full reports
opa test --format json policy > test.json
opa test --coverage --threshold 90 --format json policy > coverage.json
python .github/scripts/opa_test_to_junit.py --test-json test.json --output-xml test.xml
python .github/scripts/opa_coverage_to_cobertura.py --coverage-json coverage.json --output-xml coverage.xml --policy-directory policy
```
