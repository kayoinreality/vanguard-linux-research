# Contratos declarados do League Client no laboratório Arch

**Resultado:** os dois arquivos analisados continuam sendo executáveis Windows x64. `LeagueClientUx.exe` declara integração nativa com CEF; `LeagueClient.exe` declara integração com bibliotecas Riot, atualização e Direct3D. Isso delimita dependências separadas da interface JavaScript do Riot Client que o laboratório informou ter adaptado para Electron/Linux. Esta coleta não examinou nem validou aquela adaptação.

## Evidência estática

Foram lidos somente `LeagueClient.exe` e `LeagueClientUx.exe` no diretório `/home/lab/lol-lab/prefix/drive_c/Riot Games/League of Legends`. Um coletor próprio usou `pefile` para interpretar cabeçalhos PE, tabelas de importação ordinária e adiadas, e calcular SHA-256 sobre os mesmos bytes analisados. Nenhum executável do cliente foi carregado ou executado por esta tarefa.

| Arquivo | Formato | Bytes | Módulos / símbolos ordinários | Módulos adiados |
|---|---|---:|---:|---:|
| `LeagueClient.exe` | PE32+, AMD64, Windows GUI | 30.936.512 | 32 / 758 | 0 |
| `LeagueClientUx.exe` | PE32+, AMD64, Windows GUI | 4.731.320 | 26 / 652 | 0 |

Os metadados de tamanho e modificação permaneceram iguais antes e depois de cada leitura. O parser não reportou avisos. Essa checagem reduz a possibilidade de leitura concorrente inconsistente, mas não equivale a um snapshot do sistema de arquivos. Os caminhos foram mantidos pela coordenação durante a migração; o coletor não modificou mounts nem cópias do jogo.

| Arquivo | SHA-256 dos bytes públicos do executável |
|---|---|
| `LeagueClient.exe` | `e1c9fdae2f29f5f8bd94fda4b5168850989cb06fd651aeb5739faaa701f5e09c` |
| `LeagueClientUx.exe` | `bb49893101079d3eb7bd4bc90a5ba22d69be451fc560174461d5b043ee7b5d0d` |

O JSON acompanhante contém todas as importações coletadas, o horário UTC, a versão do parser e os metadados de consistência. Os hashes identificam estas amostras; não constituem verificação de autenticidade ou assinatura.

## Dependências e efeitos sobre um port

As interpretações da última coluna são **inferências de engenharia**, limitadas pelos nomes declarados e pela documentação das APIs. Não afirmam que os símbolos foram chamados.

| Contrato | Evidência nominal realmente presente | Implicação a investigar |
|---|---|---|
| **Host CEF e comunicação de processos** | Em `LeagueClientUx.exe`, 54 símbolos de `libcef.dll`, incluindo `cef_initialize`, `cef_run_message_loop`, `cef_browser_host_create_browser`, `cef_process_message_create` e `cef_api_hash`. | O host possui uma fronteira nativa de integração com o navegador. Reutilizar conteúdo web em Linux exigiria satisfazer os contratos da aplicação com esse host. A versão exata do CEF não foi determinada. |
| **Integração Riot e atualização** | Em `LeagueClient.exe`, `RiotGamesApi.dll`: `ConnectRiotClient`, `LaunchRiotClient`, `CreateRiotGamesApi`; `rpatch.dll`: `rp_check`, `rp_patch`, `rp_create_session`. | Os nomes sugerem contratos de integração e atualização a inventariar separadamente. As assinaturas, os formatos de dados, a semântica e os destinos dessas funções não foram extraídos. |
| **Runtime e ABI C/C++ Windows** | Nos dois arquivos: `MSVCP140.dll`, `VCRUNTIME140.dll`, `VCRUNTIME140_1.dll` e módulos `api-ms-win-crt-*`. | A execução dos PE depende do ambiente de runtime Windows correspondente. Um host Linux recompilado teria outro conjunto de dependências e precisaria preservar os contratos de suas próprias integrações. A lista não informa compilador, flags ou versão exata do runtime. |
| **Janelas e integração com o sistema** | `LeagueClient.exe`: `CreateWindowExA`, `DeviceIoControl`, `OpenServiceW`, `QueryServiceStatus`; `LeagueClientUx.exe`: `CreateWindowExW`, `SetWindowsHookExW`; ambos: `CreateProcessW`, `LoadLibraryW`, `GetProcAddress`, `CreateFileW`. | Há contratos Win32 além de HTML/JavaScript. Uma investigação de port teria de tratar janelas, arquivos, carregamento e integração com serviços/dispositivos conforme o comportamento requerido. Objetos, processos ou dispositivos efetivamente acessados são desconhecidos. |
| **Gráficos** | `LeagueClient.exe` importa `D3D11CreateDevice` de `d3d11.dll`. | A documentação define essa API como criação de um dispositivo Direct3D. O requisito efetivo de renderização, as opções e os feature levels escolhidos pela amostra não foram determinados. A árvore de dependências do CEF também não foi examinada. |
| **Rede e IPC local** | Nos dois arquivos: `WSAStartup`, `WSAEventSelect`, `WSAEnumNetworkEvents`, `CreateNamedPipeW`, `TransactNamedPipe`; em `LeagueClient.exe`: `DnsQuery_A`, `GetAdaptersAddresses`. | Rede externa, IPC CEF e protocolos locais da aplicação são fronteiras distintas. Seria necessário documentar o contrato de cada uma antes de substituir um host. Nomes de pipes, portas, endpoints e mensagens não foram coletados. |
| **Criptografia, certificados e diagnóstico** | Nos dois arquivos: `CryptCreateHash`, `CryptSignHashW`, `CertOpenStore`, `CertFindCertificateInStore`, `MiniDumpWriteDump`. Ambos possuem diretório PE de certificados. | São dependências nominais de operações criptográficas, armazenamento de certificados e diagnóstico. Não identificam algoritmos, chaves, objetos avaliados nem decisões do Vanguard. Nenhuma assinatura foi validada, alterada ou emulada. |

## CEF, backend e JavaScript

A Riot descreveu em **2016 e 2017** uma arquitetura do League Client com apresentação HTML/JavaScript em CEF e uma camada C++ de serviços locais com REST e WebSocket. São descrições históricas, úteis para orientar a divisão de responsabilidades; não provam que cada detalhe daquela implementação permaneça igual nas amostras atuais. [Arquitetura do League Client Update](https://www.riotgames.com/en/news/architecture-league-client-update), [Hextech UI](https://www.riotgames.com/en/news/under-hood-league-client%E2%80%99s-hextech-ui).

A documentação pública de desenvolvedores da Riot ainda define a **League Client API** como protocolos locais entre CEF e uma biblioteca C++ que se comunica com a plataforma. Ela informa que esse serviço não recebe suporte oficial para aplicações de terceiros nem garantias de documentação completa ou aviso de mudanças. Esta tarefa não consultou endpoints. [League Client API](https://support-developer.riotgames.com/hc/en-us/articles/22698698001939-League-of-Legends).

CEF é o framework de navegador incorporado e integração nativa; chamá-lo simplesmente de “backend” esconde essa fronteira. A documentação do CEF separa processo de navegador, renderização/JavaScript e comunicação entre processos. Os símbolos da amostra Ux são compatíveis nominalmente com esse papel, mas a lista não revela o grafo de execução da aplicação. [CEF General Usage](https://chromiumembedded.github.io/cef/general_usage).

Electron também distingue processo principal, renderers e APIs expostas por preload/context bridge. Compartilhar Chromium ou conseguir renderizar o JavaScript não estabelece equivalência entre as integrações nativas do Electron e do CEF. O header atual de `cef_api_hash` documenta versionamento e hashes da API; a presença do símbolo na amostra não informa qual versão foi negociada ou como foi utilizada. [Electron Process Model](https://www.electronjs.org/docs/latest/tutorial/process-model), [CEF API hash](https://github.com/chromiumembedded/cef/blob/master/include/cef_api_hash.h).

**Implicação limitada para Linux:** o CEF possui builds e procedimentos de desenvolvimento para Linux, o que oferece uma base para um host próprio. Isso não converte uma DLL Windows ou os executáveis Riot em componentes Linux. Uma interface já adaptada pode continuar dependendo de backend Windows em Wine; um port integral do League Client exigiria demonstrar os contratos nativos, de integração e de recursos necessários ao seu funcionamento. Nada nesta coleta valida a entrada em partida ou a aceitação do ambiente pelos serviços oficiais. [CEF Branches and Building](https://chromiumembedded.github.io/cef/branches_and_building).

## Limites e próximos estudos independentes da sessão

- Uma importação demonstra uma referência declarada no arquivo, não uma chamada executada, seus argumentos ou sua finalidade.
- O coletor examinou as tabelas ordinária e adiada. A ausência de entradas na segunda não demonstra ausência de carregamento dinâmico; ambos os arquivos importam APIs de carregamento e resolução de símbolos.
- Não houve análise recursiva das DLLs, plugins, recursos web, executáveis auxiliares, proteções ou código desmontado. O comportamento do host CEF, do backend e da interface portada não foi testado.
- A leitura evitou dados de processos, argumentos de autenticação, logs, lockfiles e informações de sessão. Não houve interação com UI ou conta, alteração de executáveis ou operação sobre a migração.
- Uma continuação estática útil seria inventariar separadamente os módulos públicos selecionados e seus recursos, mantendo os hashes das versões comparadas. Testes posteriores com programas próprios poderiam esclarecer os contratos documentados de CEF e Win32 antes de qualquer validação da aplicação real.

A separação entre importações ordinárias, adiadas e tabela de certificados segue a especificação **PE/COFF**. As interpretações do runtime e do dispositivo gráfico usam documentação Microsoft. [PE Format](https://learn.microsoft.com/en-us/windows/win32/debug/pe-format), [C/C++ Runtime Libraries](https://learn.microsoft.com/en-us/cpp/c-runtime-library/crt-library-features?view=msvc-170), [D3D11CreateDevice](https://learn.microsoft.com/en-us/windows/win32/api/d3d11/nf-d3d11-d3d11createdevice).
