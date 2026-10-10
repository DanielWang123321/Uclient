"""JSON-RPC error codes (design doc §5.4)."""

from __future__ import annotations

from typing import Any

PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603
AUTH_FAILED = 1001
API_VERSION_MISMATCH = 1002
ROBOT_NOT_FOUND = 2001
SESSION_NOT_FOUND = 2002
ASSET_ERROR = 2003
CALIBRATION_INVALID = 2004
IK_UNREACHABLE = 3001
IK_NOT_CONVERGED = 3002
JOINT_LIMIT = 3003
SINGULAR = 3004
JOB_CANCELLED = 4001
BACKEND_UNAVAILABLE = 5001


class RpcError(Exception):
    def __init__(self, code: int, message: str, data: Any = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data

    def to_dict(self) -> dict[str, Any]:
        err: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.data is not None:
            err["data"] = self.data
        return err


def invalid_params(message: str) -> RpcError:
    return RpcError(INVALID_PARAMS, message)
