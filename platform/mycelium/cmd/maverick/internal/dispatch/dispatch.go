// Package dispatch routes maverick subcommands to either native Go handlers
// or to the maverick-dev bash shim for write/orchestration verbs.
//
// The single-binary unified interface means teammates only ever type `maverick`.
// Read verbs run natively (fast, no toolchain). Write verbs shell out to
// maverick-dev so the same command line works end-to-end — the user never
// has to learn two CLIs.
package dispatch

import (
	"os"
	"os/exec"
	"sort"
)

type Kind int

const (
	KindNative Kind = iota
	KindShellOut
	KindUnknown
)

type Route struct {
	Verb           string
	Kind           Kind
	Description    string
	NeedsToolchain bool
}

var nativeRoutes = []Route{
	{"ask", KindNative, "semantic search against the graph (hosted embed endpoint)", false},
	{"config", KindNative, "show or init the maverick config file", false},
	{"doctor", KindNative, "ping the graph, surface connection errors", false},
	{"export-guide", KindNative, "render :ContributorGuide sections to CONTRIBUTING.md", false},
	{"health", KindNative, "invariant + autonomous-score summary", false},
	{"help", KindNative, "print help text", false},
	{"shell", KindNative, "run a read-only Cypher query (write verbs refused)", false},
	{"status", KindNative, "graph vitals (Being count, target, timestamp)", false},
	{"uninstall", KindNative, "remove all maverick global Claude Code changes", false},
	{"version", KindNative, "print binary version + build time", false},
}

var shellOutRoutes = []Route{
	{"bootstrap", KindShellOut, "load Protocol cypher files into graph (writer)", true},
	{"drift", KindShellOut, "report drift between local and a remote target", true},
	{"dream", KindShellOut, "run a dream round — cross-scale pattern discovery", true},
	{"dump", KindShellOut, "snapshot the graph to a .dump file", true},
	{"fork", KindShellOut, "fork maverick-dev into maverick-local with APOC export/import", true},
	{"ingest-repo", KindShellOut, "ingest a git repo history as :Commit/:Author/:File nodes", true},
	{"inject", KindShellOut, "inject a protocol or signal into the graph", true},
	{"migrate", KindShellOut, "apply a migration plan", true},
	{"restore", KindShellOut, "restore the graph from a .dump file", true},
	{"start", KindShellOut, "register the APOC heartbeat job", true},
	{"stop", KindShellOut, "cancel the APOC heartbeat job", true},
	{"swarm", KindShellOut, "parallel cypher workers — zero-LLM multi-agent", true},
	{"sync", KindShellOut, "sync a local target from prod/dev", true},
	{"target", KindShellOut, "switch or list configured targets", true},
}

var all = func() []Route {
	combined := append([]Route{}, nativeRoutes...)
	combined = append(combined, shellOutRoutes...)
	sort.Slice(combined, func(i, j int) bool { return combined[i].Verb < combined[j].Verb })
	return combined
}()

var byVerb = func() map[string]Route {
	m := make(map[string]Route, len(all))
	for _, r := range all {
		m[r.Verb] = r
	}
	return m
}()

// Lookup returns the Route for a verb. Unknown verbs return Kind=KindUnknown.
func Lookup(verb string) Route {
	if r, ok := byVerb[verb]; ok {
		return r
	}
	return Route{Verb: verb, Kind: KindUnknown}
}

// Registry returns all known routes, sorted by verb.
func Registry() []Route {
	out := make([]Route, len(all))
	copy(out, all)
	return out
}

// FindMaverickDev locates the maverick-dev executable.
// Precedence: MAVERICK_DEV_PATH env var, then PATH lookup.
// Falls back to MYCELIUM_DEV_PATH for backwards compat.
func FindMaverickDev() string {
	if p := os.Getenv("MAVERICK_DEV_PATH"); p != "" {
		if info, err := os.Stat(p); err == nil && !info.IsDir() {
			return p
		}
	}
	// Backwards compat: check MYCELIUM_DEV_PATH
	if p := os.Getenv("MYCELIUM_DEV_PATH"); p != "" {
		if info, err := os.Stat(p); err == nil && !info.IsDir() {
			return p
		}
	}
	if p, err := exec.LookPath("maverick-dev"); err == nil {
		return p
	}
	// Backwards compat: try mycelium-dev if maverick-dev not found
	if p, err := exec.LookPath("mycelium-dev"); err == nil {
		return p
	}
	return ""
}
