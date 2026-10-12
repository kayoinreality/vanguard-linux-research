$ErrorActionPreference = 'Stop'
$taskOutput = Join-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) 'outputs\arch-lab'
$taskConfig = Get-Content -LiteralPath (Join-Path $taskOutput 'config.json') -Raw | ConvertFrom-Json
foreach($taskOldHelper in @(Get-CimInstance Win32_Process -Filter "Name='pwsh.exe'" | Where-Object { $_.ProcessId -ne $PID -and $_.CommandLine -like ('*' + $PSCommandPath + '*') })) {
    Stop-Process -Id $taskOldHelper.ProcessId -Force
}
Import-Module Hyper-V
$taskVM = Get-VM -Name $taskConfig.VMName
if ($taskVM.Notes -ne ('Codex Arch laboratory instance ' + $taskConfig.InstanceId)) { throw 'VM ownership mismatch.' }
$taskComputer = Get-CimInstance -Namespace 'root\virtualization\v2' -ClassName Msvm_ComputerSystem -Filter ("Name='" + $taskVM.Id.ToString() + "'")
$taskKeyboard = Get-CimAssociatedInstance -InputObject $taskComputer -ResultClassName Msvm_Keyboard
$taskSetting = @(Get-CimAssociatedInstance -InputObject $taskComputer -ResultClassName Msvm_VirtualSystemSettingData | Where-Object {$_.VirtualSystemType -eq 'Microsoft:Hyper-V:System:Realized'})[0]
$taskManager = Get-CimInstance -Namespace 'root\virtualization\v2' -ClassName Msvm_VirtualSystemManagementService
$taskRequest = Join-Path $PSScriptRoot 'admin-request.json'
$taskResponse = Join-Path $PSScriptRoot 'admin-response.json'
$taskUntil = [DateTimeOffset]::UtcNow.AddMinutes(40)
$taskLastNonce = ''
function Capture-LabFrame {
    $taskFrame = Invoke-CimMethod -InputObject $taskManager -MethodName GetVirtualSystemThumbnailImage -Arguments @{TargetSystem=$taskSetting;WidthPixels=[uint16]1024;HeightPixels=[uint16]768}
    if ($taskFrame.ReturnValue -ne 0) {throw ('Thumbnail operation failed: '+$taskFrame.ReturnValue)}
    [IO.File]::WriteAllBytes((Join-Path $PSScriptRoot 'console.rgb565'), [byte[]]$taskFrame.ImageData)
    return @{Frame='console.rgb565';Width=1024;Height=768;Bytes=$taskFrame.ImageData.Count}
}
function Lab-Key([int]$Key) {
    $taskPress = Invoke-CimMethod -InputObject $taskKeyboard -MethodName PressKey -Arguments @{keyCode=[uint32]$Key}
    $taskRelease = Invoke-CimMethod -InputObject $taskKeyboard -MethodName ReleaseKey -Arguments @{keyCode=[uint32]$Key}
    if($taskPress.ReturnValue -ne 0 -or $taskRelease.ReturnValue -ne 0){throw 'Virtual key failed.'}
}
function Lab-Text([string]$Text) {
    # Send individual virtual keys at a bounded rate; bulk TypeText produced
    # corrupted input on this Linux live console.
    foreach($taskCharacter in $Text.ToCharArray()) {
        $taskShift=$false
        if($taskCharacter -cmatch '[a-z]'){$taskCode=[int][char]([string]$taskCharacter).ToUpperInvariant()}
        elseif($taskCharacter -cmatch '[A-Z]'){$taskCode=[int]$taskCharacter;$taskShift=$true}
        elseif($taskCharacter -match '[0-9]'){$taskCode=[int]$taskCharacter}
        else {
            $taskPunctuation=@{
                ' '=@(32,$false);'-'=@(189,$false);'_'=@(189,$true)
                '/'=@(191,$false);'.'=@(190,$false);';'=@(186,$false);':'=@(186,$true)
                '='=@(187,$false);'+'=@(187,$true);'\'=@(220,$false);'|'=@(220,$true)
                "'"=@(222,$false);'"'=@(222,$true);'*'=@(56,$true)
            }
            $taskMapping=$taskPunctuation[[string]$taskCharacter]
            if(-not $taskMapping){throw 'Unsupported character in fixed console command.'}
            $taskCode=[int]$taskMapping[0];$taskShift=[bool]$taskMapping[1]
        }
        if($taskShift){Invoke-CimMethod -InputObject $taskKeyboard -MethodName PressKey -Arguments @{keyCode=[uint32]16}|Out-Null}
        Lab-Key $taskCode
        if($taskShift){Invoke-CimMethod -InputObject $taskKeyboard -MethodName ReleaseKey -Arguments @{keyCode=[uint32]16}|Out-Null}
        Start-Sleep -Milliseconds 35
    }
}
while([DateTimeOffset]::UtcNow -lt $taskUntil) {
    if(Test-Path -LiteralPath $taskRequest) {
        $taskAction = Get-Content -LiteralPath $taskRequest -Raw | ConvertFrom-Json
        if($taskAction.Nonce -ne $taskLastNonce) {
            $taskLastNonce=$taskAction.Nonce
            try {
                switch($taskAction.Action) {
                    'snapshot' { $taskDetails=Capture-LabFrame }
                    'test-console' {
                        Invoke-CimMethod -InputObject $taskKeyboard -MethodName Reset | Out-Null
                        Lab-Text 'echo LAB_CONSOLE_OK'
                        Lab-Key 13
                        Start-Sleep -Seconds 1
                        $taskDetails=Capture-LabFrame
                    }
                    'recover-live-ssh' {
                        # Fixed recovery operation, exclusively in this VM's live root console.
                        $taskCommand="install -d -m700 /root/.ssh; cp /run/arch-lab/authorized-key.pub /root/.ssh/authorized_keys; chmod 600 /root/.ssh/authorized_keys; usermod -p '*NP*' root; mkdir -p /etc/ssh/sshd_config.d; printf 'PermitRootLogin prohibit-password\nPasswordAuthentication no\n' > /etc/ssh/sshd_config.d/00-lab-recovery.conf; systemctl restart sshd"
                        Lab-Text $taskCommand
                        Lab-Key 13
                        Start-Sleep -Seconds 2
                        $taskDetails=Capture-LabFrame
                    }
                    'enter' { Lab-Key 13; Start-Sleep -Seconds 1; $taskDetails=Capture-LabFrame }
                    'finalize' {
                        foreach($taskDrive in @(Get-VMDvdDrive -VMName $taskConfig.VMName)){Set-VMDvdDrive -VMDvdDrive $taskDrive -Path $null}
                        if(-not(Get-VMSnapshot -VMName $taskConfig.VMName | Where-Object{$_.Name -eq 'Arch instalado e laboratorio validado'})){
                            Checkpoint-VM -Name $taskConfig.VMName -SnapshotName 'Arch instalado e laboratorio validado' | Out-Null
                        }
                        $taskDetails=@{Finalized=$true;VMState=(Get-VM -Name $taskConfig.VMName).State.ToString()}
                    }
                    'quit' { $taskDetails=@{Stopped=$true} }
                    default { throw 'Only fixed laboratory operations are supported.' }
                }
                [pscustomobject]@{Nonce=$taskLastNonce;Success=$true;Action=$taskAction.Action;Details=$taskDetails} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $taskResponse -Encoding utf8
                if($taskAction.Action -eq 'quit'){break}
            } catch {
                [pscustomobject]@{Nonce=$taskLastNonce;Success=$false;Error=$_.Exception.Message} | ConvertTo-Json | Set-Content -LiteralPath $taskResponse -Encoding utf8
            }
        }
    }
    Start-Sleep -Seconds 1
}
