param(
    [ValidateSet('help', 'build', 'list', 'crawl', 'crawl-js', 'pokemon', 'pokemon-all',
        'test', 'lint', 'format', 'shell', 'check')]
    [string]$Target = 'help',
    [string]$Spider = 'quotes',
    [ValidateRange(1, 2147483647)]
    [int]$MaxPages = 3,
    [string[]]$ExtraArgs = @()
)

$ErrorActionPreference = 'Stop'

function Invoke-Docker([string[]]$DockerArgs) {
    & docker @DockerArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Docker a termine avec le code $LASTEXITCODE."
    }
}

function Invoke-Lint {
    Invoke-Docker @('compose', 'run', '--rm', 'crawler', 'ruff', 'check', '.')
    Invoke-Docker @('compose', 'run', '--rm', 'crawler', 'ruff', 'format', '--check', '.')
}

Push-Location $PSScriptRoot
try {
    $run = @('compose', 'run', '--rm', 'crawler')
    switch ($Target) {
        'help' {
            Write-Output '.\make.ps1 build | list | crawl | crawl-js | test | lint | format | shell | check'
            Write-Output '.\make.ps1 crawl-js -MaxPages 2'
            Write-Output '.\make.ps1 crawl -ExtraArgs @("-s", "LOG_LEVEL=DEBUG")'
            Write-Output '.\make.ps1 pokemon -MaxPages 1 -ExtraArgs @("-a", "max_cards=5")'
            Write-Output '.\make.ps1 pokemon-all  # Catalogue complet, avec reprise'
        }
        'build' { Invoke-Docker @('compose', 'build', '--pull') }
        'list' { Invoke-Docker ($run + @('scrapy', 'list')) }
        'crawl' {
            $output = if ($Spider -eq 'pokemon_jp') { 'data/pokemon_jp-sample.jsonl' }
                else { "data/$Spider.jsonl" }
            Invoke-Docker ($run + @('scrapy', 'crawl', $Spider, '-a', "max_pages=$MaxPages",
                '-O', $output) + $ExtraArgs)
        }
        'crawl-js' {
            Invoke-Docker ($run + @('scrapy', 'crawl', $Spider, '-a', 'javascript=true',
                '-a', "max_pages=$MaxPages", '-O', "data/$Spider-js.jsonl") + $ExtraArgs)
        }
        'pokemon' {
            Invoke-Docker ($run + @('scrapy', 'crawl', 'pokemon_jp', '-a', "max_pages=$MaxPages",
                '-O', 'data/pokemon_jp-sample.jsonl') + $ExtraArgs)
        }
        'pokemon-all' {
            Invoke-Docker ($run + @('scrapy', 'crawl', 'pokemon_jp', '-a', 'max_pages=0',
                '-s', 'JOBDIR=data/jobs/pokemon_jp', '-o', 'data/pokemon_jp.jsonl') + $ExtraArgs)
        }
        'test' { Invoke-Docker ($run + @('pytest', '-q')) }
        'lint' { Invoke-Lint }
        'format' { Invoke-Docker ($run + @('ruff', 'format', '.')) }
        'shell' { Invoke-Docker ($run + @('/bin/bash')) }
        'check' {
            Invoke-Lint
            Invoke-Docker ($run + @('pytest', '-q'))
        }
    }
}
finally {
    Pop-Location
}
