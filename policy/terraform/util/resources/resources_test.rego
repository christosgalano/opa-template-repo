package terraform.util.resources_test

import data.terraform.util.resources as r

# Test that by_type returns the correct resources
test_by_type if {
	resources := [{"type": "type1", "name": "name1"}, {"type": "type2", "name": "name2"}]
	r.by_type("type1", resources) == [{"type": "type1", "name": "name1"}]
}

# Test that by_action returns the correct resources
test_by_action if {
	resources := [{"type": "type1", "name": "name1", "change": {"actions": ["create"]}}, {"type": "type2", "name": "name2", "change": {"actions": ["delete"]}}]
	r.by_action("create", resources) == [{"type": "type1", "name": "name1", "change": {"actions": ["create"]}}]
}

# Test that by_type_and_action returns the correct resources
test_by_type_and_action if {
	resources := [{"type": "type1", "name": "name1", "change": {"actions": ["create"]}}, {"type": "type2", "name": "name2", "change": {"actions": ["delete"]}}]
	r.by_type_and_action("type1", "create", resources) == [{"type": "type1", "name": "name1", "change": {"actions": ["create"]}}]
}

# Test that by_name returns the correct resources
test_by_name if {
	resources := [{"type": "type1", "name": "name1"}, {"type": "type2", "name": "name2"}]
	r.by_name("name1", resources) == [{"type": "type1", "name": "name1"}]
}

# Test that by_type_and_name returns the correct resources
test_by_type_and_name if {
	resources := [{"type": "type1", "name": "name1"}, {"type": "type2", "name": "name2"}]
	r.by_type_and_name("type1", "name1", resources) == [{"type": "type1", "name": "name1"}]
}
