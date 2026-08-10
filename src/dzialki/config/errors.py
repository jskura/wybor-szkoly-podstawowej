"""Configuration errors.

None of these inherit from ``OSError``. A bare operating-system error says a path
is missing; it does not say what the reader should do about it. Every error here
names the file and the next action.
"""

from __future__ import annotations


class ConfigError(Exception):
    """The configuration is absent, malformed, or incomplete."""


class AnchorConfigMissing(ConfigError):
    """``config/anchors.yml`` is not there.

    The anchors are the owner's two places of interest. The file is gitignored on
    purpose (FR-23), so a fresh checkout never has it and the error must say where
    the template lives.
    """


class ParamsConfigMissing(ConfigError):
    """``config/params.yml`` is not there.

    Unlike the anchors, this file is committed. Its absence means a broken
    checkout, not a first run.
    """
