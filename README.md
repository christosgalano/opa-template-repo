# opa-template-repo

## Purpose

This repository provides a central, extensible library for managing and sharing OPA (Open Policy Agent) policies for infrastructure-as-code and other JSON-based validation use cases. The structure is tool-agnostic and designed to support policies for any tool that produces JSON output (Terraform, ARM templates, etc.).

Policies in this library help ensure compliance, security, and best practices across your infrastructure. The design enables teams to:

- Enforce organizational standards and governance policies
- Prevent misconfigurations before deployment
- Promote reusable, scalable policy development across multiple tools and providers
- Validate infrastructure at scale with consistent patterns

## Getting Started

- **Policy structure:** See [`docs/policy-folder-structure.md`](docs/policy-folder-structure.md) for details on the tool-agnostic folder hierarchy (Tool → Provider → Resources/Scenarios) and how to organize policies.
- **Policy development:** For guidance on authoring policies and best practices, refer to [`docs/policy-development.md`](docs/policy-development.md).
- **Policy testing:** Learn how to test policies with both unit tests and integration tests in [`docs/policy-testing.md`](docs/policy-testing.md).
- **CI/CD pipelines:** See `.github/workflows/` for CI and policy bundle publishing workflows using GitHub Actions.
