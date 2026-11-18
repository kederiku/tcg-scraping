# Test the Docker CLI boundary without requiring a running Docker engine.
$ErrorActionPreference = 'Stop'
$global:TestDockerCalls = [System.Collections.Generic.List[object]]::new()
$global:TestFailDocker = $false
function global:docker {
    $global:TestDockerCalls.Add(@($args))
    if ($global:TestFailDocker) { $global:LASTEXITCODE = 9 }
    else { $global:LASTEXITCODE = 0 }
}

function Assert-Call([int]$Index, [string[]]$Expected) {
    $actual = $global:TestDockerCalls[$Index] -join '|'
    if ($actual -ne ($Expected -join '|')) {
        throw "Unexpected Docker arguments: $actual"
    }
}

$wrapper = Join-Path (Split-Path $PSScriptRoot) 'make.ps1'
& $wrapper build
Assert-Call 0 @('compose', 'build', '--pull')
& $wrapper crawl-js -MaxPages 2 -ExtraArgs @('-s', 'LOG_LEVEL=DEBUG')
Assert-Call 1 @('compose', 'run', '--rm', 'crawler', 'scrapy', 'crawl', 'quotes',
    '-a', 'javascript=true', '-a', 'max_pages=2', '-O', 'data/quotes-js.jsonl', '-s', 'LOG_LEVEL=DEBUG')
& $wrapper check
if ($global:TestDockerCalls.Count -ne 5) { throw 'check must call lint, format-check and tests' }
& $wrapper pokemon -MaxPages 1 -ExtraArgs @('-a', 'max_cards=5')
Assert-Call 5 @('compose', 'run', '--rm', 'crawler', 'scrapy', 'crawl', 'pokemon_jp',
    '-a', 'max_pages=1', '-O', 'data/pokemon_jp-sample.jsonl', '-a', 'max_cards=5')
& $wrapper pokemon-all
Assert-Call 6 @('compose', 'run', '--rm', 'crawler', 'scrapy', 'crawl', 'pokemon_jp',
    '-a', 'max_pages=0', '-s', 'JOBDIR=data/jobs/pokemon_jp', '-o', 'data/pokemon_jp.jsonl')
& $wrapper crawl -Spider pokemon_jp -MaxPages 1
Assert-Call 7 @('compose', 'run', '--rm', 'crawler', 'scrapy', 'crawl', 'pokemon_jp',
    '-a', 'max_pages=1', '-O', 'data/pokemon_jp-sample.jsonl')
& $wrapper pokemon-kr -MaxPages 1 -ExtraArgs @('-a', 'max_cards=5')
Assert-Call 8 @('compose', 'run', '--rm', 'crawler', 'scrapy', 'crawl', 'pokemon_kr',
    '-a', 'max_pages=1', '-O', 'data/pokemon_kr-sample.jsonl', '-a', 'max_cards=5')
& $wrapper pokemon-kr-all
Assert-Call 9 @('compose', 'run', '--rm', 'crawler', 'scrapy', 'crawl', 'pokemon_kr',
    '-a', 'max_pages=0', '-s', 'JOBDIR=data/jobs/pokemon_kr', '-o', 'data/pokemon_kr.jsonl')
& $wrapper crawl -Spider pokemon_kr -MaxPages 1
Assert-Call 10 @('compose', 'run', '--rm', 'crawler', 'scrapy', 'crawl', 'pokemon_kr',
    '-a', 'max_pages=1', '-O', 'data/pokemon_kr-sample.jsonl')
$global:TestFailDocker = $true
$failed = $false
try { & $wrapper check }
catch { $failed = $true }
if (-not $failed -or $global:TestDockerCalls.Count -ne 12) { throw 'Docker failures must stop immediately' }
$global:LASTEXITCODE = 0
Write-Output 'PowerShell command tests passed.'
