# Testing Standards

This document defines the standardized testing patterns used across the eserv test suite.

## Overview

Three distinct testing patterns are used based on test complexity and purpose:

1. **Scenario Factory Pattern** - Simple data-driven tests
2. **Fixture Class Pattern** - Complex orchestration with extensive mocking
3. **Class-Based Pattern** - Traditional unit tests with logical grouping

## Pattern A: Scenario Factory Pattern

**Use when:**
- Testing pure functions or simple components
- Multiple test cases with varying inputs/outputs
- Minimal or no mocking required
- Data-driven testing scenarios

**Structure:**

```python
from __future__ import annotations

from typing import TYPE_CHECKING
from rampy import test

if TYPE_CHECKING:
    from typing import Any


def factory_name_scenario(
    *,
    param1: type1,
    param2: type2,
    expected_result: type3,
) -> dict[str, Any]:
    """Create test scenario for ComponentName."""
    return {
        'params': [param1, param2],  # Positional args to function under test
        'expected_result': expected_result,  # Named params injected to test
    }


@test.scenarios(**{
    'descriptive name 1': factory_name_scenario(
        param1=value1,
        param2=value2,
        expected_result=expected1,
    ),
    'descriptive name 2': factory_name_scenario(
        param1=value3,
        param2=value4,
        expected_result=expected2,
    ),
})
class TestComponentName:
    def test(
        self,
        /,  # Positional-only separator
        params: list[Any],
        expected_result: type3,
    ):
        """Test component behavior."""
        param1, param2 = params
        result = function_under_test(param1, param2)

        assert result == expected_result
```

**Key conventions:**
- Scenario factory function named `{component}_scenario`
- Factory returns `dict[str, Any]`
- `params` key contains list of positional arguments
- Other keys become named test parameters
- Test method uses positional-only `self` parameter (`/`)
- Test method named simply `test`
- Docstrings describe behavior, not scenario name

**Reference:** `tests/eserv/util/test_target_finder.py`

---

## Pattern B: Fixture Class Pattern

**Use when:**
- Complex mock orchestration required
- Multiple related test scenarios with shared setup
- Testing functions with many dependencies
- Need for reusable test harness

**Structure:**

```python
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import field
from typing import TYPE_CHECKING, Any, Self
from unittest.mock import Mock, patch

import pytest
from pytest_fixture_classes import fixture_class
from rampy import test

if TYPE_CHECKING:
    from collections.abc import Callable, Generator, Sequence
    from inspect import BoundArguments


# Basic fixtures
@pytest.fixture
def mock_dependency1() -> Mock:
    """Create mock for Dependency1."""
    return Mock(attr1='value1', attr2='value2')


@pytest.fixture
def mock_dependency2() -> Mock:
    """Create mock for Dependency2."""
    return Mock()


# Composite fixture
@pytest.fixture
def mock_config(mock_dependency1: Mock, mock_dependency2: Mock) -> Mock:
    """Create mock Config object."""
    return Mock(
        dep1=mock_dependency1,
        dep2=mock_dependency2,
    )


# Advanced fixture class for orchestration
@fixture_class(name='run_component_subtest')
class ComponentSubtestFixture(test.subtestfix):
    """Orchestrate complex test scenarios with mock setup."""

    subtests: ...
    factory = staticmethod(function_under_test)

    # Required dependencies (from pytest fixtures)
    mock_config: Mock
    mock_dependency1: Mock

    # Internal mocks (created by fixture class)
    mock_internal1: Mock = field(init=False, default_factory=Mock)
    mock_internal2: Mock = field(init=False, default_factory=Mock)

    @contextmanager
    def context(self) -> Generator[Any]:
        """Patch all dependencies."""
        try:
            with (
                patch('module.path.Class1', return_value=self.mock_internal1),
                patch('module.path.Class2', return_value=self.mock_internal2),
            ):
                yield
        finally:
            pass

    def converter(self, **kwds: Any) -> BoundArguments:
        """Convert scenario kwargs to factory arguments."""
        # Configure mocks based on scenario parameters
        self.mock_internal1.configure_mock(**{
            'method1.return_value': kwds['return1'],
        })

        self.mock_internal2.configure_mock(**{
            'method2.return_value': kwds['return2'],
        })

        # Bind arguments to factory function
        return self.bind_factory(
            arg1=kwds['arg1'],
            arg2=kwds['arg2'],
            config=self.mock_config,
        )

    def __call__(
        self,
        name: str,
        *,
        arg1: type1,
        arg2: type2,
        return1: type3,
        return2: type4,
        extensions: Callable[[Self], Sequence[None] | dict[str, Any]] | None = None,
        assertions: Callable[[ResultType], dict[str, Any]] | None = None,
        **_: ...,
    ) -> None:
        """Invoke subtest with scenario name and assertions."""
        super()._subtest(
            name,
            arg1=arg1,
            arg2=arg2,
            return1=return1,
            return2=return2,
            extensions=extensions,
            assertions=assertions,
        )
```

**Usage in test file:**

```python
def test_component_orchestration(
    mock_dependency: Mock,
    run_component_subtest: ComponentSubtestFixture,
) -> None:
    """Test various component behaviors."""
    run_component_subtest(
        'scenario 1 description',
        arg1=value1,
        arg2=value2,
        return1=expected1,
        return2=expected2,
        assertions=lambda res: {
            'result should match': res.value == expected1,
            'status should be success': res.status == 'success',
        },
        extensions=lambda self: [
            self.mock_internal1.method1.assert_called_once(),
            self.mock_internal2.method2.assert_called_once(),
        ],
    )

    run_component_subtest(
        'scenario 2 description',
        arg1=value3,
        arg2=value4,
        return1=expected3,
        return2=expected4,
        assertions=lambda res: {
            'different assertion': res.value == expected3,
        },
    )
```

**Key conventions:**
- Fixture class extends `test.subtestfix`
- Basic fixtures defined first, composite fixtures second
- Fixture class defined last in conftest.py
- `context()` method manages patches via context manager
- `converter()` transforms scenario kwargs to function arguments
- `__call__()` defines scenario interface
- `assertions` parameter takes dict-returning lambda
- `extensions` parameter for mock assertions
- Fixture class has `init=False` fields for internal mocks

**Reference:** `tests/eserv/stages/conftest.py` and `tests/eserv/stages/test_upload.py`

---

## Pattern C: Class-Based Pattern

**Use when:**
- Grouping logically related unit tests
- Simple fixtures without complex orchestration
- One behavior per test method
- Traditional pytest organization preferred

**Structure:**

```python
from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import Mock, patch

import pytest

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def mock_dependency() -> Mock:
    """Create mock dependency."""
    return Mock(attr='value')


class TestComponentInitialization:
    """Test component initialization."""

    def test_initialization_with_config(self, mock_dependency: Mock) -> None:
        """Test component initializes with config."""
        component = Component(config=mock_dependency)

        assert component.config is mock_dependency

    def test_initialization_sets_defaults(self) -> None:
        """Test component sets default values."""
        component = Component()

        assert component.default_value == expected


class TestComponentBehavior:
    """Test component core behavior."""

    def test_method_returns_expected_value(self, mock_dependency: Mock) -> None:
        """Test method returns expected value."""
        with patch('module.path.function') as mock_func:
            mock_func.return_value = 'expected'

            component = Component(config=mock_dependency)
            result = component.method()

            assert result == 'expected'
```

**Key conventions:**
- Group related tests by class
- Class names describe component and aspect being tested
- One test method per specific behavior
- Descriptive test method names with `test_` prefix
- Use fixtures for shared setup
- Use `with patch()` for inline mocking
- Assertions focused on single behavior

**Reference:** `tests/eserv/test_core.py`

---

## Common Conventions

### Import Organization

```python
from __future__ import annotations

# Standard library imports
from typing import TYPE_CHECKING
from unittest.mock import Mock, patch

# Third-party imports
import pytest
from pytest_fixture_classes import fixture_class
from rampy import test

# Project imports
from eserv.module import function_under_test

# Type-only imports
if TYPE_CHECKING:
    from collections.abc import Callable, Generator, Sequence
    from typing import Any

    from eserv.types import CustomType
```

### Fixture Patterns

**Simple fixtures:**
```python
@pytest.fixture
def mock_object() -> Mock:
    """Create mock object."""
    return Mock(attr='value')
```

**Composite fixtures:**
```python
@pytest.fixture
def mock_config(mock_dep1: Mock, mock_dep2: Mock) -> Mock:
    """Create mock config from dependencies."""
    return Mock(dep1=mock_dep1, dep2=mock_dep2)
```

**Fixture classes:**
```python
@fixture_class(name='fixture_name')
class FixtureClass:
    """Fixture class description."""

    dependency: Type  # Injected from pytest fixture

    def __call__(self, ...) -> ...:
        """Callable implementation."""
```

### Tempdir Management

**Use rampy's test.directory():**
```python
@pytest.fixture
def tempdir() -> Generator[Path]:
    path = test.directory('pytest_temp')
    try:
        yield path
    finally:
        path.clean()
```

**NOT manual tempfile/shutil:**
```python
# DON'T DO THIS
temp_dir = Path(tempfile.mkdtemp())
try:
    # ... test code ...
finally:
    shutil.rmtree(temp_dir)
```

### Exception Testing

**Scenario pattern:**
```python
def scenario_factory(
    *,
    input_val: str,
    should_raise: type[Exception] | None = None,
) -> dict[str, Any]:
    return {
        'params': [input_val],
        'should_raise': should_raise,
    }


@test.scenarios(**{
    'valid input': scenario_factory(input_val='valid'),
    'invalid input': scenario_factory(input_val='invalid', should_raise=ValueError),
})
class TestValidation:
    def test(self, /, params: list[Any], should_raise: type[Exception] | None):
        input_val = params[0]

        if should_raise is not None:
            with pytest.raises(should_raise):
                function_under_test(input_val)
        else:
            result = function_under_test(input_val)
            assert result is not None
```

**Class-based pattern:**
```python
def test_invalid_input_raises_error(self) -> None:
    """Test invalid input raises ValueError."""
    with pytest.raises(ValueError):
        function_under_test('invalid')
```

---

## Pattern Selection Guide

Use this decision tree:

```
START
│
├─ Complex mocking (3+ patches)?
│  └─ YES → Pattern B (Fixture Class)
│
├─ Multiple similar test cases?
│  └─ YES → Pattern A (Scenario Factory)
│
├─ Logical grouping of unit tests?
│  └─ YES → Pattern C (Class-Based)
│
└─ Default → Pattern A (Scenario Factory)
```

**Examples:**

| Test File | Pattern | Reason |
|-----------|---------|--------|
| `test_target_finder.py` | A | Pure functions, data-driven |
| `test_upload.py` | B | Complex mocking (Dropbox, matcher, cache) |
| `test_core.py` | C | Logical grouping of Pipeline tests |
| `test_extract_*.py` | A | Simple extraction, multiple cases |
| `test_processor.py` | A | Can use scenario factories instead of dataclasses |
| `test_email_state.py` | A | Simple state tracking, multiple scenarios |

---

## Anti-Patterns to Avoid

### ❌ Complex conditional logic in test body

```python
# DON'T DO THIS
def test(self, /, params, switch1, switch2, switch3):
    if switch1:
        # do something
    elif switch2:
        # do something else

    if switch3:
        # verify something
```

**Fix:** Split into separate test scenarios or use Pattern B with extensions.

### ❌ Generic factory names

```python
# DON'T DO THIS
def scenario(...):
    return {...}
```

**Fix:** Use descriptive names: `{component}_scenario`.

### ❌ Dataclass scenarios for simple cases

```python
# DON'T DO THIS (unless very complex)
@dataclass(frozen=True, slots=True, kw_only=True)
class my_scenario:
    input: str
    expected: str
```

**Fix:** Use simple factory functions returning dicts.

### ❌ Manual tempdir management

```python
# DON'T DO THIS
temp_dir = Path(tempfile.mkdtemp())
shutil.rmtree(temp_dir)
```

**Fix:** Use `rampy.test.directory()` with cleanup.

### ❌ Nested mocking in test body

```python
# DON'T DO THIS
def test_something(self):
    with patch('mod.Class1') as m1:
        with patch('mod.Class2') as m2:
            with patch('mod.Class3') as m3:
                # test code
```

**Fix:** Use Pattern B with fixture class and context manager.

---

## Migration Checklist

When updating tests to comply with standards:

- [ ] Identify appropriate pattern (A, B, or C)
- [ ] Update imports to match pattern
- [ ] Create scenario factory functions (Pattern A) or fixture class (Pattern B)
- [ ] Use positional-only `self` parameter for scenario tests
- [ ] Replace manual tempdir with `rampy.test.directory()`
- [ ] Move complex setup to `converter()` method (Pattern B)
- [ ] Use lambda assertions and extensions (Pattern B)
- [ ] Remove conditional logic from test body
- [ ] Add descriptive docstrings
- [ ] Verify tests still pass

---

## References

**Primary examples:**
- Pattern A: `tests/eserv/util/test_target_finder.py`
- Pattern B: `tests/eserv/stages/conftest.py` + `tests/eserv/stages/test_upload.py`
- Pattern C: `tests/eserv/test_core.py`

**Supporting documentation:**
- pytest: https://docs.pytest.org/
- pytest-fixture-classes: https://github.com/rampy/pytest-fixture-classes
- rampy: https://github.com/rampy/rampy
