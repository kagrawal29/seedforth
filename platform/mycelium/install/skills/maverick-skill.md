# Maverick CLI Skill

**Name:** maverick
**Description:** Direct pass-through to maverick CLI — invoke the binary with any arguments unchanged
**Command invocation:** `/maverick` (or `/maverick alone` for help)

## How it works

This skill forwards all tokens after `/maverick` verbatim to the `maverick` binary:

```
/maverick shell "MATCH (b:Being) RETURN count(b)"
  → runs: maverick shell "MATCH (b:Being) RETURN count(b)"

/maverick ask "how do I contribute"
  → runs: maverick ask "how do I contribute"

/maverick alone
  → runs: maverick --help (prints help text)

/maverick
  → runs: maverick --help (prints help text)
```

## Parameters

No parameters — this skill is a pure dispatcher. Arguments are passed to `maverick` as-is.

## Output

Returns the stdout/stderr output of the `maverick` CLI command executed.

## Error handling

- If `maverick` binary is not on PATH, the error message will indicate so
- All `maverick` CLI errors propagate unchanged
- Non-zero exit codes are preserved
