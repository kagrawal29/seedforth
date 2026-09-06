package flags

import (
	"errors"
	"time"
)

// Parsed represents the parsed CLI flags and subcommand arguments.
type Parsed struct {
	Target     string        // dev, staging, or prod; empty means caller fills from env or config
	JSON       bool          // output as JSON
	Timeout    time.Duration // command timeout; default 30s
	Quiet      bool          // suppress output
	Subcommand string        // the actual command to run (status, shell, health, etc.)
	Args       []string      // additional arguments for the subcommand
}

// ValidTargets is the set of valid target environments.
var ValidTargets = map[string]bool{
	"dev":     true,
	"staging": true,
	"prod":    true,
}

// Parse takes raw argv and returns a *Parsed or an error.
// Flags can appear before or after the subcommand.
// If the same flag is specified multiple times, last one wins.
func Parse(argv []string) (*Parsed, error) {
	p := &Parsed{
		Target:  "",
		JSON:    false,
		Timeout: 30 * time.Second,
		Quiet:   false,
	}

	// Find the subcommand: first non-flag argument that is NOT a flag value.
	// We need to skip both flags (--name) and their values.
	var subcommandIdx int = -1
	for i := 0; i < len(argv); i++ {
		arg := argv[i]

		// If it's a flag name, skip it and its value
		if isFlagName(arg) {
			// Check if this flag takes a value
			if arg == "--json" || arg == "--quiet" {
				// No value, just continue
				continue
			} else if arg == "--target" || arg == "--timeout" {
				// Skip the next argument (the value)
				i++
				continue
			}
		}

		// We found a non-flag argument that wasn't a flag value
		subcommandIdx = i
		p.Subcommand = arg
		break
	}

	// Process all arguments as flags or args
	var allArgs []string
	for i := 0; i < len(argv); i++ {
		arg := argv[i]

		// Skip the subcommand itself
		if i == subcommandIdx {
			continue
		}

		// Parse flags
		if isFlagName(arg) {
			switch arg {
			case "--json":
				p.JSON = true
			case "--quiet":
				p.Quiet = true
			case "--target":
				if i+1 >= len(argv) {
					return nil, errors.New("flag --target requires a value")
				}
				i++
				target := argv[i]
				if !ValidTargets[target] {
					return nil, errors.New("invalid target: " + target + "; valid targets are: dev, staging, prod")
				}
				p.Target = target
			case "--timeout":
				if i+1 >= len(argv) {
					return nil, errors.New("flag --timeout requires a value")
				}
				i++
				dur, err := time.ParseDuration(argv[i])
				if err != nil {
					return nil, errors.New("invalid timeout duration: " + err.Error())
				}
				p.Timeout = dur
			default:
				// Unknown flag: only an error if it appears before the subcommand
				if i < subcommandIdx {
					return nil, errors.New("unknown flag: " + arg)
				}
				// After subcommand, unknown flag-like things become Args
				allArgs = append(allArgs, arg)
			}
		} else {
			// Non-flag arguments (after subcommand) become Args
			if i > subcommandIdx {
				allArgs = append(allArgs, arg)
			}
		}
	}

	p.Args = allArgs
	return p, nil
}

// isFlagName returns true if arg looks like a flag (starts with --)
func isFlagName(arg string) bool {
	return len(arg) > 2 && arg[0] == '-' && arg[1] == '-'
}
