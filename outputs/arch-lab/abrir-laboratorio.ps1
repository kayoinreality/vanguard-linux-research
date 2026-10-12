$ErrorActionPreference = 'Stop'
$taskConfig = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'config.json') -Raw | ConvertFrom-Json
$taskState = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'status.json') -Raw | ConvertFrom-Json
if($taskState.Stage -ne 'ready'){throw 'O laboratorio ainda nao consta como validado. Consulte status.json.'}
$taskAddress=[string]$taskState.Details.Address
$taskMac=[string]$taskState.Details.MacAddress
if($taskMac){
    $taskNeighbor=@(Get-NetNeighbor -AddressFamily IPv4 -ErrorAction SilentlyContinue | Where-Object {($_.LinkLayerAddress -replace '[-:]','') -eq $taskMac})
    if($taskNeighbor.Count -eq 1){$taskAddress=[string]$taskNeighbor[0].IPAddress}
}
Write-Host 'Conectando ao Arch Linux do laboratorio. Use exit para sair.'
& ssh.exe -i $taskConfig.SSHKey -o StrictHostKeyChecking=yes -o ('UserKnownHostsFile='+(Join-Path $PSScriptRoot 'known_hosts')) -o ('HostKeyAlias='+$taskConfig.InstanceId+'-installed') ('lab@'+$taskAddress)
if($LASTEXITCODE -ne 0){throw 'A conexao falhou. A VM pode estar desligada ou o endereco pode ter mudado.'}
