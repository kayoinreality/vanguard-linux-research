# Estudo inicial: Vanguard, LoL e Arch Linux

Data de referência: 11 de outubro de 2026, America/Sao_Paulo.
Momento exato da coleta em UTC: 2026-10-12T02:34:20.316716+00:00.

## Resultado desta etapa

O inventário e a leitura básica dos binários oficiais já podem ser feitos no Windows atual. Foram preservadas seis cópias locais para análise; o SHA-256 de cada cópia coincidiu com o original antes e depois da cópia. Todos os arquivos analisados são PE32+ x86-64 e têm assinatura digital reconhecida como válida pelo Windows.

O driver `vgk.sys` declara dependências de `ntoskrnl.exe`, `HAL.dll` e `cng.sys`. Essa observação sustenta que a compatibilidade envolve serviços do núcleo do Windows. Não determina quais rotinas são executadas, quais verificações são exigidas em uma sessão, nem se uma implementação alternativa seria aceita pelo LoL.

Ainda não existe neste projeto um substituto do Vanguard nem uma execução do LoL validada no Linux. O resultado é uma base verificável para orientar a investigação.

## Máquina de referência

| Item | Identificação local |
| --- | --- |
| Placa-mãe | MSI H310M PRO-M2 (MS-7B28), revisão informada pelo firmware: 2.0 |
| Processador | Intel Core i7-8700, 6 núcleos / 12 processadores lógicos |
| Vídeo | NVIDIA GeForce GTX 1660 e Intel UHD Graphics 630 |
| Memória | 15,9 GiB detectados, correspondente aos 16 GB informados |
| Windows | Windows 11 Pro, versão 10.0.28000, build 28000 |
| BIOS | A.E0, data informada: novembro de 2024 |
| Sistema alvo | Arch Linux x86-64; ainda não instalado, conforme informado pelo usuário |

O Windows reporta `HypervisorPresent=true`. Isso pode ocorrer com recursos de virtualização e segurança do próprio Windows; não demonstra que este Windows esteja instalado em uma máquina virtual.

## Arquivos examinados

| Arquivo | Versão | Subsistema PE | Descritores de importação | Entradas importadas | Assinatura |
| --- | --- | --- | --- | --- | --- |
| `vgc.exe` | 1.19.1-18+20261001.143443 | Windows GUI | 15 | 357 | Valid |
| `vgk.sys` | 1.19.1-18+20261001.143443 | Native | 3 | 129 | Valid |
| `vgm.exe` | 1.19.1-18+20261001.143443 | Windows GUI | 7 | 231 | Valid |
| `vgrl.dll` | 1.19.1-18+20261001.143443 | Windows CUI | 10 | 22 | Valid |
| `LeagueClient.exe` | 16.20.827.198 | Windows GUI | 32 | 758 | Valid |
| `League of Legends.exe` | 16.20.824.8524 | Windows GUI | 25 | 446 | Valid |

As contagens acima correspondem à tabela comum de importações PE, lida sem avisos pelo analisador. Descritores podem repetir o mesmo nome de biblioteca. Importações dinâmicas e atrasadas não foram examinadas.

No `vgc.exe`, a tabela inclui funções de serviços do Windows como `StartServiceCtrlDispatcherW`, `OpenSCManagerW`, `OpenServiceW` e `StartServiceW`. A presença dessas funções é um indício das interfaces a investigar, e não evidência de sua execução numa sessão específica.

No `vgk.sys`, a tabela inclui interfaces como `MmGetSystemRoutineAddress`, `IoCreateFileEx` e `ZwQuerySystemInformation`. O significado de cada uso exige análise de código e observação de execução posteriores.

## Estado observado e limites

- O usuário informa que LoL e Vanguard estão instalados e funcionando no Windows.
- No instante da coleta, o serviço `vgc` e o driver `vgk` estavam parados, ambos com modo de início informado como Manual. Nenhum deles foi iniciado pelo estudo. Uma sessão funcional ainda precisa ser registrada como referência.
- O registro do Windows informa `UEFISecureBootEnabled=1`, ou seja, Secure Boot habilitado segundo essa fonte. A consulta direta à UEFI não pôde ser concluída por falta de privilégios. As fontes foram registradas separadamente.
- O estado do TPM não pôde ser obtido. Isso não significa ausência ou desativação do TPM.
- Foram examinados cabeçalhos, seções e importações comuns dos arquivos em disco. Não houve carregamento dos binários pelo analisador, descompilação completa, análise de protocolos nem instrumentação de execução.
- A entropia das seções consta do inventário técnico. Esse número isolado não prova criptografia, compactação ou uma técnica específica de proteção.

## Ambiente Arch proposto

Para começar com ferramentas e pequenos programas próprios, uma VM Arch com 4 vCPU, 4–6 GB de RAM e 40–60 GB de disco dinâmico é um dimensionamento inicial razoável para este PC. Essa é uma proposta de laboratório, não um requisito oficial nem uma validação de desempenho. O acesso direto à GTX 1660 não é necessário nesta primeira etapa.

Para testes posteriores de compatibilidade no hardware físico, a opção preferencial é um SSD separado com instalação Arch em UEFI. A escolha e a disponibilidade do disco ainda estão pendentes. A GTX 1660 aparece na lista de GPUs suportadas pelos módulos abertos da NVIDIA; o ArchWiki recomenda a família de pacotes `nvidia-open` para Turing. [NVIDIA](https://github.com/NVIDIA/open-gpu-kernel-modules), [ArchWiki: NVIDIA](https://wiki.archlinux.org/title/NVIDIA).

A ISO oficial do Arch não oferece suporte a Secure Boot. A preparação da instalação precisa considerar o Windows atual e uma futura cadeia de boot assinada. Configurações UEFI/TPM e chaves do firmware são compartilhadas pela máquina mesmo quando os sistemas usam discos distintos. [ArchWiki: Secure Boot](https://wiki.archlinux.org/title/Unified_Extensible_Firmware_Interface/Secure_Boot).

## Próximos experimentos e critérios

1. **Referência de execução no Windows.** Registrar versões, estado de serviços e processos durante uma abertura normal do LoL, com horário e resultado observados. Isso deve confirmar a diferença entre o relato de funcionamento e o estado parado visto nesta coleta.
2. **Análise estática aprofundada.** Examinar funções e caminhos que utilizam as interfaces identificadas, separando fatos observados de hipóteses. Escolher ferramentas oficiais e analisar as cópias preservadas.
3. **Matriz de compatibilidade.** Para cada interface relevante, registrar a função exigida, a evidência, a disponibilidade no Wine/Linux e um teste pequeno que consiga demonstrar o comportamento equivalente. Um nome importado, sozinho, não basta para preencher essa matriz.
4. **Experimentos isolados.** Usar programas próprios para verificar hipóteses específicas no Arch. Um programa que simule comunicação entre serviço e driver demonstra apenas esse comportamento local.
5. **Avaliação de interoperabilidade.** Antes de uma implementação ampla, determinar quais requisitos podem ser atendidos localmente e quais dependem da integração com o sistema da Riot. A documentação pública não especifica todo esse contrato.

A Riot declara que Wine/Lutris não satisfazem os requisitos do Vanguard e que a integridade do ambiente faz parte da proteção. Isso é uma limitação documentada, mas não uma prova de impossibilidade absoluta de qualquer pesquisa futura. O estudo precisa produzir evidências de compatibilidade; um anticheat independente não recebe integração automática com o LoL. [Riot: Vanguard x LoL](https://www.leagueoflegends.com/pt-br/news/dev/dev-vanguard-x-lol/).

## Evidência reproduzível

O arquivo `inventario-vanguard-arch.json` contém o inventário local, as versões, os resultados das assinaturas e a análise dos cabeçalhos e importações. Os binários de referência permanecem no diretório de trabalho local e não são incluídos nos entregáveis.

SHA-256 dos arquivos examinados:

- `vgc.exe`: `c8f330a77351f36e1112d0b94972a735a7747fc33a4aa4735d95f43f01637c51`
- `vgk.sys`: `8ba32cfbc4a07fd41a082344e23e312515ffafef0e568ba72e7d33e83b558f13`
- `vgm.exe`: `55e25cce83c8ec9088b99d1193a7aa750609e69ed8cfc7c758076ec3591de3d9`
- `vgrl.dll`: `d76344bcda5acba14156b090e037ccc270f15d3571d2c629a83f5f7263be32c0`
- `LeagueClient.exe`: `e1c9fdae2f29f5f8bd94fda4b5168850989cb06fd651aeb5739faaa701f5e09c`
- `League of Legends.exe`: `f6fd49d6fb21c6cec23e329ca8a9a7c0809393cb950daf29ca62cf60a08455c6`

A estrutura do analisador segue a especificação pública PE/COFF da Microsoft. Esse formato documenta a representação do arquivo, não o comportamento completo do programa. [Microsoft: PE Format](https://learn.microsoft.com/en-us/windows/win32/debug/pe-format).
