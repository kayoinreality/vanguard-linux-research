# Erro de reabertura e recuperação após reparo oficial

Coleta somente de leitura em **12/10/2026, 19:53:21, America/Sao_Paulo**. Foram preservados até 40 eventos sanitizados dos logs gerais recentes. Não houve ação na UI, escrita na VM, início/parada de processos ou leitura de argumentos, autenticação ou lockfiles.

## Erro anterior confirmado

Às **19:40:43**, o launcher registrou falha ao **ler/abrir os metadados da instalação do Riot Client**. Em seguida registrou falha de atualização mencionando **RiotClientServices.exe**. Não foi identificado um HRESULT, DLL ausente, basename público específico do metadado ou estrutura interna de empacotamento que permita aprofundar a causa com esta evidência. A redação parcial foi preservada no JSON.

## Situação após o reparo

O responsável pela tarefa executou o reparo pelo instalador oficial e informou que o wrapper normal voltou a abrir a UI nativa em carregamento, sem o diálogo anterior de “Couldn't update”. Essa observação da interface é a evidência de recuperação; o coletor não operou nem inspecionou a UI.

A leitura do arquivo público confirmou:

| Campo | Resultado |
| --- | --- |
| Arquivo | RiotClientServices.exe |
| FileVersion do PE | **141.0.4.5083** |
| Tamanho | **76.543.296 bytes** |
| Arquitetura | x86-64, Machine 0x8664 |
| SHA-256 | cb802225b8db5322026a20672c3f91957fc0d638d5aba71430b243671d7b0090 |
| Duas leituras de hash | Coincidentes |

O hash coincide com o informado pela tarefa após o reparo. O SHA-256 informado para o novo ASAR é c59631b545fb11ccde204c901cb73bd9a7ba273e51e95cbf5f7ac51e606a7e60; esse arquivo não foi reaberto pelo coletor.

A amostra pós-reparo não identifica uma nova falha terminal do bootstrapper. Há mensagens genéricas de erro/HTTP, cuja finalidade não foi estabelecida. Menções como “permissions denied” dentro de payloads de estados não foram tratadas como erro ativo. A coleta de presença de metadados usou poucos caminhos fixos e não valida o conjunto completo.

## Limites

As palavras e identificadores desconhecidos foram substituídos por [redacted]; URLs, emails e contexto de autenticação/identidade foram excluídos. Esse filtro pode omitir detalhes decisivos. Horários relativos foram ancorados nos cabeçalhos e conferidos com mtime; a inferência está documentada no JSON.

A recuperação observada diz respeito à abertura do cliente. Não demonstra validade integral dos metadados, entrada no jogo, execução do Vanguard ou aceitação do ArchGuard.

Evidência complementar: erro-reabertura-apos-cancelar.json.
