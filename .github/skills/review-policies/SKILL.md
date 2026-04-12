---
name: review-policies
description: >
  Review a group of OPA policy files for correctness, consistency, and style.
  Lints with Regal, explains what each policy does, identifies coverage gaps,
  and suggests improvements. Use this skill when a user asks to review, audit,
  explain, or improve policies in a directory.
---

# Review Policies Skill

Use this skill to perform a thorough review of one or more OPA policy files.
The review covers correctness, structural conventions, test quality, and cohesion.

## Workflow

### Step 1 — Identify scope

Ask the user which policies to review if not already specified. Typical scopes:

- A single entity: `policy/terraform/azuredevops/project/`
- An entire provider: `policy/terraform/azuredevops/`
- All policies for a tool: `policy/terraform/`
- The full policy tree: `policy/`

### Step 2 — Read all policy and test files

For each `.rego` and `_test.rego` file in scope, read the full content.
Also read any utility packages they import.

### Step 3 — Run lint

```bash
regal lint <scope_path>
```

Report every finding with its rule name, file, line, and a brief explanation of why it matters.

### Step 4 — Run tests

```bash
# Remember to include utility paths when testing a subset
opa test --verbose policy/<tool>/util/ <scope_path>

# Coverage
opa test --coverage --format=json policy/<tool>/util/ <scope_path> > coverage.json
```

Report any test failures in full. Report overall coverage percentage and flag any file below 90%.

### Step 5 — Structural review

Check each policy file against these criteria:

**Conventions**

- [ ] Package name matches directory path exactly
- [ ] Package-level `# METADATA` present with `description:` and correct `entrypoint:` value
- [ ] All `deny` rules use `deny contains msg if` pattern
- [ ] All denial messages sourced from `rego.metadata.rule().description`
- [ ] Every `deny` rule has `# METADATA` with `title:` and `description:`
- [ ] Every exported helper has `# METADATA` with `title:` and `description:`
- [ ] `import input as tfplan` used (Terraform policies)
- [ ] Resource filtering via `resources.by_type(...)`, not direct `input.resource_changes` iteration
- [ ] `some <var> in <collection>` syntax (not legacy)
- [ ] No hardcoded denial message strings inline

**Design**

- [ ] Each `deny` rule covers exactly one constraint
- [ ] Reusable logic extracted to utility packages (no duplication across policies)
- [ ] Scenario policies re-export entity `deny` sets with `|` operator
- [ ] No `allow` rules or boolean `deny` patterns

### Step 6 — Test quality review

Check each `_test.rego` file:

- [ ] `import rego.v1` present
- [ ] Policy under test imported with short alias
- [ ] `valid_<entity>` baseline fixture defined
- [ ] Factory functions defined for each tested property
- [ ] Input helper functions defined
- [ ] Baseline test present and first
- [ ] Tests grouped by property with comment headers
- [ ] At least one passing and one failing test per `deny` rule
- [ ] Message test present for each `deny` rule
- [ ] Multi-violation test present (when policy has ≥ 2 rules)
- [ ] Test names are descriptive (`test_<scenario>`, not `test1`)

### Step 7 — Cohesion review

When reviewing multiple policies together:

- Identify **duplicate validation logic** that could be extracted to a utility.
- Check for **naming inconsistencies** in package names, function names, or test fixture patterns.
- Identify **missing coverage**: resource types present in sibling policies but without a dedicated policy.
- Note any **message inconsistencies** (e.g. same constraint expressed differently across policies).
- For scenarios: confirm they **re-export all** relevant entity `deny` sets.

### Step 8 — Produce a structured report

Output the review as:

```text
## Policy Review: <scope>

### Lint Results
<lint output or "All checks passed">

### Test Results
<pass/fail summary>
Coverage: X% (<files below 90% highlighted>)

### Structural Findings
<file>: <finding> — <recommendation>

### Test Quality Findings
<file>: <finding> — <recommendation>

### Cohesion Observations
<observation> — <recommendation>

### Summary
<2-4 sentence summary of overall quality and top priorities>
```

### Step 9 — Offer fixes

After presenting the report, ask the user if they want any of the identified issues fixed. If yes, apply fixes following `rego.instructions.md` and `rego-test.instructions.md`, then re-run lint and tests to confirm.
