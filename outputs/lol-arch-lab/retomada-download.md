# Retomada do download após cancelamento

Observações de 12/10/2026. O lançador foi recuperado pelo instalador oficial BR no mesmo prefixo Wine e a atualização do LoL voltou a avançar. A conclusão da instalação e a entrada em partida ainda precisam de evidência separada.

## Reabertura e reparo do lançador

A primeira reabertura mostrou “Couldn't update”. Os registros sanitizados identificam falha de leitura/abertura dos metadados da instalação, mas não estabelecem o arquivo ou a estrutura interna que causou o erro. Consulte [o diagnóstico](erro-reabertura-apos-cancelar.md).

O instalador oficial foi executado novamente com destino `C:\Riot Games`, no prefixo já existente da VM. Os volumes vinculados de League of Legends e Teamfight Tactics continuaram montados. A interface original voltou a abrir pelo wrapper Electron Linux e manteve a sessão autenticada.

Componentes observados após o reparo:

| Componente | Identidade |
| --- | --- |
| RiotClientServices.exe | PE 141.0.4.5083; 76.543.296 bytes; SHA-256 `cb802225b8db5322026a20672c3f91957fc0d638d5aba71430b243671d7b0090` |
| app.asar | 154.535.634 bytes; SHA-256 `c59631b545fb11ccde204c901cb73bd9a7ba273e51e95cbf5f7ac51e606a7e60` |

As identidades anteriores permanecem nos inventários históricos. Essa mudança de versão impede tratar as duas coletas como se fossem o mesmo lançador.

## Estado do jogo antes e depois da solicitação

A página do LoL mostrou `Repair`. O GET v2 confirmou `NeedsRepair` com `launchable=false`. Após a solicitação oficial de reparo pela interface, apareceram `Getting ready` e, em seguida, atualização em andamento.

| Horário UTC | Estado v2 | Progresso desta etapa |
| --- | --- | --- |
| 22:53:42 | NeedsRepair | 0 bytes |
| 22:54:31 | Updating | 1.331.783.923 / 6.904.276.777 bytes; 19,13% |
| 22:55:42 | Updating | 5.065.244.594 / 6.904.276.777 bytes; 73,11% |
| 22:56:27 | Updating | 6.666.496.147 / 6.904.276.777 bytes; 96,41% |

O avanço de bytes confirma a retomada nesta etapa. Os dados anteriores foram preservados e o total exibido é menor que o download original, mas não medimos quantos arquivos foram efetivamente reutilizados. Percentuais de etapas distintas não devem ser comparados como progresso total da instalação.

Nessas quatro leituras, `launchable=false`. Às **22:57:57 UTC**, uma etapa posterior mostrou `Updating`, 2.632.813.714 / 3.290.679.323 bytes, 79,82% e **`launchable=true`**. O total mudou entre as etapas; essa coleta não deve ser comparada numericamente com o percentual anterior. A disponibilidade indicada pelo patcher permite testar o lançamento, mas não comprova que ele tenha ocorrido.

O endpoint v1 continuou retornando `not_installed`; essa diferença entre versões da API não foi usada para atribuir a causa da falha. Não houve diagnóstico de bloqueio pelo Vanguard com base nesses campos.

## Solicitação de lançamento e região

A interface exibiu `Play`. A solicitação de abertura mostrou a escolha inicial de região; foram aplicados Brasil e português, conforme a preferência do usuário. Em seguida, a interface voltou a mostrar a barra de atualização com um indicador de velocidade de 41,3 MB/s. Esse indicador visual, isoladamente, não mede atividade nova de download.

Às **23:00:05 UTC**, o GET v2 mostrou `Updating`, `previousState=CheckingForUpdate`, `launchable=false` e progresso de 99,99098%. Os contadores eram 3.290.679.323 bytes baixados e zero no total a baixar; esse estado transitório não foi interpretado como instalação concluída. O valor anterior `launchable=true` era uma observação daquela etapa, e não uma propriedade permanente.

Não foi observada a abertura da interface LeagueClient ou entrada em partida até essa coleta. Consulte [a leitura após a seleção da região](estado-patcher-apos-regiao.json).

## Método e evidências

O [contrato do ASAR reparado](contrato-patcher-apos-reparo.json) confirma os caminhos públicos de estado v1/v2. A coleta usa apenas GET no backend local, com CA original e validação de certificado e nome de host habilitadas. Valores da conexão permanecem apenas em memória; os documentos contêm campos selecionados de estado e progresso.

- [Antes do reparo do jogo](estado-patcher-antes-reparo-jogo.json)
- [Primeiro avanço](estado-patcher-apos-reparo-jogo.json)
- [Segundo avanço](estado-patcher-progresso-retomada.json)
- [Última leitura desta coleta](estado-patcher-retomada-final.json)
- [Etapa posterior com lançamento disponível](estado-patcher-atual.json)

As capturas da interface e os arquivos proprietários permanecem no laboratório privado. A recuperação do lançador e o download não comprovam execução do driver no Linux ou aceitação do ArchGuard pelo LoL.
