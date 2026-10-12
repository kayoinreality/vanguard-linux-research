$ErrorActionPreference = 'Stop'
$taskHelper = Join-Path $PSScriptRoot 'preparar-vm.ps1'
$taskEngine = 'pwsh.exe'
if (-not (Test-Path -LiteralPath $taskEngine)) { throw 'O PowerShell usado na preparacao nao esta mais disponivel.' }
if (-not (Test-Path -LiteralPath (Join-Path $PSScriptRoot 'config.json'))) { throw 'A configuracao e as midias ainda nao estao prontas.' }
$taskArguments = @('-NoLogo', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', ('"' + $taskHelper + '"'))
Start-Process -FilePath $taskEngine -ArgumentList $taskArguments -Verb RunAs -WindowStyle Hidden | Out-Null
Write-Output 'A criacao da VM foi enviada ao Windows. Autorize a janela UAC para iniciar; acompanhe status.json nesta pasta.'
