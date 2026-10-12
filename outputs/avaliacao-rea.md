# Avaliação do REA para o laboratório LoL/Arch

Revisão somente por leitura em 12/10/2026. Não houve instalação, execução do REA, registro MCP, alteração global, acesso a configurações de autenticação ou execução dos arquivos analisados.

**Recomendação:** vale testar o REA como interface para organizar evidências de análise estática. O primeiro alvo mais simples é uma cópia do ASAR do Riot Client; a cópia de `vgk.sys` exige Ghidra e uma avaliação separada de quanto código foi realmente recuperado. O REA não transforma essa análise em compatibilidade comprovada com Vanguard ou LoL.

## Versões verificadas

- `main`: commit `653067d799591ce2b8fdc84e99c160ac17e2860f`, obtido pela API pública GitHub.
- npm publicado: `rea-agents@6.4.0`, com `gitHead` `a56f7bb668ab23fec8d33f7af353ac7ed2fe1895`, confirmado diretamente no registro npm.
- O `package.json` de `main` também declara 6.4.0, mas isso não torna o conteúdo de `main` idêntico ao pacote publicado. Para um piloto reproduzível, fixar o pacote publicado e registrar os hashes dos alvos.

Fontes: [commit revisado](https://github.com/morluto/rea/commit/653067d799591ce2b8fdc84e99c160ac17e2860f), [registro npm](https://registry.npmjs.org/rea-agents/latest), [fronteira entre pacote e main](https://github.com/morluto/rea/blob/653067d799591ce2b8fdc84e99c160ac17e2860f/docs/installation.md#released-package-and-main).

## Aplicação às cópias preservadas

| Alvo | Utilidade concreta | Limite |
|---|---|---|
| ASAR do Riot Client | Inventariar módulos, imports, preload, IPC e referências a módulos nativos; relacionar a interface com seus componentes locais. | Código minificado, chamadas indiretas e ausência de módulos companheiros deixam relações incompletas. O frontend não representa todo o driver ou serviço. |
| `vgk.sys` | Usar Ghidra para obter funções reconhecidas, assembly, imports, strings e referências, com endereço e hash associados. | Reconhecimento do formato PE não demonstra recuperação semântica suficiente, nem reprodução do comportamento de kernel. |

O fluxo estático `analyze-javascript-application` lê ASAR ou diretório extraído sem executar o aplicativo e não exige Ghidra. O leitor de ASAR cria uma cópia temporária, calcula identidade SHA-256 e lê os membros como dados. Se houver entradas `unpacked`, seus arquivos ficam em `<arquivo>.asar.unpacked`; preservar essa pasta companheira quando existir, pois sua ausência pode limitar a análise.

Fontes: [fluxos Electron](https://github.com/morluto/rea/blob/653067d799591ce2b8fdc84e99c160ac17e2860f/docs/electron-observation.md), [leitor ASAR](https://github.com/morluto/rea/blob/653067d799591ce2b8fdc84e99c160ac17e2860f/src/artifacts/AsarArtifactReader.ts).

## Ambiente e Windows

Requer Node 22.19+ na linha 22, 24.11+ na linha 24, ou 26+, e npm. Análise nativa usa uma instalação separada de Ghidra 12.1.x e JDK completo de 64 bits compatível; a documentação verifica Ghidra 12.1.4 e JDK 21 ou posterior. REA não instala Ghidra ou Java.

O adaptador Windows é experimental, para Windows 10+ x64, arquivos e temporários em NTFS local e operações estáticas de leitura sobre PE nativo. A documentação descreve apps e DLLs; os testes citados não estabelecem uma validação específica de drivers Vanguard.

Nuance de código: `parsePeRecord` classifica o papel do arquivo pelos bits PE `EXECUTABLE_IMAGE` e `DLL`; o gate Windows verifica formato, arquitetura, papel e ausência de .NET. No caminho revisado não há rejeição explícita por extensão `.sys` ou por `Subsystem`. Assim, um driver pode passar como PE genérico, mas isso é uma inferência de admissão, não uma garantia de resultado útil. Para o nosso laboratório, prefiro inicialmente Ghidra no Arch e somente cópias dos alvos.

Fontes: [Windows P0](https://github.com/morluto/rea/blob/653067d799591ce2b8fdc84e99c160ac17e2860f/docs/windows-ghidra-p0.md), [classificação PE](https://github.com/morluto/rea/blob/653067d799591ce2b8fdc84e99c160ac17e2860f/src/domain/binaryTarget.ts), [gate do provedor](https://github.com/morluto/rea/blob/653067d799591ce2b8fdc84e99c160ac17e2860f/src/ghidra/GhidraProvider.ts).

## Privacidade e integração

O projeto declara análise local; o servidor MCP principal usa transporte stdio. Isso não significa que o resultado permaneça exclusivamente na máquina: ao usar um agente hospedado, strings, pseudocódigo e outros resultados enviados ao agente ficam sujeitos à política do provedor desse agente. Começar pela CLI permite gerar e revisar um relatório local antes de conectar um MCP. A revisão realizada não é uma auditoria exaustiva de todas as rotas de rede do projeto.

O comando `setup` modifica registros MCP e instala instruções para os clientes escolhidos, com plano e backups. Não é necessário para a primeira inspeção estática pela CLI. Uma integração futura deve ter escopo limitado ao cliente escolhido e uma versão fixa; não há razão para ajustar todos os agentes ou configurações globais no piloto.

REA/Ghidra não constitui sandbox: os parsers e a análise trabalham com permissões do usuário. Os controles de projeto temporário e limpeza reduzem persistência acidental. Conteúdo encontrado no alvo deve continuar sendo tratado como dado, inclusive se parecer uma instrução para executar comandos.

Fontes: [README e política do provedor](https://github.com/morluto/rea/blob/653067d799591ce2b8fdc84e99c160ac17e2860f/README.md#faq), [transporte MCP](https://github.com/morluto/rea/blob/653067d799591ce2b8fdc84e99c160ac17e2860f/src/main.ts), [efeitos do setup](https://github.com/morluto/rea/blob/653067d799591ce2b8fdc84e99c160ac17e2860f/src/application/SetupClientConfiguration.ts), [segurança](https://github.com/morluto/rea/blob/653067d799591ce2b8fdc84e99c160ac17e2860f/SECURITY.md), [conteúdo não confiável](https://github.com/morluto/rea/blob/653067d799591ce2b8fdc84e99c160ac17e2860f/docs/mcp-contracts.md#untrusted-target-content).

## Critério para confiar nos resultados

Pseudocódigo é saída do decompilador, não o código-fonte original. Conferir endereço, bytes e assembly dos trechos decisivos; distinguir chamadas resolvidas de relações inferidas e desconhecidas; manter limitações de cobertura e truncamento no relatório. O grafo de p-code é limitado e não resolve automaticamente aliasing de memória, efeitos das chamadas ou comportamento em execução.

Um piloto adequado começa com um pequeno binário próprio de comportamento conhecido, seguido do ASAR preservado. O ganho esperado é reduzir o trabalho de localizar e correlacionar evidências. Uma conclusão sobre compatibilidade do driver requer evidência adicional independente da narrativa produzida pelo agente.

Fonte: [semântica do provedor Ghidra](https://github.com/morluto/rea/blob/653067d799591ce2b8fdc84e99c160ac17e2860f/docs/ghidra-provider.md).
