$ErrorActionPreference = 'Stop'
$taskOutputRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$taskConfig = Get-Content (Join-Path $taskOutputRoot 'arch-lab\config.json') -Raw | ConvertFrom-Json
$taskKnownHosts = Join-Path $taskOutputRoot 'arch-lab\known_hosts'
$taskAddress = (Get-NetNeighbor -AddressFamily IPv4 | Where-Object { ($_.LinkLayerAddress -replace '-','') -eq '00155D010300' -and $_.State -ne 'Unreachable' } | Select-Object -First 1).IPAddress
if (-not $taskAddress) { $taskAddress = '192.0.2.10' }
$taskSSHOptions=@('-i',[string]$taskConfig.SSHKey,'-o','BatchMode=yes','-o','ConnectTimeout=8','-o','StrictHostKeyChecking=yes','-o',('UserKnownHostsFile='+$taskKnownHosts),'-o',('HostKeyAlias='+$taskConfig.InstanceId+'-installed'))
& ssh.exe @taskSSHOptions ('lab@'+$taskAddress) 'bash /home/lab/lol-lab/start-native-lab.sh'
if ($LASTEXITCODE -ne 0) { throw 'Não foi possível iniciar a interface do laboratório.' }
$taskPortActive = Get-NetTCPConnection -LocalAddress '127.0.0.1' -LocalPort 16081 -State Listen -ErrorAction SilentlyContinue
if (-not $taskPortActive) {
    $taskTunnelArgs = $taskSSHOptions + @('-o','ExitOnForwardFailure=yes','-N','-L','127.0.0.1:16081:127.0.0.1:6081',('lab@'+$taskAddress))
    Start-Process -FilePath ssh.exe -ArgumentList $taskTunnelArgs -WindowStyle Hidden | Out-Null
}
Write-Host 'Interface do laboratório disponível em:'
Write-Host 'http://127.0.0.1:16081/vnc.html?autoconnect=true&resize=scale'
