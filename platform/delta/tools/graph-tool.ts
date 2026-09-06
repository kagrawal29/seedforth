import { tool } from "@opencode-ai/plugin"

export default tool({
  description:
    "Query the fleet knowledge graph (read-only). Before every decision, query the graph for relevant context. Every query is traced for Hebbian learning (fire_count).",
  args: {
    cypher: tool.schema
      .string()
      .describe("Read-only Cypher query (MATCH/RETURN only)"),
  },
  async execute(args, context) {
    const { execSync } = await import("child_process")
    try {
      const result = execSync(
        `python3 /opt/delta/tools/graph-tool.py ${JSON.stringify(args.cypher)}`,
        { timeout: 30000, encoding: "utf-8" }
      )
      return result
    } catch (e) {
      return `Error: ${String(e).slice(0, 300)}`
    }
  },
})
