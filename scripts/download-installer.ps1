[CmdletBinding()]
param(
    [string]$Tag = 'installer-2026-09-20',
    [string]$OutputDirectory = (Join-Path (Get-Location) 'kali-installer-download'),
    [string]$BaseUrl = '',
    [switch]$Offline
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$isoName = 'kali-linux-rolling-installer-amd64.iso'
if ($Tag -cnotmatch '^[A-Za-z0-9_-][A-Za-z0-9._-]*$') { throw 'Invalid release tag' }
if (-not $BaseUrl) { $BaseUrl = "https://github.com/agammann/kali-installer/releases/download/$Tag" }
if ($BaseUrl -notmatch '^https://' -and $BaseUrl -notmatch '^http://127\.0\.0\.1:') {
    throw 'Use an HTTPS release URL (or a localhost URL for testing)'
}
$outDir = [IO.Path]::GetFullPath($OutputDirectory)
[IO.Directory]::CreateDirectory($outDir) | Out-Null
$temps = [Collections.Generic.List[string]]::new()
Add-Type -AssemblyName System.Net.Http
$client = [Net.Http.HttpClient]::new()
$client.Timeout = [TimeSpan]::FromHours(4)
$client.DefaultRequestHeaders.UserAgent.ParseAdd('kali-installer-download/1.0')

function New-DownloadTemp {
    $path = Join-Path $outDir ('.download-' + [Guid]::NewGuid().ToString('N'))
    $temps.Add($path)
    return $path
}
function Get-Sha256([string]$Path) {
    $sha = [Security.Cryptography.SHA256]::Create()
    $stream = [IO.File]::OpenRead($Path)
    try {
        return [BitConverter]::ToString($sha.ComputeHash($stream)).Replace('-', '').ToLowerInvariant()
    } finally {
        $stream.Dispose()
        $sha.Dispose()
    }
}
function Get-ReleaseFile([string]$Name, [string]$Destination) {
    for ($attempt = 1; $attempt -le 3; $attempt++) {
        $response = $null
        $source = $null
        $target = $null
        try {
            $response = $client.GetAsync(($BaseUrl.TrimEnd('/') + '/' + $Name), [Net.Http.HttpCompletionOption]::ResponseHeadersRead).GetAwaiter().GetResult()
            $response.EnsureSuccessStatusCode() | Out-Null
            $source = $response.Content.ReadAsStreamAsync().GetAwaiter().GetResult()
            $target = [IO.File]::Open($Destination, [IO.FileMode]::Create, [IO.FileAccess]::Write, [IO.FileShare]::None)
            $source.CopyTo($target)
            return
        } catch {
            if ($attempt -eq 3) { throw }
            Start-Sleep -Seconds $attempt
        } finally {
            if ($null -ne $target) { $target.Dispose() }
            if ($null -ne $source) { $source.Dispose() }
            if ($null -ne $response) { $response.Dispose() }
        }
    }
}

try {
    $manifest = Join-Path $outDir 'SHA256SUMS'
    $manifestTemp = $null
    if (-not $Offline) {
        $manifestTemp = New-DownloadTemp
        Get-ReleaseFile 'SHA256SUMS' $manifestTemp
        $manifest = $manifestTemp
    }
    $lines = [IO.File]::ReadAllLines($manifest)
    if ($lines.Length -lt 2 -or $lines.Length -gt 1000) { throw 'Invalid manifest part count' }
    $parts = @()
    $isoHash = ''
    for ($i = 0; $i -lt $lines.Length; $i++) {
        if ($lines[$i] -cnotmatch '^([0-9a-f]{64})  (.+)$') { throw 'Invalid checksum manifest' }
        $digest = $Matches[1]
        $name = $Matches[2]
        if ($i -eq 0) {
            if ($name -cne $isoName) { throw 'Manifest must start with the ISO checksum' }
            $isoHash = $digest
        } else {
            if ($name -cne ('{0}.part{1:D3}' -f $isoName, $i)) { throw 'Invalid or out-of-order part name' }
            $parts += [pscustomobject]@{ Name = $name; Hash = $digest }
        }
    }
    if ($null -ne $manifestTemp) {
        Move-Item -LiteralPath $manifestTemp -Destination (Join-Path $outDir 'SHA256SUMS') -Force
    }
    $isoPath = Join-Path $outDir $isoName
    if (Test-Path -LiteralPath $isoPath) {
        if ((Get-Sha256 $isoPath) -cne $isoHash) { throw 'Existing ISO has a different checksum; use an empty output directory' }
        Write-Host "Already verified: $isoPath"
        return
    }
    foreach ($part in $parts) {
        $partPath = Join-Path $outDir $part.Name
        if ((Test-Path -LiteralPath $partPath -PathType Leaf) -and (Get-Sha256 $partPath) -ceq $part.Hash) {
            Write-Host "Verified cached part: $($part.Name)"
            continue
        }
        if ($Offline) { throw "Missing or corrupt part: $($part.Name)" }
        Write-Host "Downloading $($part.Name)"
        $temp = New-DownloadTemp
        Get-ReleaseFile $part.Name $temp
        if ((Get-Sha256 $temp) -cne $part.Hash) { throw "Checksum mismatch: $($part.Name)" }
        Move-Item -LiteralPath $temp -Destination $partPath -Force
    }
    Write-Host 'Joining verified parts...'
    $isoTemp = New-DownloadTemp
    $target = [IO.File]::Open($isoTemp, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
    try {
        foreach ($part in $parts) {
            $source = [IO.File]::OpenRead((Join-Path $outDir $part.Name))
            try { $source.CopyTo($target) } finally { $source.Dispose() }
        }
    } finally { $target.Dispose() }
    if ((Get-Sha256 $isoTemp) -cne $isoHash) { throw 'Reconstructed ISO checksum mismatch' }
    Move-Item -LiteralPath $isoTemp -Destination $isoPath
    Write-Host "Verified ISO ready: $isoPath"
} finally {
    $client.Dispose()
    foreach ($temp in $temps) {
        if (Test-Path -LiteralPath $temp -PathType Leaf) { Remove-Item -LiteralPath $temp -Force }
    }
}
