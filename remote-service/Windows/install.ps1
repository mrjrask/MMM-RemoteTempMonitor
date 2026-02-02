$ErrorActionPreference = "Stop"

$serviceDir = "$env:ProgramData\RemoteTempMonitor"
$scriptName = "temp_broadcaster_windows.py"
$taskName = "RemoteTempMonitor"

Write-Host "Creating install directory at $serviceDir"
New-Item -ItemType Directory -Path $serviceDir -Force | Out-Null
Copy-Item -Path $PSScriptRoot\$scriptName -Destination $serviceDir\$scriptName -Force

Write-Host "Ensuring Python dependencies"
python -m pip install --upgrade pip | Out-Null
python -m pip install wmi pywin32 | Out-Null

$action = New-ScheduledTaskAction -Execute "python" -Argument "$serviceDir\$scriptName"
$trigger = New-ScheduledTaskTrigger -AtStartup
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -RestartCount 5 -RestartInterval (New-TimeSpan -Minutes 1)

$task = New-ScheduledTask -Action $action -Trigger $trigger -Principal $principal -Settings $settings

Write-Host "Registering scheduled task $taskName"
Register-ScheduledTask -TaskName $taskName -InputObject $task -Force | Out-Null
Start-ScheduledTask -TaskName $taskName

Write-Host "Remote Temperature Monitor installed and started."
