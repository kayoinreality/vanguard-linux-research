"""Archive fixed public metadata collected from the owned lab prefix."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re

root = Path(__file__).resolve().parent.parent.parent
capture = root / "work/vanguard-estudo/guest-vanguard-readonly-capture.json"
data = json.loads(capture.read_text(encoding="utf-8-sig"))
reference = json.loads((root / "work/vanguard-estudo/inventory.json").read_text(encoding="utf-8-sig"))
by_name = {x["Name"]: x for x in reference["Files"]}
for item in data["files"]:
    original = by_name[item["name"]]
    assert original["SHA256"].lower() == item["baseline"]["sha256"]
    assert original["FileVersion"] == item["baseline"]["version"]
    assert original["Bytes"] == item["baseline"]["bytes"]

for query in data["service_queries"]:
    text = query.get("stdout", "")
    parsed = {}
    for field, pattern, base in (
        ("type_value", r"TYPE\s*:\s*([0-9a-fA-F]+)", 16),
        ("state_value", r"STATE\s*:\s*([0-9a-fA-F]+)", 16),
        ("win32_exit_code", r"WIN32_EXIT_CODE\s*:\s*(\d+)", 10),
        ("service_exit_code", r"SERVICE_EXIT_CODE\s*:\s*(\d+)", 10),
    ):
        match = re.search(pattern, text)
        if match:
            parsed[field] = int(match.group(1), base)
    parsed["parsing_note"] = "Wine sc prints TYPE and STATE in hexadecimal without a 0x prefix; exit-code decimal values retained"
    query["parsed_status"] = parsed

data["wine_environment"] = {"WINEPREFIX": "/home/lab/lol-lab/prefix", "WINEDEBUG": "-all", "DISPLAY": ":99", "wine_release_in_task_context": "11.19"}
data["installation_stage"] = "Vanguard files already present while the official LoL download/installation was still ongoing; full game installation was not validated by this collector"
data["baseline_source"] = "work/vanguard-estudo/inventory.json"
data["version_method"] = "PE FileVersion/ProductVersion resource strings; no executable image loading or Authenticode verification by the collector"
output = root / "outputs/lol-arch-lab"
output.mkdir(parents=True, exist_ok=True)
json_path = output / "vanguard-pos-instalacao.json"
json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

local_zone = timezone(timedelta(hours=-3))
started = datetime.fromisoformat(data["started_at_utc"]).astimezone(local_zone)
completed = datetime.fromisoformat(data["completed_at_utc"]).astimezone(local_zone)
rows = []
hash_rows = []
for item in data["files"]:
    version = item.get("version_resources", [{}])[0].get("file_version", "indisponível")
    matching = "Sim" if item.get("matches_baseline_sha256") and item.get("matches_baseline_bytes") and item.get("matches_baseline_version") else "Não confirmado"
    stable = "Sim" if item.get("stable_between_two_reads") else "Não confirmado"
    rows.append(f'| `{item["name"]}` | {item.get("bytes_second", "indisponível"):,}'.replace(",", ".") + f' | `{version}` | {matching} | {stable} |')
    hash_rows.append(f'| `{item["name"]}` | `{item.get("sha256_second", "indisponível")}` |')

report = f'''# Vanguard no prefixo Wine: arquivos e consulta de estado

Coleta em **{started:%d/%m/%Y}, {started:%H:%M:%S}–{completed:%H:%M:%S}, America/Sao_Paulo**. As marcações UTC completas estão no JSON. Executada como `lab`, UID {data["uid"]}, no prefixo `/home/lab/lol-lab/prefix`, com `DISPLAY=:99` e `WINEDEBUG=-all`. A versão Wine 11.19 é a informada para este laboratório.

## Resultado observado

Os quatro componentes do Vanguard já estavam presentes durante o download e a instalação oficial do LoL. **Hash, tamanho e versão coincidem com a referência coletada no Windows**. As duas leituras também coincidiram em SHA-256, tamanho e horário de modificação para cada arquivo.

As consultas `wine sc.exe query vgk` e `wine sc.exe query vgc` retornaram código de processo zero e nenhum texto em stderr. O SCM do prefixo reportou os dois serviços como **STOPPED**, com `WIN32_EXIT_CODE=1077 (0x435)`. Isso não valida a execução do Vanguard, o término da instalação do jogo ou sua aceitação pelos serviços oficiais.

| Arquivo | Bytes | FileVersion do PE | Igual à referência | Estável nas duas leituras |
| --- | ---: | --- | --- | --- |
{chr(10).join(rows)}

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
{chr(10).join(hash_rows)}

## Escopo da coleta

Foram lidos apenas os caminhos fixos de `vgk.sys`, `vgc.exe`, `vgm.exe` e `vgrl.dll` em `drive_c/Program Files/Riot Vanguard`. Os únicos comandos SCM solicitados foram `query vgk` e `query vgc`. Nenhum comando de início, parada, configuração ou carregamento foi solicitado; não houve ação de UI.

Não foram lidos logs, configurações de cliente, autenticação ou lockfiles. O estado é uma observação daquele intervalo durante a instalação. A presença dos arquivos e o estado SCM não demonstram execução em modo kernel, equivalência com ArchGuard ou consumo de um anticheat alternativo pelo LoL.

O arquivo complementar `vanguard-pos-instalacao.json` preserva horários UTC, as duas leituras, metadados públicos, resultados de comparação e stdout/stderr exatos das duas consultas. Nenhum valor de segredo foi coletado. Os relatórios principais não foram alterados.
'''
md_path = output / "vanguard-pos-instalacao.md"
md_path.write_text(report, encoding="utf-8")
print(json.dumps({"json": str(json_path), "report": str(md_path), "files": len(data["files"]), "queries": len(data["service_queries"])}))
