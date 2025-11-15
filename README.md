# Policy Library

## Purpose

This repository provides a central, extensible library for managing and sharing policies that govern Terraform Infrastructure as Code (IaC) deployments. The structure is designed to support policies for any Terraform provider, with an initial focus on Azure DevOps.

Policies in this library help ensure compliance, security, and good practices across Terraform-managed cloud environments. The design enables teams to:

- Enforce organizational standards for Terraform resources
- Prevent misconfigurations in Terraform plans
- Promote reusable, scalable policy development for Terraform

## Getting Started

- **Policy structure:** See [`docs/policy-folder-structure.md`](docs/policy-folder-structure.md) for details on how policies are organized and how to add new providers, resources, or utilities.
- **Policy development:** For guidance on authoring policies and good practices, refer to [`docs/policy-development.md`](docs/policy-development.md).
- **Policy testing:** Learn how to test policies with both unit tests and real Terraform plans in [`docs/policy-testing.md`](docs/policy-testing.md).
- **CI/CD pipelines:** Continuous integration and policy publishing workflows are documented in the relevant pipeline YAML files under `.azurepipelines/`.
