# Contrato estático de leitura do Patcher

**Foi confirmado um GET de estado definido no bundle original:** `/patch-proxy/v2/patch-states/products/{productId}/patchlines/{patchlineId}`.

Fonte: `app.asar` original, SHA-256 `5d346edfd1c69648643b2633ac75430db4722ad974b80521ff909759f26b88a6`. Foram lidos somente os bundles públicos `dist/main/main.js` e `dist/renderer/renderer.js`, com um leitor ASAR próprio. [Evidência compacta com nomes e offsets](patcher-get-contrato-estatico.json).

O builder `buildPatchProxyV2PatchStatesURI` é usado por `usePatchStateV2`. Este usa `useTypedDataBinding`, que registra o observador. Sem cache, `addObserver` busca por `get`; as implementações de leitura usam `jsonRequest("get", URI)`. A confirmação é estática; não houve consulta ao backend.

| Endpoint GET | Campos efetivamente lidos pela interface |
|---|---|
| `/patch-proxy/v2/patch-states/products/{productId}/patchlines/{patchlineId}` | `state`, `progress.totalBytesDownloaded`, `progress.totalBytesToDownload`, `progress.overallProgress` |
| `/patch-proxy/v1/patch-states/products/{productId}/patchlines/{patchlineId}` | `combined_patch_state`, `patch_status.state`, `patch_status.progress.phase`, `patch_status.error`, `patch_status.error.code`, `dependency_status`, `repair_code` |

O v2 é consumido com estados como `Paused`, `Updating`, `Repairing`, `DependencyUpdate`, `UpToDate`, `OutOfDate` e `NeedsRepair`. No v1, os dados de progresso usam as categorias `Update`, `Manifest`, `Repair` e `Rechunk`. Para `Update`, a interface lê `patch_status.progress.update.downloaded_bytes` e `bytes_to_download`; os nomes das outras categorias estão no JSON.

Não foi identificado um campo específico de motivo da pausa. O apresentador de erros recebe um argumento `message`, mas o caminho exato de um eventual campo `error.message` na resposta não foi completamente rastreado. Os campos acima são usos observados, não um schema integral confirmado contra a sessão atual.

## Transporte, autenticação local e CA

O parser declara `appPort` como número e `remotingAuthToken` como string. As grafias hifenizadas não aparecem literalmente no main examinado; os nomes camelCase são o contrato diretamente observado do parser.

O cliente HTTP define a base `https://127.0.0.1:{appPort}` e o cabeçalho `Authorization: Basic base64("riot:" + remotingAuthToken)`. O hook de WebSocket usa o mesmo esquema de autenticação e a origem `https://127.0.0.1:{appPort}`. Nenhum valor real de porta ou token foi lido.

**O CA vem do recurso público `dist/main/root.pem` dentro do ASAR.** Na inicialização, o main lê `path.join(__dirname,"root.pem")` e fornece seus bytes a `initHttpClient(ca, cliArgs.appPort, cliArgs.remotingAuthToken)`. O inicializador usa `https.Agent({ca: certificado})`; não foi identificada uma flag de CA necessária nesse caminho. O conteúdo do PEM não foi lido nesta inspeção.

Não houve acesso a argumentos de processos, configurações de autenticação, lockfiles, logs privados, APIs ou UI. Esta análise não diagnostica a causa da atualização estacionada nem valida o handshake TLS da sessão em execução.
