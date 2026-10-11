# log-format-structured-interpolator

Parses printf-style log format strings with positional arguments into a structured key-value representation for downstream observability pipelines.

## Usage

```python
from log_format_structured_interpolator import interpolate

result = interpolate("user %s performed %s", ("alice", "login"))
print(result.message)
# user alice performed login
print(result.template)
# user %s performed %s
for arg in result.args:
    print(arg.position, arg.raw, arg.formatted)
# 0 'alice' alice
# 1 'login' login
```

You can also tokenise a format string without binding arguments:

```python
from log_format_structured_interpolator import parse

tokens = parse("order %s shipped to %s")
for t in tokens:
    print(t)
```

## Why this exists

Observability pipelines want both a human-readable message and the raw argument values as structured fields. Python's `logging` module renders the final string via `%` and discards the originals. This library re-runs the same printf-style format and keeps the positional data alongside the rendered message so a downstream consumer can index on argument values without re-parsing the string.

The trade-off: only `%s` is supported. Real printf has dozens of conversion characters (`%d`, `%f`, `%x`, `%e`, `%c`, `%r`), each with platform-specific precision and padding rules. Supporting all of them means reimplementing stdio. Log strings are almost always human-readable text where every argument is a string; supporting only `%s` keeps the library tiny and its behaviour identical across Python versions. If you need numeric formatting, format the number yourself before passing it in.

## Edge you will hit

`%%` is treated as a literal percent and does **not** consume an argument. A format string with mismatched argument count — too few or too many — raises `InterpolationError`. Any conversion character other than `s` (`%d`, `%f`, etc.) also raises `InterpolationError`; there is no silent fallback.
