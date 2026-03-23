# Start all MCP servers (Windows PowerShell)
# Usage:
#   .\scripts\start_all_mcps.ps1          # Start all in background (hidden windows)
#   .\scripts\start_all_mcps.ps1 -Visible # Start all in separate visible windows
#   .\scripts\start_all_mcps.ps1 -Print   # Just print commands (no start)

param([switch]$Visible, [switch]$Print)

$servers = @(
    @{ name = "demo"; port = 8001 },
    @{ name = "calculator"; port = 8002 },
    @{ name = "weather"; port = 8003 },
    @{ name = "notes"; port = 8004 },
    @{ name = "timezone"; port = 8005 },
    @{ name = "search"; port = 8006 },
    @{ name = "translator"; port = 8007 },
    @{ name = "unit_converter"; port = 8008 },
    @{ name = "todo"; port = 8009 },
    @{ name = "flight_booking"; port = 8010 },
    @{ name = "hotel_booking"; port = 8011 },
    @{ name = "currency"; port = 8012 },
    @{ name = "wikipedia"; port = 8013 },
    @{ name = "email"; port = 8014 },
    @{ name = "calendar"; port = 8015 },
    @{ name = "news"; port = 8016 },
    @{ name = "stocks"; port = 8017 },
    @{ name = "reminder"; port = 8018 },
    @{ name = "qr_code"; port = 8019 },
    @{ name = "json_tools"; port = 8020 },
    @{ name = "hash"; port = 8021 },
    @{ name = "uuid"; port = 8022 },
    @{ name = "jio_recharge"; port = 8023 },
    @{ name = "whatsapp_business"; port = 8024 },
    @{ name = "linkedin"; port = 8025 },
    @{ name = "irctc"; port = 8026 }
)

$root = Split-Path -Parent $PSScriptRoot
if (-not $root) { $root = "c:\CTS" }

$count = 0
foreach ($s in $servers) {
    $path = Join-Path $root "mcp-servers\$($s.name)\server.py"
    if (Test-Path $path) {
        if ($Print) {
            Write-Host "cd $root\mcp-servers\$($s.name); pip install mcp; python server.py"
        } else {
            $winStyle = if ($Visible) { "Normal" } else { "Hidden" }
            $cmd = "cd '$root\mcp-servers\$($s.name)'; pip install mcp -q; python server.py"
            $argList = if ($Visible) { @("-NoExit", "-Command", $cmd) } else { @("-Command", $cmd) }
            Start-Process powershell -ArgumentList $argList -WindowStyle $winStyle
            Write-Host "Started $($s.name) on port $($s.port)"
            $count++
        }
    }
}

if (-not $Print -and $count -gt 0) {
    Write-Host "`n$count MCP servers started."
    if (-not $Visible) { Write-Host "Run with -Visible to see each server window." }
}
