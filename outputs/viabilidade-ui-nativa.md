# Auditoria estrutural da interface do Riot Client

Inspeção em 12/10/2026, na VM Arch, sem executar o aplicativo.

**O pacote examinado não apresenta um bloqueio por addons nativos de Windows.** Não há arquivos `.node`, `.dll`, `.exe`, `.so` ou `.dylib` no ASAR, e a pasta `app.asar.unpacked` não existe nesta instalação. Isso sustenta uma tentativa experimental de inicialização com Electron Linux; não comprova que a interface abrirá nem que conseguirá operar com os serviços do Riot Client.

Os resultados completos e os metadados dos 22 arquivos `package.json` estão na [evidência JSON](viabilidade-ui-nativa.json).

| Item | Resultado observado |
|---|---|
| Arquivo | `/home/lab/lol-lab/prefix/drive_c/Riot Games/Riot Client/RiotClientElectron/resources/app.asar` |
| Tamanho | 154.483.710 bytes |
| Cabeçalho ASAR | 102.096 bytes; JSON interpretado sem erro |
| Entradas de arquivo | 374 |
| Metadados de pacotes | 22 `package.json` lidos sem erro |
| Nome e versão do aplicativo | `riot-client-ux`, `140.0.0` |
| Ponto de entrada declarado | `./dist/main/main.js` |
| Ponto de entrada encontrado | `dist/main/main.js`, 2.351.415 bytes, dentro do ASAR |
| `engines`, `os`, `cpu` no pacote principal | Ausentes |
| Restrições declaradas de `os` ou `cpu` nos pacotes examinados | Nenhuma |
| Binários nativos pelas extensões examinadas | Nenhum |
| `app.asar.unpacked` | Ausente |

## Dependências obrigatórias e opcionais

O `package.json` principal declara estas dependências regulares. A classificação abaixo vem dos metadados; não equivale a um rastreamento de carregamento durante a execução.

| Dependência | Versão requerida | Versão empacotada | Classificação declarada |
|---|---|---|---|
| `js-yaml` | `^4.1.0` | `4.3.2` | Regular |
| `ws` | `8.19.0` | `8.19.0` | Regular |
| `yargs` | `^17.4.1` | `17.7.3` | Regular |

`ws` declara `bufferutil` (`^4.0.1`) e `utf-8-validate` (`>=5.0.2`) como peers, ambos com `optional: true` em `peerDependenciesMeta`. Não há pacotes desses nomes nem addons `.node` associados nas entradas examinadas. Portanto, os metadados não exigem esses complementos nativos para instalar este conjunto de dependências.

Os pacotes empacotados que declaram `engines.node` têm requisitos mínimos de até Node 12. O aplicativo principal não informa uma versão de Electron. **`140.0.0` é a versão declarada do aplicativo, não uma identificação comprovada do runtime Electron.**

O Electron exige que módulos nativos sejam compatíveis com a plataforma, arquitetura e ABI do runtime. A ausência desses módulos neste ASAR evita esse tipo específico de dependência no material examinado. [Documentação oficial de módulos nativos](https://www.electronjs.org/docs/latest/tutorial/using-native-node-modules).

## O que permanece sem comprovação

- A versão de Electron Linux compatível com as APIs utilizadas pelo código principal.
- Dependências de serviços, executáveis ou bibliotecas externas ao ASAR. Nenhum componente vizinho foi auditado nesta etapa.
- Caminhos, opções de inicialização e comportamentos condicionados ao sistema operacional dentro do JavaScript. O código do aplicativo não foi lido nem executado.
- A causa do erro `0x80000003` observado na tentativa com Wine e se trocar o runtime resolve essa falha.
- Funcionamento do fluxo completo da interface, do jogo ou do Vanguard.

Há uma entrada `.wasm` no inventário, mas seus imports e requisitos de execução não foram analisados. A ausência de extensões nativas não prova que o pacote inteiro seja independente de plataforma.

## Próximo experimento que os resultados sustentam

Uma execução isolada da interface com Electron Linux é uma hipótese testável. O marco de sucesso deve ser abrir a janela e manter o processo principal e o renderer ativos, identificando eventuais erros de API ou recursos externos. Só depois desse teste será possível afirmar algo sobre a viabilidade operacional da interface. Esta auditoria não realizou essa execução.

O Electron reconhece arquivos dentro de ASAR por meio de um sistema de arquivos virtual, o que permite avaliar o pacote sem presumir que todos os arquivos precisam ser extraídos. [Documentação oficial de ASAR](https://www.electronjs.org/docs/latest/tutorial/asar-archives).

## Método e escopo

Foi usado um script próprio com a biblioteca padrão do Python para interpretar o cabeçalho Pickle/JSON do ASAR, listar entradas e ler somente `package.json`. O cálculo dos offsets seguiu a [implementação oficial do leitor ASAR](https://github.com/electron/asar/blob/main/src/disk.ts). Também foi verificada a existência da pasta de arquivos desempacotados e feita a classificação de extensões potencialmente nativas.

Nenhum arquivo da instalação foi alterado; somente o script de análise próprio foi transferido para a VM. Nenhum código Riot foi executado, nenhuma API foi consultada e nenhum arquivo de autenticação, lockfile ou log privado foi lido.
