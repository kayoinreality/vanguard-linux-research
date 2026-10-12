$ErrorActionPreference = 'Stop'
$taskRoot = $PSScriptRoot
$taskSamples = Join-Path $taskRoot 'samples'
New-Item -ItemType Directory -Path $taskSamples -Force | Out-Null
$taskTargets = @(
    'C:\Program Files\Riot Vanguard\vgc.exe',
    'C:\Program Files\Riot Vanguard\vgk.sys',
    'C:\Program Files\Riot Vanguard\vgm.exe',
    'C:\Program Files\Riot Vanguard\vgrl.dll',
    'C:\Riot Games\League of Legends\LeagueClient.exe',
    'C:\Riot Games\League of Legends\Game\League of Legends.exe'
)
$taskFiles = @()
foreach ($taskSource in $taskTargets) {
    $taskItem = Get-Item -LiteralPath $taskSource
    $taskSignature = Get-AuthenticodeSignature -LiteralPath $taskSource
    $taskHashBefore = (Get-FileHash -LiteralPath $taskSource -Algorithm SHA256).Hash
    $taskDestination = Join-Path $taskSamples $taskItem.Name
    Copy-Item -LiteralPath $taskSource -Destination $taskDestination
    $taskHashCopy = (Get-FileHash -LiteralPath $taskDestination -Algorithm SHA256).Hash
    $taskHashAfter = (Get-FileHash -LiteralPath $taskSource -Algorithm SHA256).Hash
    if (($taskHashBefore -ne $taskHashCopy) -or ($taskHashAfter -ne $taskHashCopy)) {
        throw ('Source changed during snapshot: ' + $taskItem.Name)
    }
    $taskFiles += [pscustomobject]@{
        Name=$taskItem.Name; Source=$taskSource; Snapshot=$taskDestination
        Bytes=$taskItem.Length; SHA256=$taskHashCopy
        FileVersion=$taskItem.VersionInfo.FileVersion
        ProductVersion=$taskItem.VersionInfo.ProductVersion
        Signature=$taskSignature.Status.ToString()
        Signer=if($taskSignature.SignerCertificate){$taskSignature.SignerCertificate.Subject}else{$null}
    }
}
$taskSecureBoot = try {
    [pscustomobject]@{ Status='Measured'; Enabled=(Confirm-SecureBootUEFI -ErrorAction Stop) }
} catch {
    [pscustomobject]@{ Status='Unavailable'; Reason=$_.Exception.Message }
}
$taskTpm = try {
    $taskTpmValue = Get-Tpm -ErrorAction Stop
    if ($null -eq $taskTpmValue -or $null -eq $taskTpmValue.TpmPresent) {
        [pscustomobject]@{ Status='Unavailable'; Reason='No readable TPM status returned' }
    } else {
        [pscustomobject]@{ Status='Measured'; Present=$taskTpmValue.TpmPresent; Ready=$taskTpmValue.TpmReady }
    }
} catch {
    [pscustomobject]@{ Status='Unavailable'; Reason=$_.Exception.Message }
}
$taskSecureBootRegistry = try {
    [pscustomobject]@{
        Source='HKLM:\SYSTEM\CurrentControlSet\Control\SecureBoot\State\UEFISecureBootEnabled'
        Value=(Get-ItemPropertyValue -LiteralPath 'HKLM:\SYSTEM\CurrentControlSet\Control\SecureBoot\State' -Name UEFISecureBootEnabled -ErrorAction Stop)
        Note='Registry-reported state; the direct UEFI query is recorded separately.'
    }
} catch {
    [pscustomobject]@{ Source='SecureBoot registry'; Error=$_.Exception.Message }
}
$taskInventory = [pscustomobject]@{
    CollectedAtUTC=[DateTimeOffset]::UtcNow.ToString('o')
    Board=@(Get-CimInstance Win32_BaseBoard | Select-Object Manufacturer, Product, Version)
    CPU=@(Get-CimInstance Win32_Processor | Select-Object Name, NumberOfCores, NumberOfLogicalProcessors)
    GPU=@(Get-CimInstance Win32_VideoController | Select-Object Name, DriverVersion)
    BIOS=@(Get-CimInstance Win32_BIOS | Select-Object SMBIOSBIOSVersion, ReleaseDate)
    OS=@(Get-CimInstance Win32_OperatingSystem | Select-Object Caption, Version, BuildNumber)
    RAMGiB=[math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB, 1)
    HypervisorPresent=(Get-CimInstance Win32_ComputerSystem).HypervisorPresent
    SecureBoot=$taskSecureBoot
    SecureBootRegistry=$taskSecureBootRegistry
    TPM=$taskTpm
    VanguardService=@(Get-CimInstance Win32_Service -Filter "Name='vgc'" | Select-Object Name, State, StartMode, PathName)
    VanguardDriver=@(Get-CimInstance Win32_SystemDriver -Filter "Name='vgk'" | Select-Object Name, State, StartMode, PathName)
    UserReport='League of Legends and Vanguard installed and working on Windows; Arch not yet installed.'
    Files=$taskFiles
}
$taskInventory | ConvertTo-Json -Depth 7 | Set-Content -LiteralPath (Join-Path $taskRoot 'inventory.json') -Encoding utf8
[pscustomobject]@{ Snapshots=$taskFiles.Count; HashesMatch=$true; Inventory=(Join-Path $taskRoot 'inventory.json') } | ConvertTo-Json
