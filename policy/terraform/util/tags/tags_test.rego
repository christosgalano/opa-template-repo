package terraform.util.tags_test

import data.terraform.util.tags as t

# Test that tags returns the tags of a resource
test__tags if {
	tags := t._tags({"change": {"after": {"tags": {"tag1": "value1", "tag2": "value2"}}}})
	tags == {"tag1": "value1", "tag2": "value2"}
}

# Test that has_tag returns true if the tag exists
test_has_tag if {
	t.has_tag({"change": {"after": {"tags": {"tag1": "value1", "tag2": "value2"}}}}, "tag1")
}

# Test that has_tag returns false if the tag does not exist
test_has_tag_not_exists if {
	not t.has_tag({"change": {"after": {"tags": {"tag1": "value1", "tag2": "value2"}}}}, "tag3")
}

# Test that tag_equals returns true if the tag has the correct value
test_tag_equals_correct if {
	t.tag_equals({"change": {"after": {"tags": {"tag1": "value1", "tag2": "value2"}}}}, "tag1", "value1")
}

# Test that tag_equals returns false if the tag has the wrong value
test_tag_equals_wrong if {
	not t.tag_equals({"change": {"after": {"tags": {"tag1": "value1", "tag2": "value2"}}}}, "tag1", "value2")
}

# Test that has_all_tags returns true if all tags are present
test_has_all_tags_present if {
	t.has_all_tags({"change": {"after": {"tags": {"tag1": "value1", "tag2": "value2"}}}}, {"tag1", "tag2"})
}

# Test that has_all_tags returns false if some tags are missing
test_has_all_tags_missing if {
	not t.has_all_tags({"change": {"after": {"tags": {"tag1": "value1", "tag2": "value2"}}}}, {"tag1", "tag2", "tag3"})
}
