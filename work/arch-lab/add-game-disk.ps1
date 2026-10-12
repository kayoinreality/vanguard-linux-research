$ErrorActionPreference = 'Stop'
$taskRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$taskResponse = Join-Path $PSScriptRoot 'add-game-disk-result.json'
try {
    Import-Module Hyper-V
    $taskConfig = Get-Content -LiteralPath (Join-Path $taskRoot 'outputs\arch-lab\config.json') -Raw | ConvertFrom-Json
    $taskVM = Get-VM -Name $taskConfig.VMName
    if ($taskVM.Id.ToString() -ne 'd5cb138f-0ae2-4a8c-8cc9-ac75e040f938') { throw 'VM identity mismatch' }
    if ($taskVM.Notes -ne ('Codex Arch laboratory instance ' + $taskConfig.InstanceId)) { throw 'VM ownership mismatch' }
    $taskDiskRoot = [IO.Path]::GetFullPath((Join-Path $taskRoot 'outputs\arch-lab\vm'))
    $taskDiskPath = [IO.Path]::GetFullPath((Join-Path $taskDiskRoot 'lol-data.vhdx'))
    if (-not $taskDiskPath.StartsWith($taskDiskRoot + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Disk path outside laboratory' }
    $taskExisting = @(Get-VMHardDiskDrive -VMName $taskVM.Name)
    foreach ($taskDrive in $taskExisting) {
        $taskCheckedPath = [IO.Path]::GetFullPath($taskDrive.Path)
        if (-not $taskCheckedPath.StartsWith($taskDiskRoot + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Unexpected VM disk path' }
    }
    if (Test-Path -LiteralPath $taskDiskPath) { throw 'Target already exists; refusing to overwrite' }
    if ((Get-PSDrive -Name C).Free -lt 40GB) { throw 'Insufficient host storage margin' }
    $taskController = @(Get-VMScsiController -VMName $taskVM.Name | Where-Object ControllerNumber -eq 0)
    if ($taskController.Count -ne 1) { throw 'Expected SCSI controller missing' }
    $taskLocations = @($taskExisting | Where-Object { $_.ControllerType -eq 'SCSI' -and $_.ControllerNumber -eq 0 } | ForEach-Object ControllerLocation)
    $taskLocations += @(Get-VMDvdDrive -VMName $taskVM.Name | Where-Object { $_.ControllerNumber -eq 0 } | ForEach-Object ControllerLocation)
    $taskSlot = @(0..63 | Where-Object { $_ -notin $taskLocations })[0]
    if ($null -eq $taskSlot) { throw 'No free SCSI slot' }
    $taskSnapshots = @(Get-VMSnapshot -VMName $taskVM.Name | Select-Object Name,Id)
    $taskNewDisk = New-VHD -Path $taskDiskPath -Dynamic -SizeBytes 60GB -LogicalSectorSizeBytes 512 -PhysicalSectorSizeBytes 4096
    Add-VMHardDiskDrive -VMName $taskVM.Name -ControllerType SCSI -ControllerNumber 0 -ControllerLocation $taskSlot -Path $taskDiskPath
    $taskAttached = @(Get-VMHardDiskDrive -VMName $taskVM.Name | Where-Object Path -eq $taskDiskPath)
    if ($taskAttached.Count -ne 1) { throw 'New disk attachment not confirmed' }
    $taskDisk = Get-VHD -Path $taskDiskPath
    [pscustomobject]@{Success=$true; VMName=$taskVM.Name; VMId=$taskVM.Id.ToString(); DiskPath=$taskDiskPath; SizeBytes=$taskDisk.Size; DiskIdentifier=$taskDisk.DiskIdentifier.ToString(); ControllerLocation=$taskSlot; PreservedSnapshots=$taskSnapshots; ExistingDisksUntouched=@($taskExisting.Path)} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $taskResponse -Encoding utf8
} catch {
    [pscustomobject]@{Success=$false; Error=$_.Exception.Message} | ConvertTo-Json | Set-Content -LiteralPath $taskResponse -Encoding utf8
    exit 1
}
