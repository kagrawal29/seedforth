# Mycelium CLI Installer for Windows
# Downloads and installs the mycelium binary for Windows.
# Usage: powershell -ExecutionPolicy Bypass -Command "& { iwr -useb https://github.com/Qubit-Capital/maverick/releases/latest/download/install.ps1 | iex }"

# Enable strict mode
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Use minimal execution policy for this script
if ((Get-ExecutionPolicy) -eq 'Restricted') {
    Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force
}

function Write-Success {
    param([string]$Message)
    Write-Host $Message -ForegroundColor Green
}

function Write-Warning-Custom {
    param([string]$Message)
    Write-Host $Message -ForegroundColor Yellow
}

function Write-Info {
    param([string]$Message)
    Write-Host $Message
}

function Write-Error-Custom {
    param([string]$Message)
    Write-Host "Error: $Message" -ForegroundColor Red
    exit 1
}

function Get-WindowsArchitecture {
    <#
    .SYNOPSIS
    Detects the Windows architecture (amd64 only for now).
    #>
    $arch = [System.Runtime.InteropServices.RuntimeInformation]::ProcessArchitecture.ToString().ToLower()

    switch ($arch) {
        'x64' {
            return 'amd64'
        }
        'amd64' {
            return 'amd64'
        }
        default {
            Write-Error-Custom "Unsupported Windows architecture: $arch. Only amd64 (x64) is supported."
        }
    }
}

function Add-ToUserPath {
    param([string]$BinDir)

    <#
    .SYNOPSIS
    Adds a directory to the user's PATH environment variable via registry.
    Idempotent: does nothing if the directory is already in PATH.
    #>

    # Get current user PATH
    $currentPath = [Environment]::GetEnvironmentVariable('PATH', 'User') -split ';'

    # Check if already present
    foreach ($path in $currentPath) {
        if ($path -eq $BinDir) {
            Write-Info "PATH entry already exists: $BinDir"
            return
        }
    }

    # Append new path
    $newPath = $currentPath + $BinDir
    $newPathString = $newPath -join ';'

    # Set in registry
    [Environment]::SetEnvironmentVariable('PATH', $newPathString, 'User')
    Write-Info "Added $BinDir to user PATH"

    # Also update current process PATH so it works immediately in this session
    $env:PATH = "$BinDir;$env:PATH"
}

function Install-MaverickSkill {
    <#
    .SYNOPSIS
    Installs the maverick Claude Code skill to ~/.claude/skills/maverick/
    Idempotent: running multiple times produces the same result.
    #>

    $skillDir = Join-Path $env:USERPROFILE ".claude\skills\maverick"
    New-Item -ItemType Directory -Path $skillDir -Force | Out-Null

    # The skill template is embedded here for release artifacts
    # In development, copy from install/skills/maverick-skill.md
    $skillContent = @"
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
"@

    $skillPath = Join-Path $skillDir "SKILL.md"
    Set-Content -Path $skillPath -Value $skillContent -Encoding UTF8 -Force

    Write-Info "Installed maverick skill to $skillPath"
}

function Verify-SHA256 {
    param(
        [string]$FilePath,
        [string]$ExpectedHash
    )

    <#
    .SYNOPSIS
    Verifies a file's SHA256 checksum.
    #>

    $actualHash = (Get-FileHash -Path $FilePath -Algorithm SHA256).Hash.ToLower()
    $expectedHashLower = $ExpectedHash.ToLower()

    if ($actualHash -ne $expectedHashLower) {
        Write-Error-Custom "Checksum mismatch!`nExpected: $expectedHashLower`nGot: $actualHash"
    }

    Write-Info "Checksum verified"
}

function Install-MyceliumWindows {
    Write-Info "Mycelium CLI Installer for Windows"
    Write-Info ""

    # Detect architecture
    $arch = Get-WindowsArchitecture
    Write-Info "Detected Windows architecture: $arch"

    # Construct URLs
    $baseUrl = "https://github.com/Qubit-Capital/maverick/releases/latest/download"
    $archiveFileName = "mycelium_Windows_${arch}.zip"
    $downloadUrl = "$baseUrl/$archiveFileName"
    $checksumsUrl = "$baseUrl/checksums.txt"

    Write-Info "Downloading from: $downloadUrl"

    # Create temp directory
    $tmpDir = New-Item -ItemType Directory -Path $([IO.Path]::GetTempPath()) -Name "mycelium-$([System.Guid]::NewGuid())" -Force | Select-Object -ExpandProperty FullName

    try {
        $archivePath = Join-Path $tmpDir $archiveFileName
        $checksumsPath = Join-Path $tmpDir "checksums.txt"

        # Fetch helper: try Invoke-WebRequest first; on failure (private repo 404)
        # fall back to `gh release download` since Qubit-Capital/maverick is private.
        function Fetch-Asset {
            param([string]$Url, [string]$OutPath, [string]$AssetName)
            try {
                $ProgressPreference = 'SilentlyContinue'
                Invoke-WebRequest -Uri $Url -OutFile $OutPath -ErrorAction Stop
                return
            } catch {
                # Fall through to gh fallback
            }
            $ghCmd = Get-Command gh -ErrorAction SilentlyContinue
            if (-not $ghCmd) {
                Write-Error-Custom "Direct download failed (private repo) and ``gh`` CLI is not installed.`nInstall GitHub CLI: https://cli.github.com/`nThen: gh auth login"
            }
            try { gh auth status *> $null } catch {
                Write-Error-Custom "Direct download failed (private repo) and ``gh`` is not authenticated.`nRun: gh auth login"
            }
            Write-Info "Public download failed; using gh CLI to fetch $AssetName from private repo..."
            $tag = $env:MYCELIUM_RELEASE_TAG
            $ghArgs = @('release','download')
            if ($tag) { $ghArgs += $tag }
            $ghArgs += @('--repo','Qubit-Capital/maverick','--pattern',$AssetName,'--output',$OutPath,'--clobber')
            & gh @ghArgs
            if ($LASTEXITCODE -ne 0) {
                Write-Error-Custom "gh release download failed for $AssetName"
            }
        }

        # Download archive
        Write-Info "Downloading $archiveFileName..."
        Fetch-Asset -Url $downloadUrl -OutPath $archivePath -AssetName $archiveFileName
        Write-Info "Downloaded $archiveFileName"

        # Download checksums
        Write-Info "Downloading checksums..."
        Fetch-Asset -Url $checksumsUrl -OutPath $checksumsPath -AssetName "checksums.txt"

        # Parse checksums
        Write-Info "Verifying SHA256 checksum..."
        $checksumsContent = Get-Content -Path $checksumsPath -Raw
        $lines = $checksumsContent -split "`n"

        $expectedChecksum = $null
        foreach ($line in $lines) {
            if ($line -match "^([a-f0-9]+)\s+$([regex]::Escape($archiveFileName))") {
                $expectedChecksum = $matches[1]
                break
            }
        }

        if ([string]::IsNullOrEmpty($expectedChecksum)) {
            Write-Error-Custom "Checksum not found in checksums.txt for $archiveFileName"
        }

        # Verify checksum
        Verify-SHA256 -FilePath $archivePath -ExpectedHash $expectedChecksum

        # Create install directory
        $installDir = Join-Path $env:LOCALAPPDATA "mycelium\bin"
        New-Item -ItemType Directory -Path $installDir -Force | Out-Null
        Write-Info "Install directory: $installDir"

        # Extract archive
        Write-Info "Extracting archive..."
        Expand-Archive -Path $archivePath -DestinationPath $tmpDir -Force

        # Find binary
        $binaryPath = Get-ChildItem -Path $tmpDir -Name "mycelium.exe" -File -Recurse | Select-Object -First 1
        if ([string]::IsNullOrEmpty($binaryPath)) {
            $binaryPath = Get-ChildItem -Path $tmpDir -Name "mycelium" -File -Recurse | Select-Object -First 1
        }

        if ([string]::IsNullOrEmpty($binaryPath)) {
            Write-Error-Custom "Binary 'mycelium.exe' or 'mycelium' not found in archive"
        }

        # Copy to install directory
        $fullBinaryPath = Join-Path $tmpDir $binaryPath
        Copy-Item -Path $fullBinaryPath -Destination (Join-Path $installDir "mycelium.exe") -Force
        Write-Info "Installed mycelium to $installDir\mycelium.exe"

        # Update PATH
        Add-ToUserPath -BinDir $installDir

        # Install the maverick skill for Claude Code
        Install-MaverickSkill

        # Success message
        Write-Host ""
        Write-Success "mycelium installed successfully!"
        Write-Host ""
        Write-Info "To get started:"
        Write-Info "  1. Open a new PowerShell window"
        Write-Info "  2. Run: mycelium version"
        Write-Host ""
        Write-Info "For more information, see:"
        Write-Info "  https://github.com/Qubit-Capital/maverick/blob/main/README.md"
    }
    finally {
        # Cleanup temp directory
        if (Test-Path $tmpDir) {
            Remove-Item -Path $tmpDir -Recurse -Force -ErrorAction SilentlyContinue | Out-Null
        }
    }
}

# Run installation
Install-MyceliumWindows
