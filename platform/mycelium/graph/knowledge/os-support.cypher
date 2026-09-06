// @node_id: knowledge-os-support
// @label: Operating System Support Matrix
// @kind: knowledge
// @description: Complete catalog of OS support status, requirements, and alternative paths for mycelium onboarding

// Atom 1: macOS 10.15+ (Supported)
MERGE (o:SystemRequirement {node_id: 'os-macos'})
SET o.label = 'macOS 10.15+',
    o.os_family = 'macos',
    o.support_status = 'supported',
    o.package_manager = 'brew',
    o.required_tools = 'brew, bash, git, curl, python3, java21',
    o.alternative_paths = '',
    o.known_caveats = 'Homebrew required; auto-installs during install-deps.sh if missing. After installation, open a new terminal to refresh PATH for neo4j and cypher-shell commands.',
    o.disk_space_gb = 5,
    o.ram_gb = 8,
    o.tested = true,
    o.updated_at = datetime()
RETURN o.node_id AS result;

// Atom 2: Ubuntu 20.04+ (Supported)
MERGE (o:SystemRequirement {node_id: 'os-ubuntu'})
SET o.label = 'Ubuntu 20.04+',
    o.os_family = 'ubuntu',
    o.support_status = 'supported',
    o.package_manager = 'apt',
    o.required_tools = 'apt, bash, git, curl, python3, openjdk-21-jre',
    o.alternative_paths = '',
    o.known_caveats = 'Most common production baseline. Ubuntu 20.04 ships with Python 3.8 which is too old for some modern libraries (e.g., tomllib). If you see ModuleNotFoundError: No module named tomllib, upgrade to Python 3.11. Requires sudo access for apt and systemd services.',
    o.disk_space_gb = 5,
    o.ram_gb = 8,
    o.tested = true,
    o.updated_at = datetime()
RETURN o.node_id AS result;

// Atom 3: Debian 11+ (Supported)
MERGE (o:SystemRequirement {node_id: 'os-debian'})
SET o.label = 'Debian 11+',
    o.os_family = 'debian',
    o.support_status = 'supported',
    o.package_manager = 'apt',
    o.required_tools = 'apt, bash, git, curl, python3, openjdk-21-jre',
    o.alternative_paths = '',
    o.known_caveats = 'Same toolchain as Ubuntu; uses apt package manager. Likely compatible but not yet formally tested. Requires sudo access for apt and systemd services.',
    o.disk_space_gb = 5,
    o.ram_gb = 8,
    o.tested = false,
    o.updated_at = datetime()
RETURN o.node_id AS result;

// Atom 4: Fedora 38+ (Unsupported, Manual Path)
MERGE (o:SystemRequirement {node_id: 'os-fedora'})
SET o.label = 'Fedora 38+',
    o.os_family = 'fedora',
    o.support_status = 'unsupported',
    o.package_manager = 'dnf',
    o.required_tools = 'dnf, bash, git, curl, python3, java21',
    o.alternative_paths = 'Use WSL2 with Ubuntu 20.04+ or manually install Neo4j 2026.03.1, APOC 2026.3.1, Qdrant, Ollama, and cypher-shell following the manual installation guide in docs/os-support.md. dnf package manager not yet integrated into install-deps.sh.',
    o.known_caveats = 'Untested; dnf-based installation requires manual setup. To add Fedora support, document what you install (neo4j --version, cypher-shell --version, qdrant --version, ollama --version) and open a GitHub issue titled "Add support for Fedora [version]".',
    o.disk_space_gb = 5,
    o.ram_gb = 8,
    o.tested = false,
    o.updated_at = datetime()
RETURN o.node_id AS result;

// Atom 5: Arch Linux (Unsupported, Manual Path)
MERGE (o:SystemRequirement {node_id: 'os-arch'})
SET o.label = 'Arch Linux',
    o.os_family = 'arch',
    o.support_status = 'unsupported',
    o.package_manager = 'pacman',
    o.required_tools = 'pacman, bash, git, curl, python3, java21',
    o.alternative_paths = 'Use WSL2 with Ubuntu 20.04+ or manually install Neo4j 2026.03.1, APOC 2026.3.1, Qdrant, Ollama, and cypher-shell following the manual installation guide. pacman package manager not yet integrated into install-deps.sh.',
    o.known_caveats = 'Untested; pacman-based installation requires manual setup. Arch users should document their installation process and contribute back via GitHub issue.',
    o.disk_space_gb = 5,
    o.ram_gb = 8,
    o.tested = false,
    o.updated_at = datetime()
RETURN o.node_id AS result;

// Atom 6: Alpine Linux (Unsupported, Manual Path)
MERGE (o:SystemRequirement {node_id: 'os-alpine'})
SET o.label = 'Alpine Linux',
    o.os_family = 'alpine',
    o.support_status = 'unsupported',
    o.package_manager = 'apk',
    o.required_tools = 'apk, bash, git, curl, python3, java21',
    o.alternative_paths = 'Use WSL2 with Ubuntu 20.04+ or Docker container with Ubuntu 22.04 base image. Manual installation possible but Alpine uses musl libc which has significant compatibility differences from glibc.',
    o.known_caveats = 'Unsupported; musl libc causes compatibility issues with some binary tools. Not recommended for Mycelium team onboarding. Use Alpine only for Docker-based isolated environments.',
    o.disk_space_gb = 5,
    o.ram_gb = 8,
    o.tested = false,
    o.updated_at = datetime()
RETURN o.node_id AS result;

// Atom 7: Windows (native) (Unsupported, WSL2 Alternative)
MERGE (o:SystemRequirement {node_id: 'os-windows-native'})
SET o.label = 'Windows (native)',
    o.os_family = 'windows-native',
    o.support_status = 'unsupported',
    o.package_manager = 'none',
    o.required_tools = 'WSL2 with Ubuntu guest',
    o.alternative_paths = 'Use WSL2 with Ubuntu 20.04+ (Windows 11: wsl --install -d Ubuntu-20.04; Windows 10: follow official WSL2 setup guide). Once WSL2 is running, clone maverick and run install-deps.sh inside the Ubuntu environment.',
    o.known_caveats = 'Windows native is not supported. WSL2 with Ubuntu is fully supported and tested as the recommended path for Windows users.',
    o.disk_space_gb = 5,
    o.ram_gb = 8,
    o.tested = false,
    o.updated_at = datetime()
RETURN o.node_id AS result;

// Atom 8: WSL2 with Ubuntu (Supported)
MERGE (o:SystemRequirement {node_id: 'os-wsl2'})
SET o.label = 'WSL2 (Ubuntu guest)',
    o.os_family = 'wsl2',
    o.support_status = 'supported',
    o.package_manager = 'apt',
    o.required_tools = 'apt, bash, git, curl, python3, openjdk-21-jre',
    o.alternative_paths = '',
    o.known_caveats = 'Behaves like Ubuntu; full support. WSL2 is the recommended path for Windows users. Install WSL2 with Ubuntu 20.04+, then run the standard Ubuntu setup steps (doctor.sh, setup-team.sh, install-deps.sh).',
    o.disk_space_gb = 5,
    o.ram_gb = 8,
    o.tested = true,
    o.updated_at = datetime()
RETURN o.node_id AS result;

// Atom 9: Raspberry Pi OS (Untested, Manual Path)
MERGE (o:SystemRequirement {node_id: 'os-raspberry-pi'})
SET o.label = 'Raspberry Pi OS',
    o.os_family = 'raspberry-pi',
    o.support_status = 'untested',
    o.package_manager = 'apt',
    o.required_tools = 'apt (ARM-based), bash, git, curl, python3, java21 (ARM)',
    o.alternative_paths = 'Manual installation required. Not recommended for production use. Requires ARM binaries for all tools. Follow manual installation guide but note RAM constraints: 4GB Pi may struggle with Neo4j + Qdrant + Ollama together.',
    o.known_caveats = 'ARM-based; requires ARM binaries for some tools. Neo4j requires manual installation (Homebrew unavailable). Partial support only. Low RAM (4GB) may cause performance issues. Experimentation OK, production use not recommended.',
    o.disk_space_gb = 5,
    o.ram_gb = 8,
    o.tested = false,
    o.updated_at = datetime()
RETURN o.node_id AS result;

// Atom 10: macOS Apple Silicon (M1/M2/M3) (Supported)
MERGE (o:SystemRequirement {node_id: 'os-macos-apple-silicon'})
SET o.label = 'macOS Apple Silicon (M1/M2/M3)',
    o.os_family = 'macos-apple-silicon',
    o.support_status = 'supported',
    o.package_manager = 'brew',
    o.required_tools = 'brew, bash, git, curl, python3, java21 (ARM native)',
    o.alternative_paths = '',
    o.known_caveats = 'Everything works natively with ARM64 support via Homebrew. Ollama, Neo4j, and Qdrant all have native ARM64 binaries. If you hit an architecture mismatch error, try: brew uninstall <tool> && brew install <tool> (Homebrew picks the right architecture automatically).',
    o.disk_space_gb = 5,
    o.ram_gb = 8,
    o.tested = true,
    o.updated_at = datetime()
RETURN o.node_id AS result;

// Link all SystemRequirement nodes to the onboarding entry point
MATCH (o:SystemRequirement)
OPTIONAL MATCH (s:OnboardingStep {node_id: 'step-prereqs'})
WHERE s IS NOT NULL
MERGE (s)-[:VALIDATES]->(o)
RETURN COUNT(o) AS os_nodes_linked;

// Alternative: if OnboardingStep doesn't exist, create a placeholder relationship
MATCH (o:SystemRequirement)
WHERE NOT EXISTS {
  (s:OnboardingStep)-[:VALIDATES]->(o)
}
WITH o
OPTIONAL MATCH (concept:Concept {node_id: 'concept-onboarding'})
WHERE concept IS NOT NULL
MERGE (concept)-[:REQUIRES]->(o)
RETURN COUNT(o) AS os_fallback_links;

// Create tag edges for semantic discovery
MATCH (o:SystemRequirement {support_status: 'supported'})
SET o:SupportedOS
RETURN COUNT(o) AS supported_os_count;

MATCH (o:SystemRequirement {support_status: 'unsupported'})
SET o:UnsupportedOS
RETURN COUNT(o) AS unsupported_os_count;

MATCH (o:SystemRequirement {support_status: 'untested'})
SET o:UntestedOS
RETURN COUNT(o) AS untested_os_count;

// Return summary of ingested OS matrix
MATCH (o:SystemRequirement)
RETURN
    COUNT(o) AS total_os_entries,
    COUNT(CASE WHEN o.support_status = 'supported' THEN 1 END) AS supported,
    COUNT(CASE WHEN o.support_status = 'untested' THEN 1 END) AS untested,
    COUNT(CASE WHEN o.support_status = 'unsupported' THEN 1 END) AS unsupported,
    COLLECT(DISTINCT o.node_id) AS all_node_ids;
