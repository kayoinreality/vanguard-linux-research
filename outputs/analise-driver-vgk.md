# Análise estática inicial do driver vgk.sys

Referência: 12 de outubro de 2026, America/Sao_Paulo. Análise dos bytes da cópia local e desassemblagem limitada de uma cópia no laboratório Arch; nenhum driver foi carregado, executado ou modificado.

## Resultado

O arquivo declara dependências de três componentes do Windows: `ntoskrnl.exe`, `cng.sys` e `HAL.dll`. A arquitetura x86-64 coincide com a do computador e do laboratório Arch, mas isso não demonstra compatibilidade com os contratos de kernel utilizados. O obstáculo a investigar inclui objetos, memória, sincronização e contexto de execução; as importações não permitem determinar quais desses recursos são usados numa sessão do LoL.

Foram localizados o ponto de entrada do PE, duas exportações e os diretórios de importação e de exceções. A leitura das instruções de 70 bytes na entrada mostra uma chamada direta seguida de retorno condicional ou salto indireto. Este resultado orienta a próxima análise de código, sem identificar um protocolo ou estabelecer viabilidade de um substituto aceito pelo jogo.

O objetivo em estudo é utilizar o ArchGuard com o cliente oficial do LoL. Há três resultados distintos a avaliar:

| Frente | O que precisaria ser demonstrado | Situação desta etapa |
| --- | --- | --- |
| Implementação nativa no Linux | Funcionalidades próprias de proteção implementadas sobre os contratos do Linux | Não há código-fonte do Vanguard disponível neste estudo para adaptar ou recompilar. Ler o PE não produz um port nativo. |
| Compatibilidade de APIs Windows | Retornos, estruturas e contexto equivalentes para os caminhos efetivamente usados pelo programa Windows | Foram identificadas dependências declaradas; nenhuma equivalência completa foi demonstrada. |
| Integração com o cliente oficial | O cliente consumir a implementação alternativa e os serviços oficiais aceitarem a sessão | Não foram identificados os contratos de comunicação ou atestação. Não há uma partida autenticada para validar esse resultado. |

A inicialização do instalador e do cliente Riot por Wine é evidência de progresso nessa parte do aplicativo. Uma tela inicial não valida a integração do jogo com um anticheat alternativo.

## Identidade da amostra

| Campo | Resultado observado |
| --- | --- |
| Arquivo | `vgk.sys` |
| Versão | `1.19.1-18+20261001.143443` |
| Tamanho em disco | 109.721.528 bytes |
| SHA-256 | `8ba32cfbc4a07fd41a082344e23e312515ffafef0e568ba72e7d33e83b558f13` |
| Formato / máquina / subsistema | PE32+ / AMD64 x86-64 / Native |
| Seções | 16 |
| Base preferida declarada | `0x140000000` |
| Tamanho de imagem declarado | 108.994.560 bytes |
| Assinatura do arquivo instalado | `Valid`, segundo a verificação Authenticode do Windows |

O SHA-256 da cópia foi recalculado nesta etapa e coincide com o inventário anterior. Uma consulta somente de leitura ao arquivo instalado confirmou tamanho, versão e hash iguais. A assinatura foi consultada no arquivo instalado; o analisador de PE não verifica certificados. A base preferida é um campo do arquivo, não um endereço medido em execução.

A cópia enviada ao Arch em `/home/lab/vanguard-study/vgk.sys` teve o mesmo SHA-256 confirmado antes da leitura por `objdump`. Executar o analisador para ler esse arquivo não executa o código do driver.

## Pontos de entrada e localização das tabelas

RVA identifica uma posição relativa à base da imagem; offset identifica uma posição nos bytes do arquivo. Esses valores têm significados diferentes. [Especificação PE/COFF da Microsoft](https://learn.microsoft.com/en-us/windows/win32/debug/pe-format).

| Item | RVA | Offset no arquivo | Seção que contém os bytes |
| --- | --- | --- | --- |
| `AddressOfEntryPoint` | `0x061C213C` | `0x0618673C` | `.riot1` |
| Exportação `Egg`, ordinal 1 | `0x067C6ED0` | `0x0678B4D0` | `.riot1` |
| Exportação `Egg2`, ordinal 2 | `0x067C6EE0` | `0x0678B4E0` | `.riot1` |
| Diretório de exportação | `0x0616F250` | `0x06133850` | `.riot0` |
| Diretório de importação | `0x001AC000` | `0x00173600` | `INIT` |
| Diretório de exceções | `0x06105128` | `0x060C9728` | `.riot0` |

Os nomes `Egg` e `Egg2` são os nomes efetivamente declarados; sua finalidade não foi determinada. O endereço de entrada pode levar a uma rotina intermediária antes da inicialização principal. Não foi atribuído a ele um nome recuperado de símbolo.

A Microsoft descreve `DriverEntry` como a rotina de inicialização de um driver e documenta os parâmetros `DRIVER_OBJECT` e caminho do registro. Isso fornece uma referência para estudar inicialização; não comprova que os bytes neste RVA correspondam diretamente a uma implementação identificável desse contrato. [DRIVER_INITIALIZE](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nc-wdm-driver_initialize).

Há seções chamadas `.edata` e `.pdata`, mas os diretórios relevantes apontam para `.riot0`. Portanto, procurar tabelas apenas pelos nomes das seções produziria um mapa incompleto. A seção `.grfn1` ocupa 99.674.112 bytes, cerca de 90,84% do arquivo; tamanho, nome e entropia não estabelecem seu papel ou uma técnica de proteção.

O diretório de exceções declara 434.472 bytes, equivalentes a 36.206 registros candidatos de 12 bytes no formato x64. Todos passaram por uma checagem mínima de intervalo e mapeamento; os inícios estão ordenados. Um registro abrange a entrada PE: `[0x061C213C, 0x061C2182)`, com referência de unwind em `0x061C6110`. Não foram validadas instruções, regras de unwind ou cobertura de código. **36.206 não é uma contagem de funções reais.** [Formato x64 de RUNTIME_FUNCTION e unwind](https://learn.microsoft.com/en-us/cpp/build/exception-handling-x64?view=msvc-170).

Os diretórios TLS e de importações atrasadas têm RVA e tamanho zero. Isso descreve esses campos; não exclui inicialização adicional, resolução dinâmica ou callbacks registrados em execução.

## Desassemblagem limitada da entrada

O arquivo [vgk-entry-disassembly.txt](vgk-entry-disassembly.txt) registra as instruções de `[0x1461C213C, 0x1461C2182)`, com endereços calculados a partir da base preferida. Os 70 bytes exibidos nas 27 instruções coincidem com a cópia local nesse offset. A leitura cobre apenas esse intervalo; o alvo da chamada ainda não foi analisado.

| Trecho observado | Interpretação limitada |
| --- | --- |
| `push` de `RBX`, `RCX`, `RDX`, `R8`, `R9`; reserva de `0x20` bytes na pilha | Os cinco registradores são salvos. A reserva de 32 bytes antes da chamada é consistente com o espaço de parâmetros da ABI x64 do Windows. |
| `lea RBX,[RIP-0x8E]`; `mov R8,RBX`; `call 0x1461B9E27` | `RBX` recebe o endereço local `B=0x1461C20C0`, também passado em `R8` à chamada direta. Os tipos dos argumentos e a função chamada ainda são desconhecidos. |
| Recuperação dos 32 bytes; `pop R9`, `R8`, `RDX`, `RCX`; testes de `EAX` | Se os 32 bits de `EAX` são zero ou `0xD4494E49`, o trecho restaura `RBX` e executa `ret`. O significado desses valores não foi identificado. |
| Leituras em deslocamentos derivados de `RBX` após a chamada; restauração de `RBX`; `jmp RAX` | Nos demais casos, calcula um destino usando dados em memória e transfere o controle por salto indireto. Não há um destino fixo comprovado nesta leitura. |

A documentação Microsoft descreve `RCX`, `RDX`, `R8` e `R9` para os primeiros argumentos inteiros e prevê espaço na pilha para quatro parâmetros; `RBX` é um registrador preservado pela função. Isso sustenta a comparação com a ABI, sem identificar o contrato da rotina observada. [Convenção x64 do Windows](https://learn.microsoft.com/en-us/cpp/build/x64-calling-convention?view=msvc-170).

O cálculo observado do salto pode ser representado assim, considerando as leituras após a chamada direta:

```text
R = valor de RBX após a chamada direta
deslocamento = extensão com sinal para 64 bits de DWORD[R + 0x28]
ponteiro = QWORD[R + deslocamento + 0x10]
ajuste = extensão com zeros para 64 bits de DWORD[R + 0x5C]
destino = (ponteiro + ajuste) módulo 2^64
```

`DWORD` e `QWORD` indicam leituras de 32 e 64 bits. Se a chamada respeitar a preservação de `RBX` prevista pela ABI, `R` permanece igual a `B=0x1461C20C0`; o corpo chamado ainda não foi examinado para confirmar isso. Essa expressão descreve o fluxo de instruções, sem atribuir nomes às estruturas. A chamada também pode afetar os dados consultados. A sequência é compatível com uma pequena rotina intermediária de encaminhamento, cuja finalidade permanece indeterminada. Ela não identifica `DriverEntry`, uma política, mecanismo de proteção ou protocolo do Vanguard.

O `objdump` avisou que ignorou `IMAGE_SCN_MEM_NOT_PAGED` em algumas seções. Esses avisos delimitam a interpretação dos atributos PE pela ferramenta. A desassemblagem não testa paginabilidade, carregamento ou comportamento do driver no Linux.

## Dependências Windows declaradas

A tabela ordinária contém **129 entradas**: 119 em `ntoskrnl.exe`, nove em `cng.sys` e uma em `HAL.dll`. Os grupos abaixo são uma classificação dos nomes, sem atribuir ao Vanguard um comportamento observado.

| Contrato a investigar | Exemplos presentes | Questão ainda aberta |
| --- | --- | --- |
| Memória e contexto de processo | `IoAllocateMdl`, `MmMapLockedPagesSpecifyCache`, `MmUnmapLockedPages`, `KeStackAttachProcess`, `KeUnstackDetachProcess` | Quais buffers, processos, permissões e contextos são realmente usados? |
| Objetos, arquivos e configuração | `IoCreateFileEx`, `ZwReadFile`, `ZwWriteFile`, `ObReferenceObjectByHandle`, `ZwCreateKey`, `ZwSetValueKey` | Quais objetos são abertos e com quais opções? Não foram identificados dispositivos ou mensagens. |
| Threads, sincronização e níveis de execução | `PsCreateSystemThread`, `KeInitializeDpc`, `KeGetCurrentIrql`, `KeAcquireSpinLockRaiseToDpc`, `KeWaitForSingleObject` | Quais ordens de chamada e requisitos de contexto precisam ser satisfeitos? |
| Resolução e consulta ao sistema | `MmGetSystemRoutineAddress`, `ZwQuerySystemInformation` | Quais nomes são resolvidos e quais classes de informação são solicitadas? |
| Hashes e assinaturas | `BCryptOpenAlgorithmProvider`, `BCryptCreateHash`, `BCryptHashData`, `BCryptFinishHash`, `BCryptImportKeyPair`, `BCryptVerifySignature` | Quais algoritmos, chaves, formatos e entradas são escolhidos? |
| Temporização | `HAL.dll`: `KeQueryPerformanceCounter`; kernel: `KeQuerySystemTimePrecise` | Quais valores são comparados e com quais tolerâncias? |

`MmGetSystemRoutineAddress` resolve rotinas exportadas pelo kernel ou HAL. Sua presença torna especialmente inadequado tratar a tabela ordinária como lista completa das rotinas possíveis. [Documentação Microsoft](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-mmgetsystemroutineaddress).

`IoCreateFileEx` usa estruturas e opções do gerenciador de I/O do Windows. `KeStackAttachProcess` e o mapeamento por MDLs possuem contratos próprios do kernel; uma troca de dados entre programas de usuário não valida esses contratos. [IoCreateFileEx](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntddk/nf-ntddk-iocreatefileex), [KeStackAttachProcess](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-kestackattachprocess), [MmMapLockedPagesSpecifyCache](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-mmmaplockedpagesspecifycache).

`BCryptVerifySignature` verifica uma assinatura segundo chave, dados e parâmetros fornecidos; sua documentação estabelece condições para chamadas em modo kernel. Essa importação não identifica uma política de certificados ou atestação usada pelo Vanguard. [BCryptVerifySignature](https://learn.microsoft.com/en-us/windows/win32/api/bcrypt/nf-bcrypt-bcryptverifysignature).

## Próximos experimentos do laboratório

1. **Mapa estático da inicialização.** Ampliar a leitura a partir da chamada identificada em `0x1461B9E27`, delimitando o intervalo antes de interpretar código. Seguir os destinos de chamadas e saltos identificáveis e registrar regiões que a ferramenta não consegue interpretar. Exportações e registros de unwind são pistas de localização, não descrições de finalidade.
2. **Contratos com dados próprios.** Exercitar hash e verificação de assinatura com vetores, chaves e formatos escolhidos para o laboratório. Comparar resultados matemáticos e casos de erro com um programa próprio no Windows. O sucesso não valida os provedores ou contextos do driver.
3. **Semântica local em programas próprios.** Medir eventos, espera, temporização e mapeamento de buffers com casos definidos. Identificar separadamente o que é observável em espaço de usuário e o que exigiria um futuro driver de laboratório em uma VM Windows específica.
4. **Matriz por chamada confirmada.** Para cada chamada identificada no código, registrar parâmetros, estruturas, requisito de contexto e evidência. Só então avaliar alternativas no Linux. Ainda não foi verificada a disponibilidade equivalente dessas interfaces no Arch ou em uma camada de compatibilidade.

Um protótipo de laboratório que troca mensagens ou detecta alterações em um arquivo demonstra seu contrato próprio. Ele não demonstra execução de `vgk.sys` no Linux, equivalência do Vanguard ou aceitação do LoL pelos serviços oficiais.

### Roteiro concreto de leitura estática

1. Confirmar o SHA-256 da cópia e abrir o arquivo em modo de leitura no analisador, com arquitetura x86-64 e base preferida `0x140000000`. Conferir cabeçalhos, seções, importações e exportações antes de interpretar código.
2. Revisar os 70 bytes já desassemblados, cobertos pelo registro que começa na entrada PE. O endereço calculado com a base preferida é `0x1461C213C`; o offset em disco permanece `0x0618673C`. Esses são endereços para análise estática, sem afirmar que sejam os endereços de uma sessão em execução.
3. Seguir chamadas e saltos diretos que a desassemblagem consiga sustentar. Registrar os alvos e os bytes de origem. Em chamadas indiretas, separar endereço comprovado, hipótese e destino ainda desconhecido; não preencher a lacuna com o nome de uma importação próxima.
4. Localizar referências identificáveis às entradas da IAT, especialmente às famílias de memória, sincronização e resolução dinâmica. Uma referência estática também não prova que o caminho seja alcançado em uma sessão.
5. Para estudar os módulos importados, consultar primeiro os contratos documentados das APIs. Uma etapa futura pode inventariar e ler tabelas de exportação de cópias oficiais de `ntoskrnl.exe`, `HAL.dll` e `cng.sys`, preservando versão e hash. Não foram analisados os bytes desses módulos nesta etapa.
6. Registrar cada descoberta com hash da amostra, RVA, offset, evidência, interpretação e incerteza. Só propor um experimento de compatibilidade depois de definir entradas e resultados esperados para programas próprios.

Com a cópia já verificada em `/home/lab/vanguard-study/vgk.sys`, a leitura limitada da entrada é reproduzível no Arch por:

```sh
objdump -D -Mintel --start-address=0x1461C213C --stop-address=0x1461C2182 /home/lab/vanguard-study/vgk.sys
```

As opções selecionam o intervalo e o formato da saída de desassemblagem. [Manual GNU objdump](https://sourceware.org/binutils/docs/binutils/objdump.html).

Estas alternativas com radare2 solicitam metadados e o mesmo intervalo de bytes. São instruções adicionais; não foram executadas neste estudo:

```sh
rabin2 -I -S -i -E vgk.sys
r2 -N -q -B 0x140000000 -c 'iI;iS;ii;iE;pD 70 @ 0x1461C213C;q' vgk.sys
```

`-N` desativa configurações pessoais de inicialização; a linha abre o binário em leitura. `pD 70` seleciona 70 bytes, e não 70 instruções ou uma função comprovadamente completa. [Manual oficial radare2](https://github.com/radareorg/radare2/blob/master/man/radare2.1), [Print Modes](https://book.rada.re/commandline/print_modes.html#disassembly), [Rabin2](https://book.rada.re/tools/rabin2/intro.html).

## Limites e reprodução

Foram lidos cabeçalhos, seções, importações ordinárias, exportações e diretórios PE; a tabela de exceções recebeu apenas checagens estruturais mínimas. Houve desassemblagem estática dos 70 bytes da entrada. Não houve recuperação completa de lógica, análise de protocolos, acesso à memória do processo, instrumentação ou teste de carga do driver. A ausência de um nome na tabela não prova ausência de uso. A validação estrutural sem avisos e a saída de desassemblagem não certificam que o arquivo inteiro seja carregável em outro ambiente.

As evidências locais são `work/vanguard-estudo/pe-inventory.json`, `work/vanguard-estudo/vgk-static-details.json` e `outputs/vgk-entry-disassembly.txt`. A análise complementar do PE é reproduzível por `work/vanguard-estudo/inspect_driver_details.py`, usando Python e a cópia `work/vanguard-estudo/samples/vgk.sys`. Esses caminhos são relativos à pasta deste estudo. O script e o `objdump` leem os bytes e não solicitam carregamento do driver. Os binários não estão incluídos nos entregáveis.
