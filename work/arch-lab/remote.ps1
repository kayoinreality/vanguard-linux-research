param([Parameter(Mandatory=$true)][string]$RemoteCommand)
$ErrorActionPreference = 'Stop'
$taskRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$taskConfig = Get-Content (Join-Path $taskRoot 'outputs\arch-lab\config.json') -Raw | ConvertFrom-Json
$taskKnownHosts = Join-Path $taskRoot 'outputs\arch-lab\known_hosts'
$taskAddress = (Get-NetNeighbor -AddressFamily IPv4 | Where-Object { ($_.LinkLayerAddress -replace '-','') -eq '00155D010300' -and $_.State -ne 'Unreachable' } | Select-Object -First 1).IPAddress
if (-not $taskAddress) { $taskAddress = '192.0.2.10' }
$taskSSHOptions = @('-i',[string]$taskConfig.SSHKey,'-o','BatchMode=yes','-o','ConnectTimeout=8','-o','StrictHostKeyChecking=yes','-o',('UserKnownHostsFile='+$taskKnownHosts),'-o',('HostKeyAlias='+$taskConfig.InstanceId+'-installed'))
& ssh.exe @taskSSHOptions ('lab@'+$taskAddress) $RemoteCommand
exit $LASTEXITCODE
