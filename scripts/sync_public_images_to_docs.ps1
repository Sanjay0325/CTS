# Sync images from public/ to docs/assets/ and update README + SYSTEM_ARCHITECTURE files.
# Run when adding new images to public/ so they appear in the docs.

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$publicDir = Join-Path $projectRoot "public"
$assetsDir = Join-Path $projectRoot "docs" "assets"

# Ensure docs/assets exists
if (-not (Test-Path $assetsDir)) { New-Item -ItemType Directory -Path $assetsDir -Force | Out-Null }

# Copy all images from public to docs/assets
$imageExts = @("*.png", "*.jpg", "*.jpeg", "*.webp", "*.gif")
$images = @()
foreach ($ext in $imageExts) {
    $found = Get-ChildItem -Path $publicDir -Filter $ext -ErrorAction SilentlyContinue
    if ($found) { $images += $found }
}
foreach ($img in $images) {
    Copy-Item $img.FullName (Join-Path $assetsDir $img.Name) -Force
    Write-Host "Copied: $($img.Name)"
}

$imageNames = $images | ForEach-Object { $_.Name } | Sort-Object -Unique
if ($imageNames.Count -eq 0) {
    Write-Host "No images in public/"
    exit 0
}

# Build img tags block
$imgTagsRoot = ""
$imgTagsDocs = ""
foreach ($name in $imageNames) {
    $baseName = [System.IO.Path]::GetFileNameWithoutExtension($name)
    $imgTagsRoot += "<img src=`"docs/assets/$name`" alt=`"$baseName`" width=`"800`"/>`n`n"
    $imgTagsDocs += "<img src=`"assets/$name`" alt=`"$baseName`" width=`"800`"/>`n`n"
}

# Update README - replace only the Architecture Diagrams img section
$readmePath = Join-Path $projectRoot "README.md"
$readme = Get-Content $readmePath -Raw -Encoding UTF8
$readmePattern = '(?s)(### Architecture Diagrams\s*\n\s*)<img[^>]*>[\s\S]*?(?=\n```|\n---|\n##)'
$readmeReplacement = "`$1$imgTagsRoot"
if ($readme -match $readmePattern) {
    $readme = $readme -replace $readmePattern, $readmeReplacement
    Set-Content $readmePath -Value $readme -Encoding UTF8 -NoNewline
    Write-Host "Updated: README.md"
}

# Update root SYSTEM_ARCHITECTURE - replace only img section
$archPath = Join-Path $projectRoot "SYSTEM_ARCHITECTURE.md"
$arch = Get-Content $archPath -Raw -Encoding UTF8
$archPattern = '(?s)(### Architecture Diagrams\s*\n\s*)<img[^>]*>[\s\S]*?(?=\n---|\n##)'
$archReplacement = "`$1$imgTagsRoot"
if ($arch -match $archPattern) {
    $arch = $arch -replace $archPattern, $archReplacement
    Set-Content $archPath -Value $arch -Encoding UTF8 -NoNewline
    Write-Host "Updated: SYSTEM_ARCHITECTURE.md"
}

# Update docs/SYSTEM_ARCHITECTURE - use assets/ path
$archDocsPath = Join-Path $projectRoot "docs" "SYSTEM_ARCHITECTURE.md"
$archDocs = Get-Content $archDocsPath -Raw -Encoding UTF8
$archDocsPattern = '(?s)(### Architecture Diagrams\s*\n\s*)<img[^>]*>[\s\S]*?(?=\n---|\n##)'
$archDocsReplacement = "`$1$imgTagsDocs"
if ($archDocs -match $archDocsPattern) {
    $archDocs = $archDocs -replace $archDocsPattern, $archDocsReplacement
    Set-Content $archDocsPath -Value $archDocs -Encoding UTF8 -NoNewline
    Write-Host "Updated: docs/SYSTEM_ARCHITECTURE.md"
}

Write-Host "Synced $($imageNames.Count) image(s) to docs/assets/"
