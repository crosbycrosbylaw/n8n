from __future__ import annotations

from typing import TYPE_CHECKING, Literal, cast, overload

if TYPE_CHECKING:
    from eserv.monitor.result import ErrorDict
    from eserv.monitor.types import StatusFlag


@overload
def status_flag(*, success: Literal[True] = True) -> StatusFlag: ...
@overload
def status_flag(error: ErrorDict) -> StatusFlag: ...
def status_flag(
    error: ErrorDict | None = None,
    *,
    success: Literal[True] | None = None,
) -> StatusFlag:
    """Create a status flag with the given value.

    Args:
        error (ErrorDict):
            The error dictionary for an exception that occurred in the pipeline. Used in formatting the value of the flag.
        success (Literal[True]):
            Indicates that no error occurred in pipeline execution.

    Returns:
        A `StatusFlag` dictionary with id and value.

    """
    out = {'id': 'String {00020329-0000-0000-C000-000000000046} Name eserv_flag'}

    if error is None or success is True:
        out['value'] = '$eserv_success'
    elif (category := error['category']).startswith('$eserv_error:'):
        out['value'] = category
    else:
        out['value'] = f'$eserv_error:{category}'

    return cast('StatusFlag', out)
