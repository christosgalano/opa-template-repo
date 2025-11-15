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

# METADATA
# title: Deny the creation of Azure DevOps projects with version control other than Git.
# description: Azure DevOps projects must use Git for version control.
deny contains msg if {
	projects := resources.by_type("azuredevops_project", tfplan.resource_changes)
	some project in projects
	project.change.after.version_control != "Git"
	annotation := rego.metadata.rule()
	msg := annotation.description
}

# METADATA
# title: Deny the creation of Azure DevOps projects with invalid names.
# description: Azure DevOps project names must be between 4 and 64 characters long, start with a letter, contain only letters, numbers, or hyphens, and not end with a hyphen.
deny contains msg if {
	projects := resources.by_type("azuredevops_project", tfplan.resource_changes)
	some project in projects
	not has_valid_name(project.change.after.name)
	annotation := rego.metadata.rule()
	msg := annotation.description
}

# METADATA
# title: Check if a string is a valid name.
# description: |
#  A valid name is a string that:
#  - starts with a letter
#  - followed by letters, numbers, or hyphens
#  - does not end with a hyphen
#  - is between 4 and 64 characters long
has_valid_name(name) if {
	regex.match(`^[a-zA-Z][a-zA-Z0-9-]*[a-zA-Z0-9]$`, name)
	count(name) >= 4
	count(name) <= 64
}
