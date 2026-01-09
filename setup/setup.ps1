# Run as Administrator

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "FINAL FIX - Hidden Background Execution" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Check admin
if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
  Write-Host "[ERROR] This script must be run as Administrator!" -ForegroundColor Red
  pause
  exit
}

# Dynamic path resolution
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$rootPath = Split-Path -Parent $scriptPath
$exePath = Join-Path $rootPath "dist\monitor.exe"
$workingDir = Join-Path $rootPath "dist"

Write-Host "Detected paths:" -ForegroundColor Gray
Write-Host "  Root: $rootPath" -ForegroundColor Gray
Write-Host "  Executable: $exePath" -ForegroundColor Gray
Write-Host ""

# Stop any running instances
Write-Host "Stopping any running monitor instances..." -ForegroundColor Yellow
Stop-Process -Name monitor -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# Delete old task and registry entry
Write-Host "Removing old startup entries..." -ForegroundColor Yellow
schtasks /Delete /TN "AntiTheftMonitor" /F 2>$null | Out-Null
reg delete "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Run" /v AntiTheftMonitor /F 2>$null | Out-Null

# Create XML with proper hidden execution settings
$xml = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>Anti-Theft Monitor - Runs hidden in background</Description>
  </RegistrationInfo>
  <Triggers>
    <BootTrigger>
      <Enabled>true</Enabled>
      <Delay>PT20S</Delay>
    </BootTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>S-1-5-18</UserId>
      <RunLevel>HighestAvailable</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>false</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <IdleSettings>
      <StopOnIdleEnd>false</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>true</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <DisallowStartOnRemoteAppSession>false</DisallowStartOnRemoteAppSession>
    <UseUnifiedSchedulingEngine>true</UseUnifiedSchedulingEngine>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <Priority>7</Priority>
    <RestartOnFailure>
      <Interval>PT1M</Interval>
      <Count>999</Count>
    </RestartOnFailure>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>$exePath</Command>
      <WorkingDirectory>$workingDir</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
"@

# Save XML
$xmlPath = Join-Path $env:TEMP "antitheft_final.xml"
$xml | Out-File -FilePath $xmlPath -Encoding unicode

# Create task
Write-Host "Creating hidden background task..." -ForegroundColor Yellow
$result = schtasks /Create /TN "AntiTheftMonitor" /XML $xmlPath /F 2>&1

if ($LASTEXITCODE -eq 0) {
  Write-Host ""
  Write-Host "[SUCCESS] Task created successfully!" -ForegroundColor Green
  Write-Host ""
  Write-Host "Configuration:" -ForegroundColor Cyan
  Write-Host "  [OK] Runs on BOOT (20 seconds after startup)" -ForegroundColor White
  Write-Host "  [OK] Runs as SYSTEM (before login)" -ForegroundColor White
  Write-Host "  [OK] HIDDEN execution (no console window)" -ForegroundColor White
  Write-Host "  [OK] Auto-restart on failure (999 attempts)" -ForegroundColor White
  Write-Host "  [OK] No time limit (runs forever)" -ForegroundColor White
}
else {
  Write-Host ""
  Write-Host "[ERROR] Failed to create task!" -ForegroundColor Red
  Write-Host $result -ForegroundColor Red
}

# Clean up
Remove-Item $xmlPath -ErrorAction SilentlyContinue

# Verify
Write-Host ""
Write-Host "Verifying task..." -ForegroundColor Yellow
$taskInfo = schtasks /Query /TN "AntiTheftMonitor" /V /FO LIST 2>&1 | Select-String "Status|Run As|Task To Run"
$taskInfo | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }

# Start the task now for immediate testing
Write-Host ""
Write-Host "Starting monitor now..." -ForegroundColor Yellow
schtasks /Run /TN "AntiTheftMonitor" | Out-Null
Start-Sleep -Seconds 3

# Check if it's running
$process = Get-Process -Name monitor -ErrorAction SilentlyContinue
if ($process) {
  Write-Host "[SUCCESS] Monitor is running (PID: $($process.Id))" -ForegroundColor Green
  Write-Host "  [OK] No console window visible (running hidden)" -ForegroundColor White
}
else {
  Write-Host "[WARNING] Monitor may not have started. Check Task Scheduler." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "CRITICAL TEST:" -ForegroundColor Yellow
Write-Host "  1. SHUT DOWN your computer (not restart!)" -ForegroundColor White
Write-Host "  2. Power it back on" -ForegroundColor White
Write-Host "  3. At lock screen, enter 2 wrong PINs" -ForegroundColor White
Write-Host "  4. Log in correctly" -ForegroundColor White
Write-Host "  5. Check Telegram for the alert!" -ForegroundColor White
Write-Host ""
Write-Host "The monitor will run HIDDEN in the background." -ForegroundColor Cyan
Write-Host "You won't see any windows or notifications." -ForegroundColor Cyan
Write-Host ""
pause
