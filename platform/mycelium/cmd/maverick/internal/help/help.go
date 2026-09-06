// Package help emits deterministic help text for the maverick CLI.
//
// The text reflects the unified dispatcher: one binary, two kinds of verbs.
// Native verbs run in the Go binary (zero toolchain). Toolchain verbs dispatch
// to maverick-dev on the user's machine — required only for contributors.
package help

import (
	"fmt"
	"strings"

	"github.com/Qubit-Capital/maverick/cmd/maverick/internal/dispatch"
	"github.com/Qubit-Capital/maverick/cmd/maverick/internal/embedded"
)

const VersionStamp = "dev"

func Text() string {
	var b strings.Builder
	ver := embedded.VersionStamp
	if ver == "" {
		ver = "dev"
	}

	fmt.Fprintf(&b, "maverick %s — the team's living knowledge graph\n\n", ver)
	b.WriteString("USAGE\n")
	b.WriteString("  maverick [FLAGS] <command> [args...]\n\n")

	b.WriteString("FLAGS\n")
	b.WriteString("  --target <dev|staging|prod>  target environment (default: from MAVERICK_TARGET or config)\n")
	b.WriteString("  --json                        emit JSON (for scripting)\n")
	b.WriteString("  --timeout <duration>          command timeout (default: 30s)\n")
	b.WriteString("  --quiet                       suppress decor\n\n")

	b.WriteString("READ COMMANDS (native, no toolchain needed)\n")
	for _, r := range dispatch.Registry() {
		if r.Kind == dispatch.KindNative {
			fmt.Fprintf(&b, "  %-12s %s\n", r.Verb, r.Description)
		}
	}
	b.WriteString("\n")

	b.WriteString("WRITE / ORCHESTRATION COMMANDS (require maverick-dev on PATH)\n")
	for _, r := range dispatch.Registry() {
		if r.Kind == dispatch.KindShellOut {
			fmt.Fprintf(&b, "  %-12s %s\n", r.Verb, r.Description)
		}
	}
	b.WriteString("\nFor contributor setup (needed only for the write commands), see\n")
	b.WriteString("docs/contributor-setup.md in the maverick repo.\n")

	fmt.Fprintf(&b, "\nVersionStamp: %s\n", ver)
	return b.String()
}
