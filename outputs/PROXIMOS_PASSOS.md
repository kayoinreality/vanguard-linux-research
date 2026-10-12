# Próximos passos para retomar a pesquisa

Este roteiro conserva o layout existente `outputs/` e `work/`. Não acrescenta uma segunda cópia do ArchGuard nem distribui componentes Riot.

## Estado que deve orientar a retomada

- ArchGuard Lab 0.1: serviço original em espaço de usuário, socket Unix e integridade de fixture próprio; os 18 testes são um resultado histórico do laboratório.
- Riot Client: interface original iniciada com Electron nativo no Linux, mantendo backend Windows sob Wine. Isso não constitui um port integral.
- Jogo: na retomada, GET v2 confirmou avanço de bytes em etapas de atualização. `Play` mostrou a escolha inicial de região; Brasil/português foram aplicados e o cliente voltou a atualizar. Instalação, abertura e entrada em partida ainda não foram validadas como fluxo completo. Veja [a evidência da retomada](lol-arch-lab/retomada-download.md).
- Vanguard: arquivos e trechos foram estudados estaticamente; não há driver nativo Linux ou substituto do Vanguard implementado. A integração com ArchGuard permanece sem demonstração.

## Ordem e critérios de conclusão

| Marco | Trabalho útil | Evidência necessária para concluir |
|---|---|---|
| Ambiente próprio | Recuperar acesso ao laboratório e revisar dependências locais | Estado da VM e execução dos testes próprios, sem publicar configuração de acesso |
| Atualização | Diagnosticar o estado real do Patcher antes de atribuir uma causa ou solicitar nova tentativa | Resposta técnica de estado/progresso, com versão e horário; campos públicos selecionados e nenhum dado de sessão |
| Instalação | Confirmar presença e integridade dos arquivos esperados | Inventário de metadados e hashes; arquivos presentes não equivalem a execução |
| Lançamento | Observar separadamente solicitação e resultado da abertura do aplicativo | Resultado verificável da tentativa e erro explícito, quando houver; não inferir partida de uma interface aberta |
| Partida | Validar o fluxo completo apenas quando os marcos anteriores estiverem atendidos | Resultado real da entrada em partida; nenhuma conclusão foi obtida nessa etapa do estudo |
| Contratos próprios | Ampliar o ArchGuard com requisitos e dados escolhidos para o laboratório | Testes de comportamento, erro e recuperação próprios; sucesso não comprova consumo pelo cliente Riot |
| REA | Testar a análise estática num binário próprio conhecido e no ASAR; avaliar depois a cópia do driver com Ghidra | Versão fixa, hash do alvo, endereços, assembly e limitações dos resultados; veja [a avaliação](avaliacao-rea.md) |

O diagnóstico estático do Patcher encontra-se em [patcher-get-contrato-estatico.md](patcher-get-contrato-estatico.md). O GET v2 documentado consome campos de estado e progresso. O v1 fornece usos de fase e erro. O CA está em um recurso público do aplicativo original, que deve ser obtido localmente; nenhum certificado ou valor de autenticação deve ser colocado no repositório.

Um estado `Paused`, processo ativo, WebSocket conectado ou ausência de erro retido não explica sozinho a atualização estacionada. A consulta e seu resultado precisam ser distinguidos da definição estática do endpoint.

## Publicação das próximas evidências

Mantenha somente fontes próprios e sínteses técnicas sanitizadas. Não adicione ASAR, binários, drivers, discos de VM, chaves, configuração de acesso, logs privados, contas ou capturas de login. Os identificadores de amostras por hash e nomes de dependências podem continuar em resumos factuais.

Antes de publicar uma alteração, revise conteúdo e diff, atualize o manifesto dos arquivos efetivamente incluídos e mantenha versões/datas como observações históricas. O arquivo de exclusões reduz adições acidentais, mas não remove material já rastreado ou presente no histórico Git.

Este roteiro não instala o REA nem registra um servidor MCP.
