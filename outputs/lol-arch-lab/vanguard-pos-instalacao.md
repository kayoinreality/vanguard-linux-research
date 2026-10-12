# Vanguard no prefixo Wine: arquivos e consulta de estado

Coleta em **12/10/2026, 10:12:40–10:12:48, America/Sao_Paulo**. As marcações UTC completas estão no JSON. Executada como `lab`, UID 1000, no prefixo `/home/lab/lol-lab/prefix`, com `DISPLAY=:99` e `WINEDEBUG=-all`. A versão Wine 11.19 é a informada para este laboratório.

## Resultado observado

Os quatro componentes do Vanguard já estavam presentes durante o download e a instalação oficial do LoL. **Hash, tamanho e versão coincidem com a referência coletada no Windows**. As duas leituras também coincidiram em SHA-256, tamanho e horário de modificação para cada arquivo.

As consultas `wine sc.exe query vgk` e `wine sc.exe query vgc` retornaram código de processo zero e nenhum texto em stderr. O SCM do prefixo reportou os dois serviços como **STOPPED**, com `WIN32_EXIT_CODE=1077 (0x435)`. Isso não valida a execução do Vanguard, o término da instalação do jogo ou sua aceitação pelos serviços oficiais.

| Arquivo | Bytes | FileVersion do PE | Igual à referência | Estável nas duas leituras |
| --- | ---: | --- | --- | --- |
| `vgk.sys` | 109.721.528 | `1.19.1-18+20261001.143443` | Sim | Sim |
| `vgc.exe` | 107.505.544 | `1.19.1-18+20261001.143443` | Sim | Sim |
| `vgm.exe` | 33.861.928 | `1.19.1-18+20261001.143443` | Sim | Sim |
| `vgrl.dll` | 7.930.376 | `1.19.1-18+20261001.143443` | Sim | Sim |

A referência é `work/vanguard-estudo/inventory.json`. A igualdade do hash compara os bytes; a versão foi lida de recursos PE e não substitui validação de execução. O coletor não realizou uma nova verificação Authenticode no Linux.

## Estado reportado pelo Wine

| Serviço | TYPE | STATE | WIN32_EXIT_CODE | SERVICE_EXIT_CODE | Saída do processo de consulta |
| --- | --- | --- | ---: | ---: | ---: |
| `vgk` | `0x1`, categoria SERVICE_KERNEL_DRIVER | `1`, STOPPED | 1077 | 0 | 0 |
| `vgc` | `0x10`, SERVICE_WIN32_OWN_PROCESS | `1`, STOPPED | 1077 | 0 | 0 |

O `sc` do Wine apresenta TYPE e STATE em hexadecimal sem prefixo. Por isso, o texto `TYPE : 10` corresponde a `0x10`, ou 16 decimal. O ramo `query` do código de referência abre o serviço para `SERVICE_QUERY_STATUS` e solicita `QueryServiceStatus`. [Código Wine: sc.c](https://github.com/wine-mirror/wine/blob/master/programs/sc/sc.c).

A Microsoft documenta `sc query` como consulta de estado. Os tipos e estados acima pertencem ao contrato SERVICE_STATUS. [sc query](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/sc-query), [SERVICE_STATUS](https://learn.microsoft.com/en-us/windows/win32/api/winsvc/ns-winsvc-service_status).

1077 é `ERROR_SERVICE_NEVER_STARTED`, descrito como ausência de tentativa de iniciar o serviço desde a última inicialização. Aqui ele é **o valor reportado pelo SCM Wine**, e não uma auditoria do histórico do Windows ou do kernel Linux. `SERVICE_EXIT_CODE=0` não caracteriza sucesso do anticheat: esse campo é significativo para erro específico do serviço quando WIN32_EXIT_CODE indica ERROR_SERVICE_SPECIFIC_ERROR. [Códigos Microsoft 1000–1299](https://learn.microsoft.com/en-us/windows/win32/debug/system-error-codes--1000-1299-), [SERVICE_STATUS](https://learn.microsoft.com/en-us/windows/win32/api/winsvc/ns-winsvc-service_status).

Mesmo um eventual estado RUNNING no SCM Wine precisaria ser interpretado no contexto dessa camada. O código de referência encaminha serviços de driver para `winedevice.exe`; a implementação de `ntoskrnl` carrega imagens nesse ambiente. Isso não equivale ao carregamento de um módulo nativo do kernel Linux. As fontes consultadas são o ramo upstream `master`, sem validar correspondência integral com a compilação Wine 11.19 instalada. [Wine: services.c](https://github.com/wine-mirror/wine/blob/master/programs/services/services.c), [Wine: ntoskrnl.c](https://github.com/wine-mirror/wine/blob/master/dlls/ntoskrnl.exe/ntoskrnl.c).

## SHA-256 observado

| Arquivo | SHA-256 na segunda leitura, igual à primeira e à referência |
| --- | --- |
| `vgk.sys` | `8ba32cfbc4a07fd41a082344e23e312515ffafef0e568ba72e7d33e83b558f13` |
| `vgc.exe` | `c8f330a77351f36e1112d0b94972a735a7747fc33a4aa4735d95f43f01637c51` |
| `vgm.exe` | `55e25cce83c8ec9088b99d1193a7aa750609e69ed8cfc7c758076ec3591de3d9` |
| `vgrl.dll` | `d76344bcda5acba14156b090e037ccc270f15d3571d2c629a83f5f7263be32c0` |

## Escopo da coleta

Foram lidos apenas os caminhos fixos de `vgk.sys`, `vgc.exe`, `vgm.exe` e `vgrl.dll` em `drive_c/Program Files/Riot Vanguard`. Os únicos comandos SCM solicitados foram `query vgk` e `query vgc`. Nenhum comando de início, parada, configuração ou carregamento foi solicitado; não houve ação de UI.

Não foram lidos logs, configurações de cliente, autenticação ou lockfiles. O estado é uma observação daquele intervalo durante a instalação. A presença dos arquivos e o estado SCM não demonstram execução em modo kernel, equivalência com ArchGuard ou consumo de um anticheat alternativo pelo LoL.

O arquivo complementar `vanguard-pos-instalacao.json` preserva horários UTC, as duas leituras, metadados públicos, resultados de comparação e stdout/stderr exatos das duas consultas. Nenhum valor de segredo foi coletado. Os relatórios principais não foram alterados.
