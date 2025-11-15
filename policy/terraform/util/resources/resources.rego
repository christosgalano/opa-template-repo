# METADATA
# scope: package
# description: A set of helper functions to work with resources in Terraform plans.
package terraform.util.resources

# METADATA
# title: Get resources by type.
# description: Returns a list of resources of a given type.
by_type(type, resources) := [resource |
	some resource in resources
	resource.type == type
]

# METADATA
# title: Get resources by action.
# description: Returns a list of resources after filtering by action.
by_action(action, resources) := [resource |
	some resource in resources
	some act in resource.change.actions
	act == action
]

# METADATA
# title: Get resources by type and action.
# description: Returns a list of resources of a given type and action.
by_type_and_action(type, action, resources) := [resource |
	some resource in resources
	resource.type == type
	some act in resource.change.actions
	act == action
]

# METADATA
# title: Get resources by name.
# description: Returns a list of resources of a given name.
by_name(resource_name, resources) := [resource |
	some resource in resources
	resource.name == resource_name
]

# METADATA
# title: Get resources by type and name.
# description: Returns a list of resources of a given type and name.
by_type_and_name(type, resource_name, resources) := [resource |
	some resource in resources
	resource.type == type
	resource.name == resource_name
]
