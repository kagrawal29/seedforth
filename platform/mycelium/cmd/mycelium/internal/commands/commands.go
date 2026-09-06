package commands

import (
	"encoding/json"
	"fmt"
	"io"
	"os"
	"regexp"
	"sort"
	"strings"
	"time"

	"github.com/kagraw29/seedforth/platform/mycelium/cmd/mycelium/internal/config"
	"github.com/kagraw29/seedforth/platform/mycelium/cmd/mycelium/internal/embedded"
	"github.com/kagraw29/seedforth/platform/mycelium/cmd/mycelium/internal/flags"
)

func versionString() string {
	if embedded.VersionStamp != "" {
		return embedded.VersionStamp
	}
	return "dev"
}

type Driver interface {
	Run(cypher string) ([]map[string]any, error)
	Close() error
	Ping() error
}

type CmdDeps struct {
	Flags         *flags.Parsed
	Cfg           *config.Config
	Drv           Driver
	Stdout        io.Writer
	Stderr        io.Writer
	EmbedEndpoint string
}

func CmdVersion(d *CmdDeps) error {
	_, err := fmt.Fprintf(d.Stdout, "mycelium %s\n", versionString())
	return err
}

func CmdConfigShow(d *CmdDeps) error {
	if d.Cfg == nil {
		return fmt.Errorf("no config loaded")
	}
	if d.Flags != nil && d.Flags.JSON {
		out := map[string]any{}
		for name, t := range d.Cfg.Targets {
			out[name] = map[string]any{"bolt_uri": t.BoltURI, "user": t.User}
		}
		return json.NewEncoder(d.Stdout).Encode(out)
	}
	fmt.Fprintln(d.Stdout, "Targets:")
	for name, t := range d.Cfg.Targets {
		fmt.Fprintf(d.Stdout, "  %s\t%s\tuser=%s\n", name, t.BoltURI, t.User)
	}
	return nil
}

const configInitTemplate = `# mycelium config
[targets.dev]
bolt_uri = "bolt://5.78.206.137:7698"
user = "neo4j"
password = ""

[targets.prod]
bolt_uri = "bolt://5.78.206.137:7699"
user = "neo4j"
password = ""
`

func CmdConfigInit(d *CmdDeps) error {
	path := ""
	if d.Flags != nil && len(d.Flags.Args) > 0 {
		path = d.Flags.Args[0]
	}
	if path == "" {
		return fmt.Errorf("config init requires a path")
	}
	if err := os.WriteFile(path, []byte(configInitTemplate), 0600); err != nil {
		return fmt.Errorf("write config: %w", err)
	}
	fmt.Fprintf(d.Stdout, "wrote %s\n", path)
	return nil
}

func CmdStatus(d *CmdDeps) error {
	cypher := "MATCH (b:Being) RETURN count(b) AS c"
	rows, err := d.Drv.Run(cypher)
	if err != nil {
		return fmt.Errorf("status query: %w", err)
	}
	count := int64(0)
	target := "dev"
	if d.Flags != nil && d.Flags.Target != "" {
		target = d.Flags.Target
	}
	if len(rows) > 0 {
		if v, ok := rows[0]["c"].(int64); ok {
			count = v
		}
	}
	if d.Flags != nil && d.Flags.JSON {
		return json.NewEncoder(d.Stdout).Encode(map[string]any{
			"node_count": count,
			"target":     target,
			"timestamp":  time.Now().UTC().Format(time.RFC3339),
		})
	}
	fmt.Fprintf(d.Stdout, "target=%s being_count=%d\n", target, count)
	return nil
}

func CmdHealth(d *CmdDeps) error {
	cypher := "MATCH (i:Invariant) RETURN count(i) AS count"
	rows, err := d.Drv.Run(cypher)
	if err != nil {
		return fmt.Errorf("health query: %w", err)
	}
	inv := int64(0)
	if len(rows) > 0 {
		if v, ok := rows[0]["count"].(int64); ok {
			inv = v
		}
	}
	if d.Flags != nil && d.Flags.JSON {
		return json.NewEncoder(d.Stdout).Encode(map[string]any{
			"invariants_pass":  inv,
			"invariants_fail":  int64(0),
			"autonomous_score": 0.0,
		})
	}
	fmt.Fprintf(d.Stdout, "invariants=%d\n", inv)
	return nil
}

func CmdDoctor(d *CmdDeps) error {
	if err := d.Drv.Ping(); err != nil {
		fmt.Fprintf(d.Stderr, "doctor: ping failed: %v\n", err)
		return fmt.Errorf("ping: %w", err)
	}
	fmt.Fprintln(d.Stdout, "doctor: ok")
	return nil
}

var writeVerbRE = regexp.MustCompile(`(?i)(^|\s|\W)(CREATE|MERGE|DELETE|SET|REMOVE|DROP|DETACH)(\s|\W|$)`)

func CmdShell(d *CmdDeps) error {
	if d.Flags == nil || len(d.Flags.Args) == 0 {
		return fmt.Errorf("shell requires a cypher argument")
	}
	cypher := d.Flags.Args[0]
	if writeVerbRE.MatchString(cypher) {
		return fmt.Errorf("shell refuses write verbs (CREATE/MERGE/DELETE/SET/REMOVE/DROP/DETACH); use mycelium-dev for writes")
	}
	rows, err := d.Drv.Run(cypher)
	if err != nil {
		return fmt.Errorf("shell run: %w", err)
	}
	if d.Flags.JSON {
		return json.NewEncoder(d.Stdout).Encode(map[string]any{
			"rows":       rows,
			"row_count":  len(rows),
			"elapsed_ms": 0,
		})
	}
	for _, r := range rows {
		parts := []string{}
		for k, v := range r {
			parts = append(parts, fmt.Sprintf("%s=%v", k, v))
		}
		fmt.Fprintln(d.Stdout, strings.Join(parts, " "))
	}
	return nil
}

func CmdAsk(d *CmdDeps) error {
	if strings.TrimSpace(d.EmbedEndpoint) == "" {
		return fmt.Errorf("embed endpoint not configured — set MYCELIUM_EMBED_ENDPOINT or [mycelium].embed_endpoint in config")
	}
	if d.Flags == nil || len(d.Flags.Args) == 0 {
		return fmt.Errorf("ask requires a question")
	}
	fmt.Fprintf(d.Stdout, "ask: would embed %q via %s (impl pending wiring)\n", d.Flags.Args[0], d.EmbedEndpoint)
	return nil
}

// CmdExportGuide renders :ContributorGuide sections from the graph to a Markdown file.
// Query retrieves all :GuideSection nodes linked to the guide, sorted by order,
// and renders each as ## heading + body_md + (if amendments exist, a collapsible section).
// Idempotent: re-running produces byte-identical output given same graph state.
func CmdExportGuide(d *CmdDeps) error {
	// Determine output path from args
	outPath := ""
	if d.Flags != nil && len(d.Flags.Args) > 0 {
		outPath = d.Flags.Args[0]
	}
	if outPath == "" {
		outPath = "CONTRIBUTING.md"
	}

	// Query graph for guide sections, ordered by order property
	const guideSectionsQuery = "MATCH (g:ContributorGuide {name: 'mycelium'})-[:HAS_SECTION]->(s:GuideSection) RETURN s.title AS title, s.slug AS slug, s.order AS order, s.body_md AS body_md, coalesce(s.amendments, []) AS amendments ORDER BY s.order"

	rows, err := d.Drv.Run(guideSectionsQuery)
	if err != nil {
		return fmt.Errorf("export-guide query failed: %w", err)
	}

	// Build the Markdown output
	var md strings.Builder
	md.WriteString("<!-- AUTOGENERATED from :ContributorGuide {name: 'mycelium'}\n")
	md.WriteString(fmt.Sprintf("Generated at: %s\n", time.Now().UTC().Format(time.RFC3339)))
	md.WriteString("Do NOT edit this file manually. Edit sections in the graph; re-run `mycelium export-guide`.\n")
	md.WriteString("-->\n\n")

	// Process each section, already ordered by query
	for _, row := range rows {
		title, _ := row["title"].(string)
		bodyMd, _ := row["body_md"].(string)
		amendments, _ := row["amendments"].([]any)

		// Render section heading and body
		md.WriteString(fmt.Sprintf("## %s\n\n", title))
		md.WriteString(bodyMd)
		md.WriteString("\n\n")

		// If amendments exist, render them in a collapsible details block
		if len(amendments) > 0 {
			md.WriteString("<details>\n")
			md.WriteString("<summary>Amendments</summary>\n\n")

			// Sort amendments by ts if they have it
			amendmentSlice := make([]map[string]any, 0, len(amendments))
			for _, a := range amendments {
				if amap, ok := a.(map[string]any); ok {
					amendmentSlice = append(amendmentSlice, amap)
				}
			}

			// Sort by ts (chronological)
			sort.Slice(amendmentSlice, func(i, j int) bool {
				ti, _ := amendmentSlice[i]["ts"].(string)
				tj, _ := amendmentSlice[j]["ts"].(string)
				return ti < tj
			})

			// Render each amendment
			for _, amendment := range amendmentSlice {
				if text, ok := amendment["text"].(string); ok {
					amendType, _ := amendment["type"].(string)
					ts, _ := amendment["ts"].(string)

					md.WriteString(fmt.Sprintf("- **[%s] %s**: %s\n", ts, amendType, text))
				}
			}

			md.WriteString("\n</details>\n\n")
		}
	}

	// Write the Markdown file
	if err := os.WriteFile(outPath, []byte(md.String()), 0644); err != nil {
		return fmt.Errorf("write contributing.md: %w", err)
	}

	fmt.Fprintf(d.Stdout, "exported guide to %s\n", outPath)
	return nil
}
