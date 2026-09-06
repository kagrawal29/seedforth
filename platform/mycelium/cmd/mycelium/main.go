// mycelium — unified team CLI.
//
// Reads (status/shell/ask/health/doctor/version/config) run natively.
// Writes (bootstrap/start/swarm/dream/ingest-repo/...) dispatch to mycelium-dev.
// Teammates see one binary, one help output, one consistent command line.
package main

import (
	"fmt"
	"io"
	"os"
	"os/exec"
	"strconv"

	"github.com/kagraw29/seedforth/platform/mycelium/cmd/mycelium/internal/bolt"
	"github.com/kagraw29/seedforth/platform/mycelium/cmd/mycelium/internal/commands"
	"github.com/kagraw29/seedforth/platform/mycelium/cmd/mycelium/internal/dispatch"
	"github.com/kagraw29/seedforth/platform/mycelium/cmd/mycelium/internal/embedded"
	"github.com/kagraw29/seedforth/platform/mycelium/cmd/mycelium/internal/flags"
	"github.com/kagraw29/seedforth/platform/mycelium/cmd/mycelium/internal/help"
)

// shelloutDepthEnv tracks nested shellouts so we refuse recursion when the
// resolved mycelium-dev shim re-invokes this same binary (issue #40: the old
// pulse deployment ships a /usr/local/bin/mycelium-dev wrapper whose `./mycelium`
// is the Go binary itself, producing a fork bomb that exhausts TasksMax).
const shelloutDepthEnv = "MYCELIUM_SHELLOUT_DEPTH"

// maxShelloutDepth is the highest depth we allow. One legitimate shellout =
// depth 1 inside the child. Anything ≥ shelloutRecursionThreshold on entry
// to runShellOut means the dev shim looped back to us.
const shelloutRecursionThreshold = 1

func versionStamp() string {
	if embedded.VersionStamp != "" {
		return embedded.VersionStamp
	}
	return "dev"
}

func main() {
	os.Exit(run(os.Args[1:], os.Stdout, os.Stderr))
}

func run(argv []string, stdout, stderr io.Writer) int {
	if len(argv) == 0 {
		fmt.Fprint(stdout, help.Text())
		return 0
	}
	for _, a := range argv {
		if a == "-h" || a == "--help" {
			fmt.Fprint(stdout, help.Text())
			return 0
		}
	}

	parsed, err := flags.Parse(argv)
	if err != nil {
		fmt.Fprintf(stderr, "mycelium: %v\n", err)
		return 2
	}
	verb := parsed.Subcommand
	if verb == "" {
		fmt.Fprint(stdout, help.Text())
		return 0
	}

	route := dispatch.Lookup(verb)
	switch route.Kind {
	case dispatch.KindNative:
		return runNative(verb, parsed, stdout, stderr)
	case dispatch.KindShellOut:
		return runShellOut(verb, argv, stdout, stderr)
	case dispatch.KindUnknown:
		fmt.Fprintf(stderr, "mycelium: unknown command %q\n\n", verb)
		fmt.Fprint(stderr, help.Text())
		return 2
	}
	return 0
}

func runNative(verb string, parsed *flags.Parsed, stdout, stderr io.Writer) int {
	switch verb {
	case "version":
		fmt.Fprintf(stdout, "mycelium %s\n", versionStamp())
		return 0
	case "help":
		fmt.Fprint(stdout, help.Text())
		return 0
	}

	deps := &commands.CmdDeps{
		Flags:         parsed,
		Stdout:        stdout,
		Stderr:        stderr,
		EmbedEndpoint: getEmbedEndpoint(),
	}

	// Config and uninstall commands don't need a driver.
	switch verb {
	case "config":
		sub := ""
		if len(parsed.Args) > 0 {
			sub = parsed.Args[0]
			parsed.Args = parsed.Args[1:]
		}
		switch sub {
		case "init":
			return surfaceErr(stderr, commands.CmdConfigInit(deps))
		default:
			return surfaceErr(stderr, commands.CmdConfigShow(deps))
		}
	case "uninstall":
		return surfaceErr(stderr, commands.CmdUninstall(deps))
	}

	// Everything else needs a live graph connection from embedded creds.
	creds, err := embedded.Load()
	if err != nil {
		fmt.Fprintf(stderr, "mycelium: %v\n", err)
		return 1
	}
	target := parsed.Target
	if target == "" {
		target = "dev"
	}
	uri, user, pass := resolveCreds(creds, target)
	if uri == "" {
		fmt.Fprintf(stderr, "mycelium: target %q has no embedded credentials\n", target)
		return 1
	}
	drv, err := bolt.NewBoltDriver(uri, user, pass)
	if err != nil {
		fmt.Fprintf(stderr, "mycelium: connect: %v\n", err)
		return 1
	}
	defer drv.Close()
	deps.Drv = drv

	switch verb {
	case "status":
		return surfaceErr(stderr, commands.CmdStatus(deps))
	case "health":
		return surfaceErr(stderr, commands.CmdHealth(deps))
	case "doctor":
		return surfaceErr(stderr, commands.CmdDoctor(deps))
	case "shell":
		return surfaceErr(stderr, commands.CmdShell(deps))
	case "ask":
		return surfaceErr(stderr, commands.CmdAsk(deps))
	case "export-guide":
		return surfaceErr(stderr, commands.CmdExportGuide(deps))
	default:
		fmt.Fprintf(stderr, "mycelium: native verb %q has no handler\n", verb)
		return 2
	}
}

// getEmbedEndpoint returns the canonical endpoint or the legacy variable.
func getEmbedEndpoint() string {
	if ep := os.Getenv("MYCELIUM_EMBED_ENDPOINT"); ep != "" {
		return ep
	}
	return os.Getenv("MAVERICK_EMBED_ENDPOINT")
}

func resolveCreds(c *embedded.EmbeddedCreds, target string) (uri, user, pass string) {
	switch target {
	case "dev":
		return c.Dev.BoltURI, c.Dev.User, c.Dev.Password
	case "staging":
		return c.Staging.BoltURI, c.Staging.User, c.Staging.Password
	case "prod":
		return c.Prod.BoltURI, c.Prod.User, c.Prod.Password
	}
	return "", "", ""
}

func surfaceErr(stderr io.Writer, err error) int {
	if err != nil {
		fmt.Fprintf(stderr, "mycelium: %v\n", err)
		return 1
	}
	return 0
}

func runShellOut(verb string, args []string, stdout, stderr io.Writer) int {
	depth, _ := strconv.Atoi(os.Getenv(shelloutDepthEnv))
	if depth >= shelloutRecursionThreshold {
		dev := dispatch.FindMyceliumDev()
		fmt.Fprintf(stderr,
			"mycelium: refusing to shell out — recursion detected (depth=%d).\n"+
				"The resolved mycelium-dev shim at %q re-invokes this same binary,\n"+
				"which would fork-bomb the host. See issue #40.\n"+
				"Fix: point the shim's ./mycelium (or ./mycelium) at the bash\n"+
				"dispatcher in the mycelium repo root, or unset MYCELIUM_DEV_PATH /\n"+
				"MYCELIUM_DEV_PATH so the binary runs the verb natively.\n",
			depth, dev)
		return 1
	}

	dev := dispatch.FindMyceliumDev()
	if dev == "" {
		fmt.Fprintf(stderr,
			"mycelium: %q requires the contributor toolchain (mycelium-dev).\n"+
				"Install: see docs/contributor-setup.md in the mycelium repo,\n"+
				"or set MYCELIUM_DEV_PATH=/path/to/mycelium-dev if you already have it.\n",
			verb)
		return 127
	}
	full := append([]string{verb}, args...)
	cmd := exec.Command(dev, full...)
	cmd.Stdout = stdout
	cmd.Stderr = stderr
	cmd.Stdin = os.Stdin
	// Inject depth+1 so a shim that loops back into this binary can detect the
	// recursion on the next entry and refuse instead of fork-bombing.
	cmd.Env = append(os.Environ(), fmt.Sprintf("%s=%d", shelloutDepthEnv, depth+1))
	if err := cmd.Run(); err != nil {
		if exitErr, ok := err.(*exec.ExitError); ok {
			return exitErr.ExitCode()
		}
		fmt.Fprintf(stderr, "mycelium: failed to invoke mycelium-dev: %v\n", err)
		return 1
	}
	return 0
}
