param([switch]$NoStart)
$ErrorActionPreference = 'Stop'
$taskLabRoot = $PSScriptRoot
$taskConfigPath = Join-Path $taskLabRoot 'config.json'
$taskStatusPath = Join-Path $taskLabRoot 'status.json'
$taskConfig = Get-Content -LiteralPath $taskConfigPath -Raw | ConvertFrom-Json

function Save-LabStatus([string]$Stage, [string]$Message, $Details) {
    [pscustomobject]@{
        Stage=$Stage; Message=$Message; UpdatedAtUTC=[DateTimeOffset]::UtcNow.ToString('o')
        VMName=$taskConfig.VMName; InstanceId=$taskConfig.InstanceId; Details=$Details
    } | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $taskStatusPath -Encoding utf8
}

try {
    $taskPrincipal = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
    if (-not $taskPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw 'O Hyper-V exige executar este arquivo como administrador neste computador.'
    }
    Start-Transcript -Path (Join-Path $taskLabRoot 'host-setup.log') -Append | Out-Null
    Import-Module Hyper-V -ErrorAction Stop
    foreach ($taskMedia in @($taskConfig.ArchISO, $taskConfig.SeedISO)) {
        $taskObserved = (Get-FileHash -LiteralPath $taskMedia.Path -Algorithm SHA256).Hash
        if ($taskObserved -ne $taskMedia.SHA256) { throw ('Hash divergente: ' + $taskMedia.Path) }
    }
    $taskVMName = [string]$taskConfig.VMName
    $taskOwnerNote = 'Codex Arch laboratory instance ' + $taskConfig.InstanceId
    $taskVmRoot = [IO.Path]::GetFullPath((Join-Path $taskLabRoot 'vm'))
    $taskDiskPath = [IO.Path]::GetFullPath((Join-Path $taskVmRoot 'arch-lab.vhdx'))
    if (-not $taskDiskPath.StartsWith($taskVmRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'O caminho do disco virtual saiu da pasta do laboratorio.'
    }
    $taskExisting = Get-VM -Name $taskVMName -ErrorAction SilentlyContinue
    if ($taskExisting) {
        if ($taskExisting.Notes -ne $taskOwnerNote) { throw 'Ja existe uma VM com esse nome, sem a marca deste laboratorio.' }
        $taskDisks = @(Get-VMHardDiskDrive -VMName $taskVMName)
        if ($taskDisks.Count -ne 1) {
            throw 'A VM existente nao possui o unico VHDX previsto.'
        }
        # A checkpoint replaces the active path with an AVHDX. Verify its
        # complete parent chain, confined to this VM directory, to our base.
        $taskCurrentDisk = [IO.Path]::GetFullPath($taskDisks[0].Path)
        $taskVisitedDisks = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
        while ($taskCurrentDisk -ne $taskDiskPath) {
            if (-not $taskCurrentDisk.StartsWith($taskVmRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
                throw 'A cadeia do disco virtual saiu da pasta deste laboratorio.'
            }
            if (-not $taskVisitedDisks.Add($taskCurrentDisk) -or $taskVisitedDisks.Count -gt 64) {
                throw 'A cadeia de checkpoints do disco virtual e invalida.'
            }
            $taskParentDisk = (Get-VHD -Path $taskCurrentDisk -ErrorAction Stop).ParentPath
            if (-not $taskParentDisk) { throw 'O disco da VM nao deriva do VHDX base previsto.' }
            $taskCurrentDisk = [IO.Path]::GetFullPath($taskParentDisk)
        }
    } else {
        if (Test-Path -LiteralPath $taskDiskPath) { throw 'Existe um VHDX sem VM correspondente; nenhuma sobrescrita sera feita.' }
        $taskSwitchId = [Guid]'c08cb7b8-9b3c-408e-8e30-5e16a3aeb444'
        $taskSwitch = Get-VMSwitch | Where-Object { $_.Id -eq $taskSwitchId }
        if (-not $taskSwitch) { throw 'O switch NAT padrao do Hyper-V nao esta disponivel. Nenhuma rede fisica foi alterada.' }
        New-Item -ItemType Directory -Path $taskVmRoot -Force | Out-Null
        New-VM -Name $taskVMName -Generation 2 -MemoryStartupBytes 2GB -NewVHDPath $taskDiskPath -NewVHDSizeBytes 50GB -Path $taskVmRoot -SwitchName $taskSwitch.Name | Out-Null
        Set-VM -Name $taskVMName -Notes $taskOwnerNote -AutomaticStartAction Nothing -AutomaticStopAction ShutDown -CheckpointType Standard -AutomaticCheckpointsEnabled $false
        Set-VMProcessor -VMName $taskVMName -Count 4
        Set-VMMemory -VMName $taskVMName -DynamicMemoryEnabled $true -MinimumBytes 2GB -StartupBytes 2GB -MaximumBytes 4GB
        Add-VMDvdDrive -VMName $taskVMName -Path $taskConfig.ArchISO.Path | Out-Null
        Add-VMDvdDrive -VMName $taskVMName -Path $taskConfig.SeedISO.Path | Out-Null
        $taskDisk = Get-VMHardDiskDrive -VMName $taskVMName
        $taskDvd = @(Get-VMDvdDrive -VMName $taskVMName | Where-Object { $_.Path -eq $taskConfig.ArchISO.Path })[0]
        Set-VMFirmware -VMName $taskVMName -EnableSecureBoot Off -BootOrder $taskDisk, $taskDvd
    }
    if ((Get-VM -Name $taskVMName).State -eq 'Off') {
        Set-VMMemory -VMName $taskVMName -DynamicMemoryEnabled $true -MinimumBytes 2GB -StartupBytes 2GB -MaximumBytes 4GB
        Set-VM -Name $taskVMName -AutomaticCheckpointsEnabled $false
    }
    if ($NoStart) {
        Save-LabStatus 'created' 'VM criada; inicializacao ainda nao solicitada.' $null
        exit 0
    }
    if ((Get-VM -Name $taskVMName).State -eq 'Off') { Start-VM -Name $taskVMName | Out-Null }
    Save-LabStatus 'installing' 'Arch iniciou com midia de instalacao automatica; aguardando SSH do sistema instalado.' $null
    $taskKnownHosts = Join-Path $taskLabRoot 'known_hosts'
    $taskLastAddresses = @()
    $taskDeadline = [DateTimeOffset]::UtcNow.AddMinutes(35)
    $taskReady = $false
    while ([DateTimeOffset]::UtcNow -lt $taskDeadline) {
        $taskLastAddresses = @((Get-VMNetworkAdapter -VMName $taskVMName).IPAddresses | Where-Object { $_ -match '^\d+\.\d+\.\d+\.\d+$' -and $_ -notmatch '^(127\.|169\.254\.|0\.)' })
        foreach ($taskAddress in $taskLastAddresses) {
            # Live and installed OS have different host keys. Probe only the IP
            # reported for this owned VM; pin the installed key once ready.
            $taskProbeHosts = Join-Path $taskLabRoot ('probe-' + $taskAddress + '-known_hosts')
            if(Test-Path -LiteralPath $taskKnownHosts) {
                $taskProbe = @(& ssh.exe -i $taskConfig.SSHKey -o BatchMode=yes -o ConnectTimeout=4 -o StrictHostKeyChecking=yes -o "UserKnownHostsFile=$taskKnownHosts" -o "HostKeyAlias=$($taskConfig.InstanceId)-installed" "lab@$taskAddress" 'test -f /var/lib/arch-lab/install-success && cat /var/lib/arch-lab/install-success' 2>$null)
            } else {
                $taskProbe = @(& ssh.exe -i $taskConfig.SSHKey -o BatchMode=yes -o ConnectTimeout=4 -o StrictHostKeyChecking=accept-new -o "UserKnownHostsFile=$taskProbeHosts" "lab@$taskAddress" 'test -f /var/lib/arch-lab/install-success && cat /var/lib/arch-lab/install-success' 2>$null)
                if($LASTEXITCODE -ne 0 -or ($taskProbe -join '') -ne $taskConfig.InstanceId) {
                    # A live ISO key is temporary. Do not reuse it as the installed
                    # system's key; this is a new VM's private bootstrap file.
                    if(Test-Path -LiteralPath $taskProbeHosts){Remove-Item -LiteralPath $taskProbeHosts}
                }
            }
            if ($LASTEXITCODE -eq 0 -and ($taskProbe -join '') -eq $taskConfig.InstanceId) {
                $taskReady = $true
                $taskGuestAddress = $taskAddress
                break
            }
        }
        if ($taskReady) { break }
        Start-Sleep -Seconds 15
    }
    if (-not $taskReady) {
        Save-LabStatus 'attention' 'Ainda nao foi possivel validar SSH do Arch instalado. Consulte o console da VM e os logs antes de repetir a instalacao.' @{Addresses=$taskLastAddresses}
        exit 2
    }
    $taskHostAlias = "$($taskConfig.InstanceId)-installed"
    if (-not (Test-Path -LiteralPath $taskKnownHosts)) {
        $taskHostKey = @(Get-Content -LiteralPath (Join-Path $taskLabRoot ('probe-' + $taskGuestAddress + '-known_hosts')) | Where-Object { $_ -match ' ssh-ed25519 ' })
        if ($taskHostKey.Count -ne 1) { throw 'Nao foi possivel registrar a chave SSH do Arch instalado.' }
        ($taskHostKey[0] -replace '^\S+', $taskHostAlias) | Set-Content -LiteralPath $taskKnownHosts -Encoding ascii
    }
    $taskSshBase = @('-i', [string]$taskConfig.SSHKey, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '-o', 'StrictHostKeyChecking=yes', '-o', "UserKnownHostsFile=$taskKnownHosts", '-o', "HostKeyAlias=$($taskConfig.InstanceId)-installed")
    $taskValidation = @(& ssh.exe @taskSshBase "lab@$taskGuestAddress" 'bash /usr/local/bin/arch-lab-validate' 2>&1)
    $taskValidationExit = $LASTEXITCODE
    $taskValidation | Set-Content -LiteralPath (Join-Path $taskLabRoot 'guest-validation.log') -Encoding utf8
    if ($taskValidationExit -ne 0) { throw 'O sistema instalou, mas os testes de compilacao/analise nao passaram. Consulte guest-validation.log.' }
    $taskManifest = @(& ssh.exe @taskSshBase "lab@$taskGuestAddress" 'pacman -Q' 2>&1)
    if ($LASTEXITCODE -ne 0) { throw 'Nao foi possivel registrar o manifesto de pacotes.' }
    $taskManifest | Set-Content -LiteralPath (Join-Path $taskLabRoot 'guest-packages.txt') -Encoding utf8
    foreach ($taskDrive in @(Get-VMDvdDrive -VMName $taskVMName)) { Set-VMDvdDrive -VMDvdDrive $taskDrive -Path $null }
    $taskCheckpointName = 'Arch instalado e laboratorio validado'
    if (-not (Get-VMSnapshot -VMName $taskVMName | Where-Object { $_.Name -eq $taskCheckpointName })) {
        Checkpoint-VM -Name $taskVMName -SnapshotName $taskCheckpointName | Out-Null
    }
    Save-LabStatus 'ready' 'Arch instalado; SSH, C, Rust e Python validados; checkpoint criado.' @{Address=$taskGuestAddress;User='lab';Validation='guest-validation.log';Manifest='guest-packages.txt'}
} catch {
    Save-LabStatus 'failed' $_.Exception.Message $null
    Write-Error $_.Exception.Message
    exit 1
} finally {
    try { Stop-Transcript | Out-Null } catch {}
}
