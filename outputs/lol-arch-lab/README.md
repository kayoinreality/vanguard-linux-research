# Cliente Riot no laboratório Arch

Estudo de 12 de outubro de 2026. Ambiente: VM Hyper-V `Arch-Lab-Vanguard`, Arch Linux, kernel 7.2.9-arch1-1, Wine 11.19, usuário `lab` e prefixo exclusivo `/home/lab/lol-lab/prefix`.

## Resultado atual

**O login da Riot funcionou no Arch com a interface JavaScript original executada pelo Electron Linux 44.6.0.** O serviço Windows continua executado pelo Wine. A conta de laboratório foi configurada e a interface passou a mostrar a conta online. A identificação e a captura da conta foram preservadas somente no ambiente privado.

O instalador baixou os clientes do LoL e os componentes oficiais do Vanguard. Na coleta inicial, o executável da partida ainda estava ausente, embora o Riot Client já mostrasse “Play”. O login foi validado; a instalação completa do jogo, a abertura de sua interface e a entrada em partida continuam pendentes. A substituição do Vanguard pelo ArchGuard permanece sem implementação e sem validação.

O instalador Windows foi obtido pelo link da [página oficial brasileira](https://www.leagueoflegends.com/pt-br/download/). A assinatura Authenticode consultada no Windows é válida, emitida para Riot Games. O instalador abriu e baixou aproximadamente 465 MB, instalando o Riot Client.

| Componente | Versão observada | Situação |
| --- | --- | --- |
| Instalador BR | 138.0.0.4786 | Executado pelo Wine; etapa de instalação concluída |
| RiotClientServices.exe | 140.0.8.5062 | Instalado no prefixo; processo de serviços iniciou |
| Interface Windows `Riot Client.exe` | 140.0.0.0 no recurso PE | Instalado; renderizador falhou sob Wine |
| Pacote de interface `riot-client-ux` | 140.0.0 no ASAR | Login e criação do Riot ID concluídos com Electron Linux 44.6.0 |
| LeagueClient.exe | 16.20.827.198 | Instalado; tentativa inicial alcançou configuração da conta |
| Executável da partida `Game/League of Legends.exe` | — | Ausente na coleta inicial; instalação ainda não validada como completa |
| ArchGuard Lab | 0.1 | Serviço original continua ativo; nenhuma integração com Riot foi demonstrada |

Os SHA-256 dos dois executáveis instalados no guest coincidem com os executáveis correspondentes já instalados no Windows. Essas cópias do Windows tiveram assinatura Riot válida confirmada. `identidade-arquivos.json` registra hashes e verificações. O bootstrap e o cliente atualizado têm versões diferentes; não são a versão do jogo LoL.

## Falhas observadas e testes

1. A primeira abertura do Riot Client excedeu a memória disponível. O kernel da VM registrou `oom-kill`. Foram adicionados dois arquivos de swap, totalizando 4 GiB, somente no disco da VM. Eles estão ativos nesta sessão; não foram adicionados ao fstab.
2. Com memória suficiente, o renderizador da interface encerrou três vezes com `-2147483645`, equivalente a `0x80000003`. Esse código, sozinho, não identifica a causa nem prova bloqueio do Vanguard.
3. `--disable-gpu` fornecido ao lançador não chegou ao processo da interface. A lista de nomes dos argumentos foi verificada sem exportar seus valores de conexão.
4. O pacote da interface chama `app.disableHardwareAcceleration()` quando seu argumento próprio é falso. Sua tela de ajustes também usa `/data-store/v1/install-settings/hardware-acceleration`. Foi testada a preferência `hardware-acceleration: false`, preservando uma cópia local da configuração. A alteração não eliminou a falha.
5. A interface foi iniciada separadamente com argumentos locais de diagnóstico. Encerrar a interface original interrompeu a conexão com o serviço local. Uma tentativa posterior manteve seu processo suspenso durante o teste; a interface alternativa alcançou a montagem de `AppRouter`, mas o renderizador voltou a falhar. O processo original foi retomado ao concluir a tentativa.
6. O diagnóstico também testou `--no-sandbox` no Electron dentro da VM, com 4 GiB de swap. A falha persistiu. Essa opção reduz a proteção dos processos do Electron e não deve ser tratada como configuração aprovada para uso cotidiano. A tentativa terminou e sua unidade de serviço ficou inativa.
7. A auditoria estrutural encontrou 374 entradas no ASAR e nenhuma biblioteca nativa Windows nessa estrutura. O mesmo pacote, sem alterar seus bytes, foi iniciado pelo Electron do Arch. O wrapper adaptou caminhos de arquivo e o PID observado no Linux, preservando a conexão local emitida pelo serviço. Para manter essa conexão, a interface Windows original fica suspensa durante o experimento e é retomada quando a interface nativa encerra normalmente. A inicialização alcançou a tela de login, com WebSocket conectado. O runtime Linux iniciou sem `--no-sandbox`.

SHA-256 do ASAR executado: `5d346edfd1c69648643b2633ac75430db4722ad974b80521ff909759f26b88a6`. A estrutura está documentada em `../viabilidade-ui-nativa.md`. A troca do runtime resolveu a abertura nesta configuração; a causa exata da falha anterior ainda não foi determinada.

Os [argumentos](https://www.electronjs.org/docs/latest/api/command-line-switches) e as [variáveis de diagnóstico](https://www.electronjs.org/docs/latest/api/environment-variables) do Electron orientaram a coleta. Os eventos técnicos selecionados estão em `eventos-tecnicos.json`; os logs completos e as configurações de conexão permanecem no guest.

## Evidência sobre Vanguard

Durante a abertura sob Wine, foi registrada a chamada `OpenServiceW(..., L"vgk", 0x5)`, seguida da chamada do Wine ao gerenciador de serviços emulado. Isso confirma uma consulta ao serviço de nome `vgk`. Não estabelece o retorno dessa consulta, carregamento do driver, mensagens IOCTL ou uma sessão aceita pelo jogo.

O driver foi estudado separadamente como dados, incluindo os 70 bytes da entrada PE. Consulte `../analise-driver-vgk.md` e `../vgk-entry-disassembly.txt`. Suas dependências declaradas incluem `ntoskrnl.exe`, `cng.sys` e `HAL.dll`; a coincidência da arquitetura x86-64 não torna esses contratos compatíveis com o kernel Linux.

Os quatro componentes baixados pelo instalador coincidiram em hash, tamanho e versão com as referências Windows. As consultas feitas pelo Wine às 10:12 reportaram `vgk` e `vgc` como STOPPED, com código 1077. Essa observação não demonstra carregamento do driver ou aceitação de uma sessão. Consulte `vanguard-pos-instalacao.md` e seu JSON.

## Armazenamento do jogo

A raiz de 50 GiB chegou a 25 MB disponíveis durante a instalação. A reserva ext4 foi reduzida de 5% para 1%, mantendo aproximadamente 2 GiB disponíveis enquanto a migração era preparada. Foi adicionado um **novo VHDX dinâmico de 60 GiB**, sem redimensionar nem mesclar a cadeia VHDX/AVHDX anterior. A criação e a anexação seguiram os cmdlets oficiais [New-VHD](https://learn.microsoft.com/en-us/powershell/module/hyper-v/new-vhd?view=windowsserver2025-ps) e [Add-VMHardDiskDrive](https://learn.microsoft.com/en-us/powershell/module/hyper-v/add-vmharddiskdrive?view=windowsserver2025-ps). O checkpoint anterior representa o estado capturado antes desta expansão; não constitui backup do disco novo.

O novo disco foi identificado por serial, tamanho e ausência de assinatura antes da criação do ext4. As duas pastas de jogo foram copiadas com os serviços do cliente parados. Conteúdo SHA-256, tamanhos, links e modos de acesso passaram na comparação entre origem e destino: 518 arquivos/30.104.485.239 bytes do LoL e os arquivos do TFT documentados em `migracao-arquivos-jogo.json`.

O volume usa UUID `aa6311c7-ff75-4b48-b5e4-971836c18ca6` e monta em `/var/lib/lol-lab/game-data`. Bind mounts conservam os dois caminhos originais dentro de `C:\Riot Games`. A persistência foi validada após reiniciar a VM; o helper de abertura também recusa iniciar quando o volume ou os binds esperados estão ausentes. Depois de reabrir o Riot Client, as cópias duplicadas na raiz foram removidas. A raiz ficou com aproximadamente 37 GiB livres e o disco de jogo com 24 GiB livres naquele momento. Liberar espaço no guest não confirma redução física dos arquivos VHDX no Windows.

## O que falta para o objetivo

O reinício necessário para validar a montagem encerrou a sessão. O usuário refez o login manualmente, e a conta voltou a aparecer online. A atualização pendente foi retomada: a interface registrou 7,4 de 34 GB a aproximadamente 39 MB/s; a captura desse estágio permanece no ambiente privado. O usuário confirmou Brasil e português para a conta nova; a aplicação dessas escolhas na tela do jogo ainda está pendente. A instalação está sendo acompanhada antes do primeiro lançamento com espaço disponível. Até aqui não há um bypass implementado ou teste de substituição pelo ArchGuard.

`contratos-league-client.md` registra a análise estática atual dos dois executáveis do cliente. O Ux declara 54 importações da biblioteca CEF; o LeagueClient declara integração Riot, atualização e Direct3D. As listas mostram dependências declaradas, sem provar chamadas executadas ou equivalência com Linux. `primeiro-lancamento.json` contém somente metadados públicos e contagens técnicas sanitizadas; as menções históricas a arquivos ausentes não foram atribuídas como causa de uma tentativa específica.

Executar os binários Windows pelo Wine não produz um port nativo. A [Riot explica que Wine/Lutris não satisfazem os requisitos do Vanguard no Linux](https://www.leagueoflegends.com/pt-br/news/dev/dev-vanguard-x-lol/). Essa posição de suporte não substitui os testes locais, mas impede considerar a simples abertura do cliente como prova de compatibilidade.

## Arquivos e acesso

O cliente está em `/home/lab/lol-lab/prefix/drive_c/Riot Games/Riot Client`. O acesso visual do laboratório usa noVNC pelo túnel SSH local, em `http://127.0.0.1:16081/vnc.html?autoconnect=true&resize=scale`. Os serviços de acesso gráfico escutam somente no loopback da VM e o túnel escuta somente no loopback do Windows.

Para reabrir a configuração já instalada, execute `reabrir-interface.ps1` no Windows. Quando a interface já está ativa, ele conserva a sessão e apenas informa o endereço. As unidades gráficas são transitórias; o script do laboratório também reativa seus arquivos de swap após um reboot. A VM precisa estar iniciada e acessível por SSH.

`start-native-ui.py`, `start-native-lab.sh` e `start-client.sh` são nossos wrappers originais. O pacote da Riot permanece no guest e não está incluído nesses entregáveis. A interface nativa usa um diretório próprio de preferências em `/home/lab/lol-lab/native-user` e mantém os dados de conexão no ambiente do laboratório.
