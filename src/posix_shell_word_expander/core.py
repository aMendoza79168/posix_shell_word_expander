"""POSIX-compliant word splitting and quote removal.

The implementation deliberately follows the POSIX shell grammar for words as
described in XCU 2.10.1 (Shell Grammar Lexical Conventions) and 2.6 (Word
Expansions), but stops before any expansion that would require a shell
environment: no parameter expansion, command substitution, arithmetic, or
pathname expansion is performed.  The only transformations are:

* field splitting of the unquoted result on IFS whitespace
* removal of quoting characters (backslash, single quotes, double quotes)

The choice to keep the expander purely lexical is intentional.  A caller that
wants full shell semantics should use a real shell; a caller that wants to
parse a command line safely (for example, to re-dispatch to ``execve``) wants
exactly this subset, and no more.  Keeping the surface small also means the
behaviour is easy to specify and test.
"""

from __future__ import annotations

from typing import List


class ExpansionError(ValueError):
    """Raised when the input cannot be lexed as a POSIX shell word list.

    The only structural error the lexer recognises is an unterminated quote.
    Everything else, including backslash at end of input, is handled by the
    quoting rules below.
    """


# Characters treated as IFS whitespace by default.  POSIX says IFS whitespace
# is space, tab, and newline; the caller may override the whole IFS string but
# only these three characters are ever treated as *whitespace* for the purpose
# of collapsing runs.  Other IFS characters are field delimiters that produce
# empty fields.
_DEFAULT_IFS = " \t\n"
_IFS_WHITESPACE = " \t\n"


def _is_ifs_whitespace(ch: str, ifs: str) -> bool:
    return ch in _IFS_WHITESPACE and ch in ifs


def _is_ifs_nonwhitespace(ch: str, ifs: str) -> bool:
    return ch in ifs and ch not in _IFS_WHITESPACE


def expand(text: str, ifs: str = _DEFAULT_IFS) -> List[str]:
    """Split *text* into fields using POSIX word splitting and quote removal.

    Parameters
    ----------
    text:
        The input word list, as it would appear after a command name on a
        shell command line.  The input may contain single quotes, double
        quotes, and backslash escapes.  It must not contain unquoted shell
        metacharacters that would change the grammar (``;``, ``|``, ``&``,
        ``(``, ``)``, ``<``, ``>``, ``{``, ``}``); those are treated as
        ordinary characters here because this function is not a parser for
        the full command language.
    ifs:
        The value of ``IFS``.  The default is space, tab, and newline.  The
        default is used when the argument is omitted; passing an explicit
        empty string disables field splitting entirely, matching the shell
        behaviour of ``IFS=``.

    Returns
    -------
    list of str
        The fields, with all quoting removed.  An input that produces no
        fields (for example, the empty string) yields an empty list.

    Raises
    ------
    ExpansionError
        If a single quote or double quote is not terminated before the end
        of input.

    Notes
    -----
    Field splitting is performed on the *unquoted* characters of the input.
    Quoted characters are protected from splitting but are still subject to
    quote removal.  A backslash outside quotes removes the special meaning of
    the following character; a backslash inside double quotes removes the
    special meaning of ``$``, ``\```, ``"``, ``\\``, and newline only, and is
    otherwise retained literally, as required by POSIX.
    """
    if not isinstance(text, str):
        raise TypeError("text must be a str")
    if not isinstance(ifs, str):
        raise TypeError("ifs must be a str")

    fields: List[str] = []
    current: List[str] = []
    # ``have_field`` tracks whether the current field has been started by an
    # unquoted character or a quoted empty string.  POSIX distinguishes a
    # field that exists but is empty (from ``''``) from the absence of a
    # field (from a leading IFS delimiter).  Keeping this flag is the whole
    # reason the lexer is stateful rather than a chain of str.replace calls.
    have_field = False
    i = 0
    n = len(text)

    def flush() -> None:
        nonlocal current, have_field
        if have_field:
            fields.append("".join(current))
            current = []
            have_field = False

    while i < n:
        ch = text[i]

        if ch == "'":
            # Single quotes: everything up to the next single quote is literal.
            j = text.find("'", i + 1)
            if j == -1:
                raise ExpansionError("unterminated single quote")
            current.append(text[i + 1 : j])
            have_field = True
            i = j + 1
            continue

        if ch == '"':
            # Double quotes: backslash is special only before $, `, ", \, and
            # newline; all other characters are literal.  Newline inside
            # double quotes is literal too (line continuation is handled by
            # the backslash branch below).
            j = i + 1
            while j < n:
                cj = text[j]
                if cj == '"':
                    break
                if cj == "\\" and j + 1 < n and text[j + 1] in '$`"\\':
                    current.append(text[j + 1])
                    j += 2
                    continue
                if cj == "\\" and j + 1 < n and text[j + 1] == "\n":
                    # Line continuation inside double quotes: the backslash
                    # and newline are both removed.
                    j += 2
                    continue
                current.append(cj)
                j += 1
            if j >= n:
                raise ExpansionError("unterminated double quote")
            have_field = True
            i = j + 1
            continue

        if ch == "\\":
            if i + 1 >= n:
                # A trailing backslash at end of input has no character to
                # escape.  POSIX leaves this unspecified for interactive
                # shells; for a pure lexer the least surprising choice is to
                # treat it as an error, because silently dropping it would
                # hide a real quoting mistake in a script.
                raise ExpansionError("trailing backslash")
            nxt = text[i + 1]
            if nxt == "\n":
                # Line continuation outside quotes: both characters vanish.
                i += 2
                continue
            current.append(nxt)
            have_field = True
            i += 2
            continue

        if _is_ifs_whitespace(ch, ifs):
            flush()
            i += 1
            continue

        if _is_ifs_nonwhitespace(ch, ifs):
            # A non-whitespace IFS character terminates the current field and
            # produces an empty field if no field was in progress.
            if have_field:
                flush()
            else:
                fields.append("")
            i += 1
            continue

        current.append(ch)
        have_field = True
        i += 1

    flush()
    return fields
