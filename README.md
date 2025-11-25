# opa-template-repo

This repository provides a central, extensible library for managing and sharing OPA (Open Policy Agent) policies for infrastructure-as-code and other JSON-based validation use cases. The structure is tool-agnostic and designed to support policies for any tool that produces JSON output (Terraform, ARM templates, etc.).

Policies in this library help ensure compliance, security, and best practices across your infrastructure. The design enables teams to:

- Enforce organizational standards and governance policies
- Prevent misconfigurations before deployment
- Promote reusable, scalable policy development across multiple tools and providers
- Validate infrastructure at scale with consistent patterns

## Getting Started

- [OPA Policy-Driven Governance for Infrastructure as Code](https://youtu.be/kU1KhvxRynQ?si=XFSozYT1-Kj0BHVA): Video presentation covering OPA concepts and policy-driven governance for IaC

## Documentation

Comprehensive documentation is available in the [Wiki](https://github.com/christosgalano/opa-template-repo/wiki):

### [Structure](https://github.com/christosgalano/opa-template-repo/wiki/Structure)

Learn how the repository is organized:

- Directory layout and flexible hierarchy
- File and package naming conventions
- How to add new tools, organizational levels, entities, utilities, and scenarios

### [Workflows](https://github.com/christosgalano/opa-template-repo/wiki/Workflows)

Understand CI/CD and policy bundle management:

- CI workflow for validation (lint, test, coverage)
- Policy bundle workflow for publishing to Azure Storage
- Bundle concept and storage
- Local testing commands
- Best practices

### [Creating Policies](https://github.com/christosgalano/opa-template-repo/wiki/Creating-Policies)

Step-by-step guide for creating policies:

- Entity policy example (Azure DevOps Git repository)
- Scenario policy example (complete project validation)
- Tool-specific input structures (Terraform, ARM)
- Testing patterns and best practices
- Running tests and coverage

## Quick Start

1. **Understand the structure**: Read the [Structure](https://github.com/christosgalano/opa-template-repo/wiki/Structure) guide to learn how policies are organized
2. **Learn workflows**: Review the [Workflows](https://github.com/christosgalano/opa-template-repo/wiki/Workflows) guide to understand CI/CD and bundles
3. **Create policies**: Follow the [Creating Policies](https://github.com/christosgalano/opa-template-repo/wiki/Creating-Policies) guide to add new validations

## Resources

### OPA Official Documentation

- [OPA Documentation](https://www.openpolicyagent.org/docs/latest/): Official OPA documentation
- [Policy Language (Rego)](https://www.openpolicyagent.org/docs/latest/policy-language/): Rego language reference
- [Policy Testing](https://www.openpolicyagent.org/docs/latest/policy-testing/): Writing and running tests
- [Policy Reference](https://www.openpolicyagent.org/docs/latest/policy-reference/): Built-in functions and operators
- [Management: Bundles](https://www.openpolicyagent.org/docs/latest/management-bundles/): Bundle distribution and management

### Learning Materials

- [OPA Playground](https://play.openpolicyagent.org/): Interactive Rego environment

### Community

- [OPA GitHub Repository](https://github.com/open-policy-agent/opa)
- [OPA Slack Community](https://openpolicyagent.slack.com/)
