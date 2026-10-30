$ErrorActionPreference = "Stop"

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principalCheck = New-Object Security.Principal.WindowsPrincipal($identity)
if (-not $principalCheck.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Run this installer as Administrator."
}
$pythonPath = (Get-Command python -CommandType Application).Source
if ($pythonPath -like "*WindowsApps*" -or $pythonPath.StartsWith($env:USERPROFILE, [System.StringComparison]::OrdinalIgnoreCase)) { throw "Install a machine-wide Python accessible to SYSTEM." }

$serviceDir = "$env:ProgramData\RemoteTempMonitor"
$scriptName = "temp_broadcaster_windows.py"
$taskName = "RemoteTempMonitor"

Write-Host "Creating install directory at $serviceDir"
New-Item -ItemType Directory -Path $serviceDir -Force | Out-Null
Copy-Item -Path $PSScriptRoot\$scriptName -Destination $serviceDir\$scriptName -Force

Copy-Item -Path "$PSScriptRoot\..\broadcaster_common.py" -Destination "$serviceDir\broadcaster_common.py" -Force

Write-Host "Creating isolated service Python environment"
& $pythonPath -m venv "$serviceDir\venv"
if ($LASTEXITCODE -ne 0) { throw "Python environment creation failed." }
$servicePython = "$serviceDir\venv\Scripts\python.exe"
Write-Host "Ensuring Python dependencies"
& $servicePython -m pip install wmi pywin32 | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Python dependency installation failed." }

$action = New-ScheduledTaskAction -Execute $servicePython -Argument "`"$serviceDir\$scriptName`"" -WorkingDirectory $serviceDir
$trigger = New-ScheduledTaskTrigger -AtStartup
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -RestartCount 5 -RestartInterval (New-TimeSpan -Minutes 1)

$task = New-ScheduledTask -Action $action -Trigger $trigger -Principal $principal -Settings $settings

Write-Host "Registering scheduled task $taskName"
Register-ScheduledTask -TaskName $taskName -InputObject $task -Force | Out-Null
Start-ScheduledTask -TaskName $taskName

Write-Host "Remote Temperature Monitor installed and started."
