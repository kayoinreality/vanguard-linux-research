$ErrorActionPreference = 'Stop'
$taskOutput = Join-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) 'outputs\arch-lab'
$taskConfig = Get-Content -LiteralPath (Join-Path $taskOutput 'config.json') -Raw | ConvertFrom-Json
Import-Module Hyper-V
$taskVM = Get-VM -Name $taskConfig.VMName
if ($taskVM.Notes -ne ('Codex Arch laboratory instance ' + $taskConfig.InstanceId)) { throw 'VM ownership mismatch.' }
$taskSetupPath = Join-Path $taskOutput 'preparar-vm.ps1'
foreach($taskProcess in @(Get-CimInstance Win32_Process -Filter "Name='pwsh.exe'" | Where-Object { $_.CommandLine -like ('*' + $taskSetupPath + '*') })) {
    Stop-Process -Id $taskProcess.ProcessId -Force
}
$taskComputer = Get-CimInstance -Namespace 'root\virtualization\v2' -ClassName Msvm_ComputerSystem -Filter ("Name='" + $taskVM.Id.ToString() + "'")
$taskKeyboard = Get-CimAssociatedInstance -InputObject $taskComputer -ResultClassName Msvm_Keyboard
if (@($taskKeyboard).Count -ne 1) { throw 'Virtual keyboard not uniquely identified.' }
function Send-LabKey([int]$Key) {
    $taskPressed = Invoke-CimMethod -InputObject $taskKeyboard -MethodName PressKey -Arguments @{keyCode=[uint32]$Key}
    $taskReleased = Invoke-CimMethod -InputObject $taskKeyboard -MethodName ReleaseKey -Arguments @{keyCode=[uint32]$Key}
    if ($taskPressed.ReturnValue -ne 0 -or $taskReleased.ReturnValue -ne 0) { throw 'Virtual key operation failed.' }
}
# Select the live ISO's root autologin console, clear any partial command.
Invoke-CimMethod -InputObject $taskKeyboard -MethodName PressKey -Arguments @{keyCode=[uint32]17} | Out-Null
Invoke-CimMethod -InputObject $taskKeyboard -MethodName PressKey -Arguments @{keyCode=[uint32]18} | Out-Null
Send-LabKey 112
Invoke-CimMethod -InputObject $taskKeyboard -MethodName ReleaseKey -Arguments @{keyCode=[uint32]18} | Out-Null
Invoke-CimMethod -InputObject $taskKeyboard -MethodName ReleaseKey -Arguments @{keyCode=[uint32]17} | Out-Null
Start-Sleep -Seconds 2
Invoke-CimMethod -InputObject $taskKeyboard -MethodName PressKey -Arguments @{keyCode=[uint32]17} | Out-Null
Send-LabKey 67
Invoke-CimMethod -InputObject $taskKeyboard -MethodName ReleaseKey -Arguments @{keyCode=[uint32]17} | Out-Null
Send-LabKey 13
$taskCommand = "install -d -m700 /root/.ssh; cp /run/arch-lab/authorized-key.pub /root/.ssh/authorized_keys; chmod 600 /root/.ssh/authorized_keys; usermod -p '*NP*' root; mkdir -p /etc/ssh/sshd_config.d; printf 'PermitRootLogin prohibit-password\nPasswordAuthentication no\n' > /etc/ssh/sshd_config.d/00-lab-recovery.conf; systemctl restart sshd"
if ($taskCommand.Length -gt 512) { throw 'Virtual keyboard command is too long.' }
$taskTyped = Invoke-CimMethod -InputObject $taskKeyboard -MethodName TypeText -Arguments @{asciiText=$taskCommand}
if ($taskTyped.ReturnValue -ne 0) { throw ('Virtual keyboard rejected the recovery command: ' + $taskTyped.ReturnValue) }
Send-LabKey 13
[pscustomobject]@{CommandSent=$true;VMName=$taskConfig.VMName;UpdatedAtUTC=[DateTimeOffset]::UtcNow.ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $taskOutput 'console-recovery.json') -Encoding utf8
