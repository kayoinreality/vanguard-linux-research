$ErrorActionPreference = 'Stop'
$contractPathTask = Join-Path $PSScriptRoot '..\..\outputs\lol-arch-lab\contratos-league-client.json'
$contractDataTask = Get-Content -LiteralPath $contractPathTask -Raw | ConvertFrom-Json

$contractSourcesTask = @(
    @{id='pe_coff'; publisher='Microsoft'; title='PE Format'; url='https://learn.microsoft.com/en-us/windows/win32/debug/pe-format'; scope='File format and ordinary/delay import directories'},
    @{id='riot_architecture_2016'; publisher='Riot Games'; title='The Architecture of the League Client Update'; url='https://www.riotgames.com/en/news/architecture-league-client-update'; scope='Historical architecture, 2016; not a guarantee for the current build'},
    @{id='riot_hextech_2017'; publisher='Riot Games'; title='Under the hood of the League Client Hextech UI'; url='https://www.riotgames.com/en/news/under-hood-league-client%E2%80%99s-hextech-ui'; scope='Historical UI/plugin architecture, 2017'},
    @{id='riot_lcu_api'; publisher='Riot Games Developer Relations'; title='League Client API'; url='https://support-developer.riotgames.com/hc/en-us/articles/22698698001939-League-of-Legends'; scope='Local CEF/C++ protocols and unsupported third-party service status'},
    @{id='cef_general'; publisher='Chromium Embedded Framework'; title='General Usage'; url='https://chromiumembedded.github.io/cef/general_usage'; scope='CEF process model and native/JavaScript boundaries'},
    @{id='cef_api_hash'; publisher='Chromium Embedded Framework'; title='CEF API hash public header'; url='https://github.com/chromiumembedded/cef/blob/master/include/cef_api_hash.h'; scope='Current public API-version/hash contract; target version not identified'},
    @{id='cef_linux'; publisher='Chromium Embedded Framework'; title='Branches and Building'; url='https://chromiumembedded.github.io/cef/branches_and_building'; scope='CEF platform-specific build/distribution procedures'},
    @{id='electron_processes'; publisher='Electron'; title='Process Model'; url='https://www.electronjs.org/docs/latest/tutorial/process-model'; scope='Main/renderer/preload model; does not establish CEF equivalence'},
    @{id='ms_crt'; publisher='Microsoft'; title='C runtime and C++ standard library files'; url='https://learn.microsoft.com/en-us/cpp/c-runtime-library/crt-library-features?view=msvc-170'; scope='Windows C/C++ runtime libraries'},
    @{id='ms_d3d11'; publisher='Microsoft'; title='D3D11CreateDevice'; url='https://learn.microsoft.com/en-us/windows/win32/api/d3d11/nf-d3d11-d3d11createdevice'; scope='Public graphics-device API contract'}
)

$contractFamiliesTask = @(
    @{id='cef_host'; evidence_kind='declared_imports'; description='Native CEF host boundary'; evidence=@(
        @{file='LeagueClientUx.exe'; module='libcef.dll'; symbols=@('cef_initialize','cef_run_message_loop','cef_browser_host_create_browser','cef_process_message_create','cef_api_hash')}
    ); source_ids=@('cef_general','cef_api_hash'); uncertainty='Exact CEF version, call paths, application bindings and helper process behavior unknown'},
    @{id='riot_and_patching'; evidence_kind='declared_imports'; description='Nominal Riot integration and patching interfaces'; evidence=@(
        @{file='LeagueClient.exe'; module='RiotGamesApi.dll'; symbols=@('ConnectRiotClient','LaunchRiotClient','CreateRiotGamesApi')},
        @{file='LeagueClient.exe'; module='rpatch.dll'; symbols=@('rp_check','rp_patch','rp_create_session')}
    ); source_ids=@('riot_architecture_2016','riot_hextech_2017'); uncertainty='Names do not establish signatures, data models, destinations or executed behavior'},
    @{id='windows_cpp_runtime'; evidence_kind='declared_modules'; description='Windows C/C++ runtime ABI dependencies'; evidence=@(
        @{file='LeagueClient.exe'; modules=@('MSVCP140.dll','VCRUNTIME140.dll','VCRUNTIME140_1.dll')},
        @{file='LeagueClientUx.exe'; modules=@('MSVCP140.dll','VCRUNTIME140.dll','VCRUNTIME140_1.dll')}
    ); source_ids=@('ms_crt'); uncertainty='Compiler flags and exact runtime version not determined'},
    @{id='win32_integration'; evidence_kind='declared_imports'; description='Windows system integration'; evidence=@(
        @{file='LeagueClient.exe'; module='KERNEL32.dll'; symbols=@('CreateProcessW','LoadLibraryW','GetProcAddress','CreateFileW','DeviceIoControl')},
        @{file='LeagueClient.exe'; module='ADVAPI32.dll'; symbols=@('OpenServiceW','QueryServiceStatus')},
        @{file='LeagueClient.exe'; module='USER32.dll'; symbols=@('CreateWindowExA')},
        @{file='LeagueClientUx.exe'; module='USER32.dll'; symbols=@('CreateWindowExW','SetWindowsHookExW')},
        @{file='LeagueClientUx.exe'; module='KERNEL32.dll'; symbols=@('CreateProcessW','LoadLibraryW','GetProcAddress','CreateFileW')}
    ); source_ids=@('pe_coff'); uncertainty='Actual targets, access modes and runtime DLL resolution were not collected'},
    @{id='graphics'; evidence_kind='declared_imports'; description='Direct3D device contract'; evidence=@(
        @{file='LeagueClient.exe'; module='d3d11.dll'; symbols=@('D3D11CreateDevice')}
    ); source_ids=@('ms_d3d11'); uncertainty='No chosen feature level or device options determined; CEF dependency graph not inspected'},
    @{id='network_and_ipc'; evidence_kind='declared_imports'; description='Nominal network and local communication dependencies'; evidence=@(
        @{file='LeagueClient.exe'; module='WS2_32.dll'; symbols=@('WSAStartup','WSAEventSelect','WSAEnumNetworkEvents')},
        @{file='LeagueClientUx.exe'; module='WS2_32.dll'; symbols=@('WSAStartup','WSAEventSelect','WSAEnumNetworkEvents')},
        @{file='LeagueClient.exe'; module='KERNEL32.dll'; symbols=@('CreateNamedPipeW','TransactNamedPipe')},
        @{file='LeagueClientUx.exe'; module='KERNEL32.dll'; symbols=@('CreateNamedPipeW','TransactNamedPipe')},
        @{file='LeagueClient.exe'; module='DNSAPI.dll'; symbols=@('DnsQuery_A')},
        @{file='LeagueClient.exe'; module='IPHLPAPI.DLL'; symbols=@('GetAdaptersAddresses')}
    ); source_ids=@('riot_lcu_api','cef_general'); uncertainty='No endpoints, pipe names, ports, runtime messages or authentication inspected'},
    @{id='crypto_and_diagnostics'; evidence_kind='declared_imports'; description='Nominal cryptographic, certificate and diagnostic APIs'; evidence=@(
        @{file='LeagueClient.exe'; module='ADVAPI32.dll'; symbols=@('CryptCreateHash','CryptSignHashW')},
        @{file='LeagueClientUx.exe'; module='ADVAPI32.dll'; symbols=@('CryptCreateHash','CryptSignHashW')},
        @{file='LeagueClient.exe'; module='CRYPT32.dll'; symbols=@('CertOpenStore','CertFindCertificateInStore')},
        @{file='LeagueClientUx.exe'; module='CRYPT32.dll'; symbols=@('CertOpenStore','CertFindCertificateInStore')},
        @{file='LeagueClient.exe'; module='dbghelp.dll'; symbols=@('MiniDumpWriteDump')},
        @{file='LeagueClientUx.exe'; module='dbghelp.dll'; symbols=@('MiniDumpWriteDump')}
    ); source_ids=@('pe_coff'); uncertainty='No algorithms, keys, signature validation or Vanguard decision inferred'}
)

$verifiedExamplesTask = 0
foreach ($familyTask in $contractFamiliesTask) {
    foreach ($evidenceTask in $familyTask.evidence) {
        $imageTask = @($contractDataTask.files | Where-Object { $_.name -eq $evidenceTask.file })
        if ($imageTask.Count -ne 1) { throw 'Evidence file mismatch' }
        if ($evidenceTask.ContainsKey('modules')) {
            foreach ($moduleTask in $evidenceTask.modules) {
                if ($moduleTask -notin $imageTask[0].ordinary_imports.module) { throw 'Module evidence mismatch' }
                $verifiedExamplesTask++
            }
        } else {
            $importsTask = @($imageTask[0].ordinary_imports | Where-Object { $_.module -eq $evidenceTask.module })
            if ($importsTask.Count -ne 1) { throw 'Import module evidence mismatch' }
            foreach ($symbolTask in $evidenceTask.symbols) {
                if ($symbolTask -notin $importsTask[0].symbols) { throw 'Symbol evidence mismatch' }
                $verifiedExamplesTask++
            }
        }
    }
}

$contractDataTask | Add-Member -NotePropertyName documentation_reviewed_at_utc -NotePropertyValue ([DateTime]::UtcNow.ToString('o')) -Force
$contractDataTask | Add-Member -NotePropertyName primary_sources -NotePropertyValue $contractSourcesTask -Force
$contractDataTask | Add-Member -NotePropertyName contract_families -NotePropertyValue $contractFamiliesTask -Force
$contractDataTask | Add-Member -NotePropertyName evidence_validation -NotePropertyValue @{examples_checked_by_file_and_module=$verifiedExamplesTask; mismatches=0} -Force
$contractDataTask | Add-Member -NotePropertyName laboratory_context -NotePropertyValue @{
    status='Reported by coordinating agent; not inspected in this collection'
    note='Riot Client JavaScript UI adapted to Electron/Linux with a Wine backend is outside the two PE image scope'
    path_migration='Coordinating agent maintains the same guest path through copy/bind migration; this collector did not modify mounts'
} -Force
$contractDataTask | Add-Member -NotePropertyName port_analysis -NotePropertyValue @{
    status='Limited engineering inference; no port or runtime validation performed'
    findings=@(
        'LeagueClientUx.exe declares a native CEF interface; UI JavaScript alone does not capture all host contracts',
        'The League client images and an adapted Riot Client dashboard are distinct investigation scopes',
        'CEF Linux builds offer a host implementation option; Windows PE images remain Windows images',
        'Full native compatibility would require satisfying application-specific integration contracts beyond renderer content',
        'This collection establishes neither gameplay compatibility nor acceptance by official services'
    )
} -Force
$contractJsonTask = $contractDataTask | ConvertTo-Json -Depth 30
[IO.File]::WriteAllText($contractPathTask, $contractJsonTask, (New-Object Text.UTF8Encoding($false)))
[pscustomobject]@{families=$contractFamiliesTask.Count; primary_sources=$contractSourcesTask.Count; verified_examples=$verifiedExamplesTask; mismatches=0} | ConvertTo-Json
