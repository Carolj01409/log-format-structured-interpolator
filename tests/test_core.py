import unittest

from log_format_structured_interpolator import (
    interpolate,
    parse,
    InterpolationError,
    StructuredLog,
)
from log_format_structured_interpolator.core import (
    LiteralToken,
    SpecifierToken,
    ArgRecord,
)


class TestParse(unittest.TestCase):
    def test_parse_plain_string(self):
        tokens = parse("hello world")
        self.assertEqual(tokens, [LiteralToken(text="hello world")])

    def test_parse_single_specifier(self):
        tokens = parse("user %s logged in")
        self.assertEqual(tokens, [
            LiteralToken(text="user "),
            SpecifierToken(spec="%s"),
            LiteralToken(text=" logged in"),
        ])

    def test_parse_escaped_percent(self):
        tokens = parse("100%% done")
        self.assertEqual(tokens, [LiteralToken(text="100% done")])

    def test_parse_consecutive_specifiers(self):
        tokens = parse("%s%s")
        self.assertEqual(tokens, [
            SpecifierToken(spec="%s"),
            SpecifierToken(spec="%s"),
        ])

    def test_parse_leading_specifier(self):
        tokens = parse("%s at start")
        self.assertEqual(tokens, [
            SpecifierToken(spec="%s"),
            LiteralToken(text=" at start"),
        ])

    def test_parse_unsupported_conversion(self):
        with self.assertRaises(InterpolationError) as ctx:
            parse("count is %d")
        self.assertIn("unsupported conversion specifier", str(ctx.exception))

    def test_parse_trailing_percent(self):
        with self.assertRaises(InterpolationError):
            parse("incomplete %")


class TestInterpolate(unittest.TestCase):
    def test_basic_interpolation(self):
        result = interpolate("hello %s", ("world",))
        self.assertIsInstance(result, StructuredLog)
        self.assertEqual(result.message, "hello world")
        self.assertEqual(result.template, "hello %s")
        self.assertEqual(len(result.args), 1)
        self.assertEqual(result.args[0].position, 0)
        self.assertEqual(result.args[0].raw, "'world'")
        self.assertEqual(result.args[0].formatted, "world")

    def test_multiple_args(self):
        result = interpolate("%s and %s", ("foo", "bar"))
        self.assertEqual(result.message, "foo and bar")
        self.assertEqual([a.formatted for a in result.args], ["foo", "bar"])
        self.assertEqual([a.position for a in result.args], [0, 1])

    def test_non_string_arg(self):
        result = interpolate("count=%s", (42,))
        self.assertEqual(result.message, "count=42")
        self.assertEqual(result.args[0].raw, "42")
        self.assertEqual(result.args[0].formatted, "42")

    def test_arg_with_repr(self):
        obj = [1, 2, 3]
        result = interpolate("data=%s", (obj,))
        self.assertEqual(result.message, "data=[1, 2, 3]")
        self.assertEqual(result.args[0].raw, "[1, 2, 3]")

    def test_too_few_args(self):
        with self.assertRaises(InterpolationError) as ctx:
            interpolate("%s %s %s", ("a", "b"))
        self.assertIn("not enough arguments", str(ctx.exception))

    def test_too_many_args(self):
        with self.assertRaises(InterpolationError) as ctx:
            interpolate("%s", ("a", "b"))
        self.assertIn("too many arguments", str(ctx.exception))

    def test_escaped_percent_does_not_consume_arg(self):
        result = interpolate("100%% complete: %s", ("done",))
        self.assertEqual(result.message, "100% complete: done")
        self.assertEqual(len(result.args), 1)

    def test_no_specifiers_no_args(self):
        result = interpolate("static message", ())
        self.assertEqual(result.message, "static message")
        self.assertEqual(result.args, [])

    def test_consecutive_specifiers(self):
        result = interpolate("%s%s%s", ("a", "b", "c"))
        self.assertEqual(result.message, "abc")
        self.assertEqual([a.position for a in result.args], [0, 1, 2])

    def test_empty_string(self):
        result = interpolate("", ())
        self.assertEqual(result.message, "")
        self.assertEqual(result.args, [])

    def test_non_str_format_raises(self):
        with self.assertRaises(InterpolationError):
            interpolate(123, ("x",))  # type: ignore[arg-type]

    def test_non_tuple_args_raises(self):
        with self.assertRaises(InterpolationError):
            interpolate("%s", ["x"])  # type: ignore[arg-type]

    def test_arg_record_fields(self):
        result = interpolate("v=%s", (7,))
        rec = result.args[0]
        self.assertIsInstance(rec, ArgRecord)
        self.assertEqual(rec.position, 0)
        self.assertEqual(rec.raw, "7")
        self.assertEqual(rec.formatted, "7")

    def test_str_includes_none(self):
        result = interpolate("value=%s", (None,))
        self.assertEqual(result.message, "value=None")
        self.assertEqual(result.args[0].formatted, "None")


if __name__ == "__main__":
    unittest.main()
