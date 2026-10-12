$ErrorActionPreference = 'Stop'
$taskOutput = Join-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) 'outputs\arch-lab'
$taskConfig = Get-Content -LiteralPath (Join-Path $taskOutput 'config.json') -Raw | ConvertFrom-Json
Import-Module Hyper-V
$taskVM = Get-VM -Name $taskConfig.VMName
if ($taskVM.Notes -ne ('Codex Arch laboratory instance ' + $taskConfig.InstanceId)) { throw 'VM ownership mismatch.' }
$taskAdapters = @(Get-VMNetworkAdapter -VMName $taskConfig.VMName | Select-Object Name, MacAddress, IPAddresses, Status)
$taskIPAddress = @($taskAdapters.IPAddresses | Where-Object { $_ -match '^\d+\.\d+\.\d+\.\d+$' -and $_ -notmatch '^(127\.|169\.254\.|0\.)' })
$taskSSH = @()
foreach($taskAddress in $taskIPAddress) {
    $taskSettings = @(& ssh.exe -G -i $taskConfig.SSHKey -o BatchMode=yes -o StrictHostKeyChecking=no -o UserKnownHostsFile=none "lab@$taskAddress" 2>$null | Select-String -Pattern '^(hostname|stricthostkeychecking|userknownhostsfile|identityfile) ' | ForEach-Object { $_.Line })
    $taskProbe = @(& ssh.exe -vv -i $taskConfig.SSHKey -o BatchMode=yes -o ConnectTimeout=5 -o StrictHostKeyChecking=no -o UserKnownHostsFile=none "lab@$taskAddress" 'cat /var/lib/arch-lab/status /var/lib/arch-lab/install-success' 2>&1 | ForEach-Object { $_.ToString() })
    $taskSSH += [pscustomobject]@{Address=$taskAddress;Settings=$taskSettings;ExitCode=$LASTEXITCODE;Output=$taskProbe}
}
[pscustomobject]@{
    State=$taskVM.State.ToString(); CPUUsage=$taskVM.CPUUsage; MemoryAssigned=$taskVM.MemoryAssigned
    Uptime=$taskVM.Uptime.ToString(); Network=$taskAdapters; Probes=$taskSSH
    UpdatedAtUTC=[DateTimeOffset]::UtcNow.ToString('o')
} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $taskOutput 'diagnostico.json') -Encoding utf8
