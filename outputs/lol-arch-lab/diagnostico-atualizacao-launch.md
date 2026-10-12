# Atualização e solicitação de lançamento: diagnóstico sanitizado

Coleta concluída em 12/10/2026, às 11:22:18, America/Sao_Paulo. Foram lidos três logs gerais recentes do Riot Client; nenhuma ação de UI, início/parada de processos ou escrita na VM foi realizada.

**Estado concreto observado:** às 11:14:20 local o RCS registrou **launchable=false** para league_of_legends, patchline live. Esse é um indício de indisponibilidade de lançamento naquele instante. O registro isolado não determina a condição interna responsável nem prova qual requisito rejeitou a solicitação.

Os novos cabeçalhos de início são de aproximadamente 11:14:18, cerca de dois segundos antes desse estado. A observação pode pertencer à inicialização e não comprova um estado persistente do processo principal.

Há eventos técnicos até 11:21, incluindo mensagens de estado do patcher às 11:18:31. Na seleção sanitizada não foi recuperado um erro público específico, dependência ausente ou enum conhecido que explique a atualização parada em 61%. **A causa permanece ambígua.** A presença de mensagens periódicas também não demonstra progresso efetivo do patcher.

O JSON complementar contém 196 eventos técnicos, dos quais 68 são desde 11:04 local. O texto foi reconstruído com vocabulário fechado: palavras desconhecidas e identificadores viram [redacted]; linhas com contexto de autenticação ou identidade foram excluídas. Esse filtro pode retirar detalhes decisivos, portanto ausência de um erro retido não equivale a ausência de erro nos logs.

Os horários vêm dos cabeçalhos de início e do tempo relativo das mensagens. Cabeçalhos sem fuso foram interpretados pela correspondência entre o último tempo relativo e o horário de modificação do arquivo, com diferenças observadas de 0,238 segundo ou menores. Essa inferência é registrada em cada âncora. Linhas sem tempo utilizável não foram incluídas.

Não foram exportadas linhas brutas, números de campos desconhecidos, URLs, endereços de email, nomes de usuário, contas, tokens, caminhos de conta ou lockfiles. Também não foram lidos argumentos de processos nem configurações de autenticação.

Evidência complementar: diagnostico-atualizacao-launch.json. Os resultados sustentam a observação do estado, não uma conclusão sobre bloqueio pelo Vanguard ou aceitação do ArchGuard.
