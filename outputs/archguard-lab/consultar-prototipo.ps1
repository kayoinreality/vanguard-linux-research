$ErrorActionPreference = 'Stop'
$taskVMFolder = Join-Path (Split-Path $PSScriptRoot -Parent) 'arch-lab'
$taskConfig = Get-Content -LiteralPath (Join-Path $taskVMFolder 'config.json') -Raw | ConvertFrom-Json
$taskVMState = Get-Content -LiteralPath (Join-Path $taskVMFolder 'status.json') -Raw | ConvertFrom-Json
$taskAddress = [string]$taskVMState.Details.Address
$taskNeighbors = @(Get-NetNeighbor -AddressFamily IPv4 -ErrorAction SilentlyContinue | Where-Object { ($_.LinkLayerAddress -replace '[-:]','') -eq $taskVMState.Details.MacAddress })
if($taskNeighbors.Count -eq 1){$taskAddress=[string]$taskNeighbors[0].IPAddress}
$taskResponse = @(& ssh.exe -i $taskConfig.SSHKey -o BatchMode=yes -o ConnectTimeout=8 -o StrictHostKeyChecking=yes -o ('UserKnownHostsFile='+(Join-Path $taskVMFolder 'known_hosts')) -o ('HostKeyAlias='+$taskConfig.InstanceId+'-installed') ('lab@'+$taskAddress) 'python /opt/archguard-lab/archguard.py check')
$taskClientExit = $LASTEXITCODE
if($taskClientExit -notin 0,3){throw 'Nao foi possivel consultar o servico. Confira se a VM esta ligada.'}
$taskState = ($taskResponse -join "`n") | ConvertFrom-Json
Write-Host ('ArchGuard Lab '+$taskState.version)
Write-Host ('Servico: '+$(if($taskState.health -eq 'running'){'ativo'}else{'desatualizado'}))
Write-Host ('Integridade: '+$(if($taskState.integrity -eq 'clean'){'integra'}else{'alerta'}))
$taskDisplayTime=[TimeZoneInfo]::ConvertTime([DateTimeOffset]$taskState.checked_at,[TimeZoneInfo]::FindSystemTimeZoneById('E. South America Standard Time'))
Write-Host ('Ultima verificacao: '+$taskDisplayTime.ToString('dd/MM/yyyy HH:mm:ss')+' (Sao Paulo)')
$taskState.files | Select-Object name,state,bytes | Format-Table
