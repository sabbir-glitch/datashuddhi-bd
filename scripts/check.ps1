<#
.SYNOPSIS
    Runs the DataShuddhi BD quality checks: ruff (lint + format), pyright and pytest.

.DESCRIPTION
    Uses the project's own virtual environment (.venv) by calling its python.exe directly,
    so the environment does not need to be activated and the PowerShell execution policy
    does not need to be changed.

    This script only RUNS checks. It does not install anything, create the virtual
    environment, change project files, or use the network itself (pyright may download its
    own helper on first use; see README).

    All text, including the output of ruff, pyright and pytest, is written to PowerShell's
    normal output stream. It is therefore visible on screen and can be captured with a
    plain pipeline, for example:
        .\scripts\check.ps1 | Tee-Object -FilePath "$env:TEMP\check-log.txt"
    (Windows PowerShell 5.1 writes such a file as UTF-16; Notepad opens it normally.)

    Every check is judged ONLY by its process exit code. The summary lists each check as
    PASSED, FAILED or SKIPPED. A check that cannot be started counts as FAILED.

    Exit codes:
      0  every check that ran passed (checks skipped on request are listed as SKIPPED)
      1  at least one check failed
      3  the virtual environment is missing or its Python cannot be run (no check ran)

.PARAMETER SkipTypeCheck
    Skip pyright. The summary then reports it as SKIPPED, not as passed.

.EXAMPLE
    PS C:\dev\datashuddhi-bd> .\scripts\check.ps1
#>
[CmdletBinding()]
param(
    [switch]$SkipTypeCheck
)

# Failures are detected through process exit codes below, not through exceptions.
$ErrorActionPreference = 'Continue'

$repoRoot = Split-Path -Parent $PSScriptRoot
$script:VenvPython = Join-Path $repoRoot '.venv\Scripts\python.exe'
$script:Results = New-Object System.Collections.ArrayList

function Add-Result {
    param(
        [string]$Name,
        [string]$Status,
        $ExitCode
    )
    [void]$script:Results.Add([pscustomobject]@{ Name = $Name; Status = $Status; ExitCode = $ExitCode })
}

# Runs one check. The tool's own output flows to the output stream (it is NOT stored in a
# variable and NOT sent to Out-Host), so it is shown and can be redirected or tee'd.
# This function deliberately returns nothing; the outcome is recorded with Add-Result.
function Invoke-Check {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string[]]$PythonArgs
    )
    Write-Output ''
    Write-Output "=== $Name ==="
    Write-Output ('> python ' + ($PythonArgs -join ' '))

    $global:LASTEXITCODE = $null
    $code = $null
    $startError = $null
    try {
        # 2>&1 merges error text into the same stream; "$_" turns every line into plain text.
        & $script:VenvPython @PythonArgs 2>&1 | ForEach-Object { "$_" }
        $code = $global:LASTEXITCODE
    }
    catch {
        $startError = $_.Exception.Message
        Write-Output ('ERROR: this check could not be started: ' + $startError)
    }

    # PASSED only if the process started AND reported exit code 0. Anything else is FAILED.
    $status = 'FAILED'
    if (($null -eq $startError) -and ($null -ne $code) -and ($code -eq 0)) {
        $status = 'PASSED'
    }
    Write-Output ("--> $Name : $status (exit code: " + $(if ($null -eq $code) { 'none' } else { $code }) + ')')
    Add-Result -Name $Name -Status $status -ExitCode $code
}

if (-not (Test-Path -LiteralPath $script:VenvPython)) {
    Write-Output "ERROR: virtual environment not found: $script:VenvPython"
    Write-Output 'Create it first. From the project folder run:'
    Write-Output '    py -m venv .venv'
    Write-Output '    .\.venv\Scripts\python.exe -m pip install -e ".[dev]" -c constraints-dev.txt'
    Write-Output 'RESULT: NOT RUN - no checks were executed.'
    exit 3
}

$finalExit = 0
Push-Location $repoRoot
try {
    Write-Output "Repository : $repoRoot"

    # Interpreter version: captured on purpose, then printed through the output stream.
    $global:LASTEXITCODE = $null
    $interpreterText = $null
    $interpreterExit = $null
    try {
        $interpreterText = (@(& $script:VenvPython --version 2>&1 | ForEach-Object { "$_" }) -join ' ').Trim()
        $interpreterExit = $global:LASTEXITCODE
    }
    catch {
        $interpreterText = 'ERROR: ' + $_.Exception.Message
    }

    if (($null -eq $interpreterExit) -or ($interpreterExit -ne 0)) {
        Write-Output "Interpreter: UNUSABLE - $interpreterText"
        Write-Output "Interpreter path: $script:VenvPython"
        Write-Output 'Recreate or repair the virtual environment (see README.md).'
        Write-Output 'RESULT: NOT RUN - no checks were executed.'
        $finalExit = 3
    }
    else {
        Write-Output "Interpreter: $interpreterText ($script:VenvPython)"

        Invoke-Check -Name 'ruff check' -PythonArgs @('-m', 'ruff', 'check', '.')
        Invoke-Check -Name 'ruff format --check' -PythonArgs @('-m', 'ruff', 'format', '--check', '.')

        if ($SkipTypeCheck) {
            Write-Output ''
            Write-Output '=== pyright ==='
            Write-Output 'SKIPPED by request (-SkipTypeCheck). Types are NOT verified.'
            Add-Result -Name 'pyright' -Status 'SKIPPED' -ExitCode $null
        }
        else {
            Invoke-Check -Name 'pyright' -PythonArgs @('-m', 'pyright', '--pythonpath', $script:VenvPython)
        }

        Invoke-Check -Name 'pytest' -PythonArgs @('-m', 'pytest')

        Write-Output ''
        Write-Output '=== Summary (judged by process exit codes) ==='
        Write-Output ('{0,-22} {1,-8} {2}' -f 'Check', 'Status', 'Exit code')
        foreach ($r in $script:Results) {
            $shownCode = 'n/a'
            if ($null -ne $r.ExitCode) { $shownCode = [string]$r.ExitCode }
            Write-Output ('{0,-22} {1,-8} {2}' -f $r.Name, $r.Status, $shownCode)
        }

        $failed = @($script:Results | Where-Object { $_.Status -eq 'FAILED' })
        $skipped = @($script:Results | Where-Object { $_.Status -eq 'SKIPPED' })
        $passed = @($script:Results | Where-Object { $_.Status -eq 'PASSED' })

        Write-Output ''
        if ($failed.Count -gt 0) {
            Write-Output ('RESULT: FAILED - ' + $failed.Count + ' check(s) failed: ' + (($failed | ForEach-Object { $_.Name }) -join ', '))
            Write-Output 'Read the tool output above. If a tool is reported as missing, run:'
            Write-Output '    .\.venv\Scripts\python.exe -m pip install -e ".[dev]" -c constraints-dev.txt'
            $finalExit = 1
        }
        elseif ($skipped.Count -gt 0) {
            Write-Output ('RESULT: PASSED WITH SKIPPED CHECKS - ' + $passed.Count + ' passed; ' + $skipped.Count + ' SKIPPED and NOT verified: ' + (($skipped | ForEach-Object { $_.Name }) -join ', '))
            $finalExit = 0
        }
        else {
            Write-Output ('RESULT: PASSED - all ' + $passed.Count + ' checks passed.')
            $finalExit = 0
        }
    }
}
finally {
    Pop-Location
}

exit $finalExit
