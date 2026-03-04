"""
Tests for scraper/validators module.
All validators are pure functions — straightforward to test.
"""

import pytest
from scraper.validators import validate, ValidationReport, ValidationError


class TestRequired:
    """Test the 'required' rule."""

    def test_required_missing_none(self):
        """None should fail required validation."""
        report = validate({"title": None}, {"title": {"required": True}})
        assert not report.valid
        assert len(report.errors) == 1
        assert report.errors[0].field == "title"
        assert report.errors[0].rule == "required"

    def test_required_missing_field(self):
        """Missing field (not in dict) should fail required validation."""
        report = validate({}, {"title": {"required": True}})
        assert not report.valid
        assert len(report.errors) == 1
        assert report.errors[0].rule == "required"

    def test_required_present(self):
        """Present value should pass required validation."""
        report = validate({"title": "Hello"}, {"title": {"required": True}})
        assert report.valid

    def test_required_with_zero(self):
        """Zero should pass required validation (not None)."""
        report = validate({"count": 0}, {"count": {"required": True}})
        assert report.valid

    def test_required_with_false(self):
        """False should pass required validation (not None)."""
        report = validate({"active": False}, {"active": {"required": True}})
        assert report.valid

    def test_required_with_empty_string(self):
        """Empty string should pass required validation (not None)."""
        report = validate({"name": ""}, {"name": {"required": True}})
        assert report.valid


class TestType:
    """Test the 'type' rule."""

    def test_type_string_pass(self):
        """String should pass type check."""
        report = validate({"name": "Alice"}, {"name": {"type": "str"}})
        assert report.valid

    def test_type_string_fail(self):
        """Non-string should fail type check."""
        report = validate({"name": 123}, {"name": {"type": "str"}})
        assert not report.valid
        assert report.errors[0].rule == "type"
        assert "expected str" in report.errors[0].message

    def test_type_int_pass(self):
        """Integer should pass type check."""
        report = validate({"age": 25}, {"age": {"type": "int"}})
        assert report.valid

    def test_type_int_fail_with_string(self):
        """String should fail int type check."""
        report = validate({"age": "25"}, {"age": {"type": "int"}})
        assert not report.valid
        assert report.errors[0].rule == "type"

    def test_type_int_reject_float(self):
        """Float should NOT pass int type check (strict type check)."""
        report = validate({"count": 3.14}, {"count": {"type": "int"}})
        assert not report.valid
        assert report.errors[0].rule == "type"

    def test_type_float_pass(self):
        """Float should pass type check."""
        report = validate({"price": 9.99}, {"price": {"type": "float"}})
        assert report.valid

    def test_type_float_accept_int(self):
        """Int should pass float type check."""
        report = validate({"price": 10}, {"price": {"type": "float"}})
        assert report.valid

    def test_type_float_fail_string(self):
        """String should fail float type check."""
        report = validate({"price": "9.99"}, {"price": {"type": "float"}})
        assert not report.valid

    def test_type_list_pass(self):
        """List should pass type check."""
        report = validate({"tags": ["a", "b"]}, {"tags": {"type": "list"}})
        assert report.valid

    def test_type_list_fail(self):
        """Non-list should fail type check."""
        report = validate({"tags": "a,b"}, {"tags": {"type": "list"}})
        assert not report.valid

    def test_type_bool_pass(self):
        """Boolean should pass type check."""
        report = validate({"active": True}, {"active": {"type": "bool"}})
        assert report.valid

    def test_type_bool_fail(self):
        """Non-boolean should fail type check."""
        report = validate({"active": "true"}, {"active": {"type": "bool"}})
        assert not report.valid


class TestNotEmpty:
    """Test the 'not_empty' rule."""

    def test_not_empty_string_pass(self):
        """Non-empty string should pass."""
        report = validate({"name": "Alice"}, {"name": {"not_empty": True}})
        assert report.valid

    def test_not_empty_string_fail(self):
        """Empty string should fail."""
        report = validate({"name": ""}, {"name": {"not_empty": True}})
        assert not report.valid
        assert report.errors[0].rule == "not_empty"

    def test_not_empty_list_pass(self):
        """Non-empty list should pass."""
        report = validate({"items": [1, 2]}, {"items": {"not_empty": True}})
        assert report.valid

    def test_not_empty_list_fail(self):
        """Empty list should fail."""
        report = validate({"items": []}, {"items": {"not_empty": True}})
        assert not report.valid
        assert report.errors[0].rule == "not_empty"

    def test_not_empty_with_none(self):
        """None should skip not_empty check (only checks non-None values)."""
        report = validate({"name": None}, {"name": {"not_empty": True}})
        # None is not empty, it's None — not_empty only checks actual values
        assert report.valid


class TestMinMax:
    """Test the 'min' and 'max' numeric bounds."""

    def test_min_int_pass(self):
        """Value above min should pass."""
        report = validate({"age": 18}, {"age": {"min": 18}})
        assert report.valid

    def test_min_int_fail(self):
        """Value below min should fail."""
        report = validate({"age": 17}, {"age": {"min": 18}})
        assert not report.valid
        assert report.errors[0].rule == "min"
        assert "17 < min(18)" in report.errors[0].message

    def test_max_int_pass(self):
        """Value below max should pass."""
        report = validate({"age": 65}, {"age": {"max": 65}})
        assert report.valid

    def test_max_int_fail(self):
        """Value above max should fail."""
        report = validate({"age": 66}, {"age": {"max": 65}})
        assert not report.valid
        assert report.errors[0].rule == "max"

    def test_min_max_float_pass(self):
        """Float in range should pass."""
        report = validate({"price": 9.99}, {"price": {"min": 0, "max": 100}})
        assert report.valid

    def test_min_max_float_fail_min(self):
        """Float below min should fail."""
        report = validate({"price": -0.01}, {"price": {"min": 0, "max": 100}})
        assert not report.valid

    def test_min_max_float_fail_max(self):
        """Float above max should fail."""
        report = validate({"price": 100.01}, {"price": {"min": 0, "max": 100}})
        assert not report.valid

    def test_min_max_both(self):
        """Value outside both bounds should fail on min first."""
        report = validate({"value": -5}, {"value": {"min": 0, "max": 10}})
        assert not report.valid
        assert report.errors[0].rule == "min"


class TestMinMaxLength:
    """Test the 'min_length' and 'max_length' rules."""

    def test_min_length_string_pass(self):
        """String above min length should pass."""
        report = validate({"name": "Alice"}, {"name": {"min_length": 3}})
        assert report.valid

    def test_min_length_string_fail(self):
        """String below min length should fail."""
        report = validate({"name": "Al"}, {"name": {"min_length": 3}})
        assert not report.valid
        assert report.errors[0].rule == "min_length"

    def test_max_length_string_pass(self):
        """String below max length should pass."""
        report = validate({"name": "Alice"}, {"name": {"max_length": 10}})
        assert report.valid

    def test_max_length_string_fail(self):
        """String above max length should fail."""
        report = validate({"name": "Alice Bob Carol"}, {"name": {"max_length": 10}})
        assert not report.valid
        assert report.errors[0].rule == "max_length"

    def test_min_length_list_pass(self):
        """List above min length should pass."""
        report = validate({"items": [1, 2, 3]}, {"items": {"min_length": 2}})
        assert report.valid

    def test_min_length_list_fail(self):
        """List below min length should fail."""
        report = validate({"items": [1]}, {"items": {"min_length": 2}})
        assert not report.valid

    def test_max_length_list_pass(self):
        """List below max length should pass."""
        report = validate({"items": [1, 2]}, {"items": {"max_length": 5}})
        assert report.valid

    def test_max_length_list_fail(self):
        """List above max length should fail."""
        report = validate({"items": [1, 2, 3, 4, 5, 6]}, {"items": {"max_length": 5}})
        assert not report.valid


class TestPattern:
    """Test the 'pattern' regex rule."""

    def test_pattern_match_pass(self):
        """String matching pattern should pass."""
        report = validate({"email": "user@example.com"}, {"email": {"pattern": r"^[^@]+@[^@]+\.[^@]+$"}})
        assert report.valid

    def test_pattern_match_fail(self):
        """String not matching pattern should fail."""
        report = validate({"email": "not-an-email"}, {"email": {"pattern": r"^[^@]+@[^@]+\.[^@]+$"}})
        assert not report.valid
        assert report.errors[0].rule == "pattern"

    def test_pattern_digits_only(self):
        """Pattern for digits only."""
        report = validate({"zip": "12345"}, {"zip": {"pattern": r"^\d+$"}})
        assert report.valid

    def test_pattern_digits_fail(self):
        """Non-digits should fail digits-only pattern."""
        report = validate({"zip": "1234a"}, {"zip": {"pattern": r"^\d+$"}})
        assert not report.valid

    def test_pattern_ignores_non_string(self):
        """Pattern rule should be ignored for non-string values."""
        report = validate({"code": 12345}, {"code": {"pattern": r"^\d+$"}})
        # Pattern is only checked for strings, int should pass
        assert report.valid


class TestIn:
    """Test the 'in' enum rule."""

    def test_in_list_pass(self):
        """Value in list should pass."""
        report = validate({"status": "active"}, {"status": {"in": ["active", "inactive"]}})
        assert report.valid

    def test_in_list_fail(self):
        """Value not in list should fail."""
        report = validate({"status": "pending"}, {"status": {"in": ["active", "inactive"]}})
        assert not report.valid
        assert report.errors[0].rule == "in"
        assert "not in allowed values" in report.errors[0].message

    def test_in_int_list(self):
        """Enum check with integers."""
        report = validate({"priority": 2}, {"priority": {"in": [1, 2, 3]}})
        assert report.valid

    def test_in_int_list_fail(self):
        """Integer not in allowed list."""
        report = validate({"priority": 5}, {"priority": {"in": [1, 2, 3]}})
        assert not report.valid


class TestMultipleErrors:
    """Test multiple validation errors on the same field."""

    def test_multiple_rules_fail(self):
        """Multiple failing rules should all be reported."""
        report = validate(
            {"age": 15, "name": "Al"},
            {
                "age": {"type": "int", "min": 18},
                "name": {"min_length": 3, "max_length": 2}  # Impossible: both min and max
            }
        )
        assert not report.valid
        # age fails min, name fails both min_length and max_length
        assert len(report.errors) >= 2

    def test_type_and_required_both_fail(self):
        """Required and type can both fail for None."""
        report = validate({"count": None}, {"count": {"required": True, "type": "int"}})
        assert not report.valid
        # Should fail on required first and skip other checks
        assert report.errors[0].rule == "required"


class TestValidationReport:
    """Test ValidationReport properties and methods."""

    def test_report_valid_property(self):
        """Report.valid should be True when no errors."""
        report = validate({"name": "Alice"}, {"name": {"type": "str"}})
        assert report.valid is True

    def test_report_valid_property_false(self):
        """Report.valid should be False when errors exist."""
        report = validate({"age": 15}, {"age": {"min": 18}})
        assert report.valid is False

    def test_report_str_no_errors(self):
        """String representation of valid report."""
        report = ValidationReport()
        assert str(report) == "valid"

    def test_report_str_with_errors(self):
        """String representation should list errors."""
        report = ValidationReport()
        report.add("field1", "rule1", "message1")
        report.add("field2", "rule2", "message2")
        report_str = str(report)
        assert "field1" in report_str
        assert "rule1" in report_str
        assert "message1" in report_str

    def test_report_as_dict(self):
        """as_dict should return structured dict."""
        report = validate({"age": 15}, {"age": {"min": 18}})
        result = report.as_dict()
        assert result["valid"] is False
        assert "errors" in result
        assert len(result["errors"]) == 1

    def test_report_as_dict_valid(self):
        """as_dict for valid report."""
        report = validate({"age": 20}, {"age": {"min": 18}})
        result = report.as_dict()
        assert result["valid"] is True
        assert result["errors"] == []


class TestComplexScenarios:
    """Test realistic validation scenarios."""

    def test_user_profile_validation_pass(self):
        """Complete user profile validation that should pass."""
        data = {
            "name": "Alice Johnson",
            "email": "alice@example.com",
            "age": 28,
            "interests": ["coding", "reading"],
            "active": True
        }
        rules = {
            "name": {"type": "str", "min_length": 2, "max_length": 50},
            "email": {"type": "str", "pattern": r"^[^@]+@[^@]+\.[^@]+$"},
            "age": {"type": "int", "min": 18, "max": 120},
            "interests": {"type": "list", "min_length": 1},
            "active": {"type": "bool"}
        }
        report = validate(data, rules)
        assert report.valid

    def test_user_profile_validation_fail(self):
        """User profile with multiple validation errors."""
        data = {
            "name": "A",  # Too short
            "email": "invalid",  # Bad pattern
            "age": 15,  # Too young
            "interests": [],  # Empty
            "active": "yes"  # Not a bool
        }
        rules = {
            "name": {"type": "str", "min_length": 2},
            "email": {"type": "str", "pattern": r"^[^@]+@[^@]+\.[^@]+$"},
            "age": {"type": "int", "min": 18},
            "interests": {"type": "list", "not_empty": True},
            "active": {"type": "bool"}
        }
        report = validate(data, rules)
        assert not report.valid
        assert len(report.errors) >= 4

    def test_optional_field_skipped(self):
        """Optional field (not required) should be skipped if None."""
        report = validate({"name": "Alice"}, {"name": {"type": "str"}, "age": {"type": "int"}})
        assert report.valid

    def test_required_field_with_type(self):
        """Required field with type check."""
        report = validate({"count": "10"}, {"count": {"required": True, "type": "int"}})
        assert not report.valid
        # When value exists (not None), it checks type, not required
        assert report.errors[0].rule == "type"
