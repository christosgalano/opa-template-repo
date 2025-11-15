# METADATA
# scope: package
# description: A set of helper functions to work with resource tags in Terraform plans.
package terraform.util.tags

# Internal helper function to extract tags from a resource
_tags(resource) := resource.change.after.tags

# METADATA
# title: Check if tag is present for a given resource.
# description: Return true if tag is present, otherwise false.
has_tag(resource, tag_name) if {
	_tags(resource)[tag_name]
}

# METADATA
# title: Check if a tag has a specific value for a given resource.
# description: Return true if tag has a specific value, otherwise false.
tag_equals(resource, tag_name, tag_value) if {
	_tags(resource)[tag_name] == tag_value
}

# METADATA
# title: Check if all required tags are present.
# description: Return true if all required tags are present, otherwise false.
has_all_tags(resource, required_tags) if {
	keys := object.keys(_tags(resource))
	missing := required_tags - keys
	missing == set()
}
