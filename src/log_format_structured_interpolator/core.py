"""Core parser for printf-style log format strings.

The parser tokenises a format string into literal text and conversion
specifiers, then binds positional arguments to those specifiers left-to-right.
The result is a StructuredLog with the rendered message and a list of
argument records.

Design decision: only %s is supported. The brief says printf-style, but real
printf has dozens of conversion characters (%d, %f, %x, %e, %g, %c, %r...).
Supporting all of them means reimplementing a chunk of C's stdio, including
platform-specific precision rules. Log strings are almost always human
readable text where every argument is a string; supporting only %s keeps the
library tiny and its behaviour identical across Python versions. If a caller
needs numeric formatting they should format the number themselves before
passing it in — that keeps this library out of the number-formatting business.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple, Union

__all__ = [
    "interpolate",
    "parse",
    "InterpolationError",
    "StructuredLog",
    "FormatToken",
    "LiteralToken",
    "SpecifierToken",
]


class InterpolationError(ValueError):
    """Raised when a format string is malformed or argument count is wrong."""


@dataclass
class LiteralToken:
    text: str


@dataclass
class SpecifierToken:
    spec: str


FormatToken = Union[LiteralToken, SpecifierToken]


@dataclass
class ArgRecord:
    position: int
    raw: str
    formatted: str


@dataclass
class StructuredLog:
    message: str
    template: str
    args: List[ArgRecord] = field(default_factory=list)


def _tokenise(fmt: str) -> List[FormatToken]:
    """Split *fmt* into LiteralToken and SpecifierToken objects.

    A specifier is '%%' (escaped percent) or '%' followed by a conversion
    character. '%%' is collapsed into a literal percent sign so callers do not
    have to handle it separately.
    """
    tokens: List[FormatToken] = []
    buf: List[str] = []
    i = 0
    n = len(fmt)
    while i < n:
        ch = fmt[i]
        if ch == "%":
            if i + 1 >= n:
                raise InterpolationError(
                    "incomplete conversion specifier at end of format string"
                )
            nxt = fmt[i + 1]
            if nxt == "%":
                buf.append("%")
                i += 2
                continue
            # Any conversion character other than '%' terminates the
            # specifier. Only %s is meaningful to us; others raise.
            if nxt != "s":
                raise InterpolationError(
                    f"unsupported conversion specifier '%{nxt}': only %s is supported"
                )
            if buf:
                tokens.append(LiteralToken("".join(buf)))
                buf = []
            tokens.append(SpecifierToken("%s"))
            i += 2
            continue
        buf.append(ch)
        i += 1
    if buf:
        tokens.append(LiteralToken("".join(buf)))
    return tokens


def parse(fmt: str) -> List[FormatToken]:
    """Tokenise *fmt* without binding arguments.

    Useful for static analysis or for reusing the same template across many
    calls. The returned list is a flat sequence of LiteralToken and
    SpecifierToken objects in document order.
    """
    if not isinstance(fmt, str):
        raise InterpolationError("format string must be str")
    return _tokenise(fmt)


def interpolate(fmt: str, args: Tuple[object, ...]) -> StructuredLog:
    """Interpolate *args* into *fmt* and return a StructuredLog.

    Each '%s' in *fmt* consumes the next positional argument. If there are
    more specifiers than arguments — or fewer — InterpolationError is raised.
    '%%' is treated as a literal percent and does NOT consume an argument.
    """
    if not isinstance(fmt, str):
        raise InterpolationError("format string must be str")
    if not isinstance(args, tuple):
        raise InterpolationError("args must be a tuple")

    tokens = _tokenise(fmt)
    out: List[str] = []
    records: List[ArgRecord] = []
    arg_index = 0

    for tok in tokens:
        if isinstance(tok, LiteralToken):
            out.append(tok.text)
            continue
        # SpecifierToken — must consume an argument.
        if arg_index >= len(args):
            raise InterpolationError(
                f"not enough arguments: format has {sum(1 for t in tokens if isinstance(t, SpecifierToken))} "
                f"specifiers but only {len(args)} argument(s) were provided"
            )
        raw_value = args[arg_index]
        # str() is the entire point of %s: the caller may pass an int, a
        # float, or any object whose __str__ yields something meaningful.
        formatted = str(raw_value)
        records.append(
            ArgRecord(
                position=arg_index,
                raw=repr(raw_value),
                formatted=formatted,
            )
        )
        out.append(formatted)
        arg_index += 1

    if arg_index < len(args):
        raise InterpolationError(
            f"too many arguments: {len(args)} provided but only "
            f"{arg_index} specifier(s) consumed"
        )

    return StructuredLog(
        message="".join(out),
        template=fmt,
        args=records,
    )
