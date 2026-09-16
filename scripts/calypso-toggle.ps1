$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$log = Join-Path $root 'logs'; New-Item -ItemType Directory -Force $log | Out-Null
$marker = Join-Path $log 'calypso.pid'
$stop = Join-Path $log 'calypso.stop'
$ack = Join-Path $log 'calypso.stop.ack'
$control = $null
if (Test-Path -LiteralPath $marker) {
  try { $control = Get-Content -LiteralPath $marker -Raw | ConvertFrom-Json } catch { $control = $null }
}
$pidValue = if ($control) { [int]$control.pid } else { 0 }
$token = if ($control) { [string]$control.token } else { '' }
$p = if ($pidValue -and $token) { Get-Process -Id $pidValue -ErrorAction SilentlyContinue } else { $null }
if ($p) {
    Remove-Item -LiteralPath $ack -Force -ErrorAction SilentlyContinue
    Set-Content -LiteralPath $stop -Value $token -Encoding ascii
    $deadline=(Get-Date).AddSeconds(5)
    do {
      Start-Sleep -Milliseconds 250
      $p = Get-Process -Id $pidValue -ErrorAction SilentlyContinue
    } while ($p -and (Get-Date) -lt $deadline)
    $ackToken = if (Test-Path -LiteralPath $ack) { (Get-Content -LiteralPath $ack -Raw).Trim() } else { '' }
    if ($p -and $ackToken -eq $token) {
      Stop-Process -Id $pidValue -Force
      $p = $null
    }
    if (-not $p) {
      Remove-Item -LiteralPath $stop,$ack,$marker -Force -ErrorAction SilentlyContinue
      Write-Output 'Calypso stopped.'
      Start-Sleep -Seconds 2
    } else {
      Write-Warning 'Calypso did not acknowledge the stop request; no process was killed.'
      exit 1
    }
} else {
  Remove-Item -LiteralPath $stop,$ack,$marker -Force -ErrorAction SilentlyContinue
  $env:PYTHONPATH = Join-Path $root 'src'
  # Qt translucent windows do not compose reliably after Win32 SetParent into
  # Explorer's WorkerW. Keep them as native tool windows: normal applications
  # cover them, while Win+D reveals them with the wallpaper.
  $started = Start-Process python -ArgumentList '-m calypso' -WorkingDirectory $root -WindowStyle Hidden -PassThru
  $deadline=(Get-Date).AddSeconds(5)
  do {
    Start-Sleep -Milliseconds 200
    $ready = Test-Path -LiteralPath $marker
    $started.Refresh()
  } while (-not $ready -and -not $started.HasExited -and (Get-Date) -lt $deadline)
  if ($ready -and -not $started.HasExited) {
    Write-Output 'Calypso started. Press Win+D to view the desktop.'
    Start-Sleep -Seconds 2
  } else {
    Write-Warning "Calypso failed to start. Check logs\calypso.log."
    exit 1
  }
}
