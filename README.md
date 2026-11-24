# posix_shell_word_expander

Performs POSIX-compliant word splitting and quote removal on shell-like input
strings without executing commands.

```python
from posix_shell_word_expander import expand, ExpansionError

fields = expand("git commit -m 'fix: handle empty input' --amend")
assert fields == ["git", "commit", "-m", "fix: handle empty input", "--amend"]

# Custom IFS works like the shell's:
assert expand("a:b:c", ifs=":") == ["a", "b", "c"]

# Unterminated quotes are reported rather than silently accepted:
try:
    expand("'oops")
except ExpansionError as exc:
    print(exc)  # unterminated single quote
```

## Why this exists

Parsing a command line that a user typed or that a build script produced is a
recurring problem: you want the fields the shell would have produced, but you
do not want to run a shell.  ``shlex`` in the standard library is close, but
its default ``posix=True`` mode also treats comments and has its own
non-POSIX quirks around empty quoted strings and non-whitespace ``IFS``
characters.  This library implements the POSIX word-splitting rules directly
and stops there: no parameter expansion, no command substitution, no globbing.

The trade-off is deliberate.  Because the expander never invokes a shell and
never consults the environment, it is safe to call on untrusted input and its
behaviour is fully specified by the input string alone.  Callers who need
``$VAR`` or ``*`` expansion should use a real shell; callers who need to
re-dispatch a parsed command to ``execve`` want exactly this subset.

## The awkward edge

A backslash at the very end of the input has no character to escape.  POSIX
leaves this unspecified for interactive shells, so this library raises
``ExpansionError`` instead of silently dropping the backslash.  If you are
feeding it a partial line from a line editor, strip the trailing backslash
before calling ``expand``.

## Performance

The window keeps a bounded buffer, so `push` is constant time and memory does not
grow with the length of the stream. `peak` and `trough` are linear in the window
size, which is the trade that keeps `push` cheap.

## Design notes

The window stores values eagerly rather than keeping running aggregates. Running
sums drift with floating point over long streams, and recomputing from a small
buffer is cheap enough that the drift is not worth the speed.

