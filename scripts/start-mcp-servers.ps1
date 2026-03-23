# Start all MCP servers in separate windows (PowerShell)
$servers = @(
    @{Name="Demo"; Path="mcp-servers/demo"; Port=8001},
    @{Name="Calculator"; Path="mcp-servers/calculator"; Port=8002},
    @{Name="Weather"; Path="mcp-servers/weather"; Port=8003},
    @{Name="Notes"; Path="mcp-servers/notes"; Port=8004},
    @{Name="Timezone"; Path="mcp-servers/timezone"; Port=8005},
    @{Name="Search"; Path="mcp-servers/search"; Port=8006}
)

foreach ($s in $servers) {
    Write-Host "Starting $($s.Name) on port $($s.Port)..."
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd $PWD\$($s.Path); pip install mcp -q; python server.py"
    Start-Sleep -Seconds 1
}
Write-Host "All MCP servers started. Register in Settings -> MCP Servers"
