import unittest

from posix_shell_word_expander import ExpansionError, expand


class ExpandTests(unittest.TestCase):
    def test_empty_input_yields_no_fields(self) -> None:
        self.assertEqual(expand(""), [])

    def test_only_whitespace_yields_no_fields(self) -> None:
        self.assertEqual(expand("   \t\n  "), [])

    def test_simple_words(self) -> None:
        self.assertEqual(expand("alpha beta gamma"), ["alpha", "beta", "gamma"])

    def test_single_quotes_preserve_spaces(self) -> None:
        self.assertEqual(expand("'a b' c"), ["a b", "c"])

    def test_double_quotes_preserve_spaces(self) -> None:
        self.assertEqual(expand('"a b" c'), ["a b", "c"])

    def test_empty_quoted_string_is_a_field(self) -> None:
        self.assertEqual(expand("''"), [""])
        self.assertEqual(expand('""'), [""])
        self.assertEqual(expand("a '' b"), ["a", "", "b"])

    def test_adjacent_quoted_and_unquoted_concatenate(self) -> None:
        self.assertEqual(expand("a'b c'd"), ["ab cd"])
        self.assertEqual(expand('a"b c"d'), ["ab cd"])

    def test_backslash_escapes_special_character(self) -> None:
        self.assertEqual(expand(r"a\ b"), ["a b"])
        self.assertEqual(expand(r"\""), ['"'])
        self.assertEqual(expand(r"\\"), ["\\"])

    def test_backslash_inside_double_quotes_only_escapes_special_set(self) -> None:
        # \n is not in the double-quote escape set, so the backslash survives.
        self.assertEqual(expand('"a\\nb"'), ["a\\nb"])
        # \" is in the set, so the quote is literal and the string continues.
        self.assertEqual(expand('"a\\"b"'), ['a"b'])

    def test_line_continuation_outside_quotes(self) -> None:
        self.assertEqual(expand("a\\\nb"), ["ab"])

    def test_line_continuation_inside_double_quotes(self) -> None:
        self.assertEqual(expand('"a\\\nb"'), ["ab"])

    def test_unterminated_single_quote_raises(self) -> None:
        with self.assertRaises(ExpansionError):
            expand("'unterminated")

    def test_unterminated_double_quote_raises(self) -> None:
        with self.assertRaises(ExpansionError):
            expand('"unterminated')

    def test_trailing_backslash_raises(self) -> None:
        with self.assertRaises(ExpansionError):
            expand("trailing\\")

    def test_custom_ifs_whitespace(self) -> None:
        self.assertEqual(expand("a:b:c", ifs=":"), ["a", "b", "c"])

    def test_custom_ifs_nonwhitespace_produces_empty_fields(self) -> None:
        # A non-whitespace IFS delimiter at the start of input yields an
        # empty leading field, matching the shell's behaviour.
        self.assertEqual(expand(":a:b", ifs=":"), ["", "a", "b"])
        self.assertEqual(expand("a::b", ifs=":"), ["a", "", "b"])

    def test_empty_ifs_disables_splitting(self) -> None:
        self.assertEqual(expand("a b c", ifs=""), ["a b c"])

    def test_quoted_ifs_characters_are_not_delimiters(self) -> None:
        self.assertEqual(expand("a'b c'd", ifs=" "), ["ab cd"])

    def test_ifs_whitespace_is_collapsed(self) -> None:
        self.assertEqual(expand("a   b\t\tc"), ["a", "b", "c"])

    def test_mixed_ifs_whitespace_and_nonwhitespace(self) -> None:
        # POSIX: IFS whitespace adjacent to a non-whitespace delimiter is
        # absorbed; the non-whitespace delimiter still produces a field
        # boundary.
        self.assertEqual(expand("a : b", ifs=" :"), ["a", "", "b"])


if __name__ == "__main__":
    unittest.main()
