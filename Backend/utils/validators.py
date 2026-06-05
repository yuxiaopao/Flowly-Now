"""
Validation utilities for forms and data.
"""

import re
from typing import Any, Dict, List, Optional, Tuple, Callable
from decimal import Decimal, InvalidOperationationError


class ValidationError(Exception):
    """Validation error exception."""

    def __init__(self, message: str, field: str = None):
        self.message = message
        self.field = field
        super().__init__(message)


class Validator:
    """Base validator class."""

    def __init__(self, error_message: str = None):
        self.error_message = error_message or 'Validation failed'

    def validate(self, value: Any) -> bool:
        raise NotImplementedError

    def __call__(self, value: Any) -> Any:
        if not self.validate(value):
            raise ValidationError(self.error_message)
        return value


class RequiredValidator(Validator):
    """Validate that value is not empty."""

    def validate(self, value: Any) -> bool:
        if value is None:
            return False
        if isinstance(value, str) and not value.strip():
            return False
        if isinstance(value, (list, dict, tuple)) and len(value) == 0:
            return False
        return True


class EmailValidator(Validator):
    """Validate email address."""

    def __init__(self, error_message: str = '请输入有效的邮箱地址'):
        super().__init__(error_message)

    def validate(self, value: Any) -> bool:
        if not value:
            return True  # Let RequiredValidator handle empty
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, str(value)))


class URLValidator(Validator):
    """Validate URL."""

    def __init__(self, error_message: str = '请输入有效的URL地址'):
        super().__init__(error_message)

    def validate(self, value: Any) -> bool:
        if not value:
            return True
        pattern = r'^https?://[^\s/$.?#].[^\s]*$'
        return bool(re.match(pattern, str(value)))


class LengthValidator(Validator):
    """Validate string length."""

    def __init__(
        self,
        min_length: int = None,
        max_length: int = None,
        error_message: str = None
    ):
        super().__init__(error_message)
        self.min_length = min_length
        self.max_length = max_length

    def validate(self, value: Any) -> bool:
        if not value:
            return True
        length = len(str(value))
        if self.min_length is not None and length < self.min_length:
            self.error_message = f'长度不能少于{self.min_length}个字符'
            return False
        if self.max_length is not None and length > self.max_length:
            self.error_message = f'长度不能超过{self.max_length}个字符'
            return False
        return True


class RangeValidator(Validator):
    """Validate numeric range."""

    def __init__(
        self,
        min_value: float = None,
        max_value: float = None,
        error_message: str = None
    ):
        super().__init__(error_message)
        self.min_value = min_value
        self.max_value = max_value

    def validate(self, value: Any) -> bool:
        try:
            num = float(value)
            if self.min_value is not None and num < self.min_value:
                self.error_message = f'值不能小于{self.min_value}'
                return False
            if self.max_value is not None and num > self.max_value:
                self.error_message = f'值不能大于{self.max_value}'
                return False
            return True
        except (TypeError, ValueError):
            self.error_message = '请输入有效的数字'
            return False


class RegexValidator(Validator):
    """Validate against regex pattern."""

    def __init__(self, pattern: str, error_message: str = None):
        super().__init__(error_message)
        self.pattern = re.compile(pattern)

    def validate(self, value: Any) -> bool:
        if not value:
            return True
        return bool(self.pattern.match(str(value)))


class ChoicesValidator(Validator):
    """Validate against allowed choices."""

    def __init__(self, choices: List[Any], error_message: str = None):
        super().__init__(error_message)
        self.choices = choices

    def validate(self, value: Any) -> bool:
        if value is None:
            return True
        return value in self.choices


class SchemaValidator:
    """Validate data against a schema."""

    def __init__(self, schema: Dict[str, List[Validator]]):
        self.schema = schema

    def validate(self, data: Dict) -> Dict[str, List[str]]:
        """Validate data and return errors."""
        errors = {}

        for field, validators in self.schema.items():
            value = data.get(field)
            field_errors = []

            for validator in validators:
                try:
                    validator(value)
                except ValidationError as e:
                    field_errors.append(e.message)

            if field_errors:
                errors[field] = field_errors

        return errors

    def is_valid(self, data: Dict) -> bool:
        """Check if data is valid."""
        return len(self.validate(data)) == 0


def validate_workflow_data(data: Dict) -> Dict[str, List[str]]:
    """Validate workflow creation/update data."""
    schema = SchemaValidator({
        'name': [
            RequiredValidator('请输入工作流名称'),
            LengthValidator(min_length=1, max_length=100)
        ],
        'description': [
            LengthValidator(max_length=500)
        ]
    })
    return schema.validate(data)


def validate_agent_data(data: Dict) -> Dict[str, List[str]]:
    """Validate agent creation/update data."""
    schema = SchemaValidator({
        'name': [
            RequiredValidator('请输入Agent名称'),
            LengthValidator(min_length=1, max_length=100)
        ],
        'model': [
            RequiredValidator('请选择AI模型')
        ]
    })
    return schema.validate(data)
