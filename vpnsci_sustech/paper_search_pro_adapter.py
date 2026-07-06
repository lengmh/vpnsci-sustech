"""Compatibility wrapper for the renamed light report bridge."""

from __future__ import annotations

from . import light_report_bridge as _impl

globals().update(
    {
        name: getattr(_impl, name)
        for name in dir(_impl)
        if not (name.startswith("__") and name.endswith("__"))
    }
)

_main = _impl.main


if __name__ == "__main__":
    _main()
