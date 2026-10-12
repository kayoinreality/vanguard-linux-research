# Leitura estática limitada do alvo chamado pela entrada de vgk.sys

Referência: 12/10/2026, America/Sao_Paulo. Nenhum driver foi carregado, executado, alterado ou desempacotado em execução.

**O alvo `0x1461B9E27` contém um salto direto de cinco bytes para `0x146247471`.** Não foi encontrado registro `RUNTIME_FUNCTION` que cubra o primeiro endereço no diretório de exceções declarado. O segundo endereço coincide com o início de um registro candidato; seus primeiros 16 bytes mostram oito `push` e `sub RSP,0x28`, seguidos por uma chamada direta e `jmp RAX`. A finalidade desse encadeamento não foi identificada.

As evidências novas estão na [desassemblagem](vgk-callee-estatico.txt) e no [JSON com limites, hashes e transferências observadas](vgk-callee-estatico.json). Os relatórios anteriores não foram alterados.

## Fonte e limites exatos

Fonte: cópia preservada `work/vanguard-estudo/samples/vgk.sys`, com 109.721.528 bytes e SHA-256 `8ba32cfbc4a07fd41a082344e23e312515ffafef0e568ba72e7d33e83b558f13`. O hash foi recalculado localmente e na cópia `/home/lab/vanguard-study/vgk.sys` do Arch; ambos coincidem. Máquina declarada: AMD64; base preferida: `0x140000000`.

Todos os VAs abaixo são calculados com a base preferida, sem medição de endereços de uma sessão em execução. O mapeamento para disco usa `offset_raw_da_seção + (RVA - RVA_da_seção)`, limitado aos bytes presentes no arquivo. [Especificação PE/COFF](https://learn.microsoft.com/en-us/windows/win32/debug/pe-format).

| Janela | VAs com fim exclusivo | Offsets com fim exclusivo | Bytes | Seção PE |
|---|---|---|---|---|
| Alvo inicial | `[0x1461B9E27, 0x1461BA027)` | `[0x0617E427, 0x0617E627)` | 512 | `.riot1` |
| Destino do primeiro salto | `[0x146247471, 0x1462474F1)` | `[0x0620BA71, 0x0620BAF1)` | 128 | `.riot1` |

SHA-256 das janelas: `75865b00cf45e41bde1c253da1a0c20033288b57cd2ca7104a27ac5c24a34608` e `d0dc030c96d847ca10b7af42cb19f5b6706775e97e5d9664195c3f4d3c607bb9`, respectivamente. A leitura do código ficou restrita a esses 640 bytes, além da conferência dos cinco bytes da chamada já identificada na entrada. Nenhum novo destino de chamada ou salto foi seguido depois da extensão autorizada de 128 bytes.

A desassemblagem usa GNU objdump 2.47 em duas cópias binárias delimitadas. Todos os bytes exibidos, incluindo linhas de continuação, foram conferidos como contíguos e iguais aos bytes das janelas de origem. O nome `.data` exibido pelo objdump é uma seção sintética do modo `-b binary`; o mapeamento PE real é `.riot1`.

## Conferência do encadeamento de endereços

Na entrada anteriormente examinada, a chamada em `0x1461C2151` contém `E8 D1 7C FF FF`, com deslocamento relativo assinado `-0x832F`:

```text
0x1461C2151 + 5 - 0x832F = 0x1461B9E27
```

No endereço chamado, os bytes iniciais são `E9 45 D6 08 00`. Interpretando `E9 rel32` em x86-64, o deslocamento é `+0x8D645`:

```text
0x1461B9E27 + 5 + 0x8D645 = 0x146247471
```

São cálculos dos operandos presentes no arquivo. Não identificam nomes de funções, contratos, dados recebidos ou valores de registradores em execução.

## Registros candidatos de exceção e unwind

O diretório de exceções declara RVA `0x06105128`, offset `0x060C9728`, tamanho 434.472 bytes, na seção `.riot0`. Foram consultados os 36.206 registros de 12 bytes desse diretório; nenhum intervalo declarado contém RVA `0x061B9E27`.

O registro anterior mais próximo termina em `0x061B7410`; o próximo começa em `0x061BA170`. A ausência de cobertura não prova que o salto inicial seja dado, nem fornece os limites de uma função. O formato x64 permite código sem um registro de unwind em determinadas situações; não foi atribuída essa classificação ao trecho. [Formato e procedimento de unwind da Microsoft](https://learn.microsoft.com/en-us/cpp/build/exception-handling-x64?view=msvc-170).

O destino do salto tem exatamente um registro candidato:

| Campo | Valor observado |
|---|---|
| Índice na tabela, começando em zero | 30.372 |
| Offset do registro de 12 bytes | `0x061226D8` |
| Bytes do registro | `71 74 24 06 04 7A 24 06 B8 4C 6F 06` |
| Intervalo RVA | `[0x06247471, 0x06247A04)`; 1.427 bytes |
| Posição do destino | Coincide com `BeginAddress`; não entra no meio desse registro |
| RVA / offset da informação de unwind | `0x066F4CB8` / `0x066B92B8`, seção `.riot1` |
| Cabeçalho de quatro bytes | `01 10 09 00` |
| Campos decodificados do cabeçalho | Versão 1; flags 0; prólogo 16 bytes; 9 slots de dois bytes; frame register e offset 0 |

Os primeiros 16 bytes desassemblados abrangem `push R15,R14,R13,R12,RSI,RDI,RBP,RBX` e `sub RSP,0x28`. Esse tamanho coincide com o campo de prólogo. Os nove slots de unwind não foram interpretados; portanto, a correção da recuperação de pilha e registradores não foi validada. O intervalo de 1.427 bytes é declarado pela tabela e não foi analisado inteiro. Registros com formato consistente continuam sendo pistas de localização, sem estabelecer propósito ou cobertura real de execução.

## Chamadas e ramos observados

No prefixo do destino `0x146247471`, após as operações de pilha, foram decodificados:

| VA da instrução | Instrução | Limite da interpretação |
|---|---|---|
| `0x146247481` | `call 0x1461D5D41` | Destino direto calculado dos bytes; corpo não examinado |
| `0x146247486` | `jmp RAX` | Destino indireto depende do registrador; não foi recuperado |

As demais chamadas abaixo aparecem na decodificação linear **depois de `jmp RAX`**. Não foi demonstrado que sejam alcançadas por esse prefixo:

| VA da instrução | Destino decodificado |
|---|---|
| `0x146247488` | `call 0x1461C4088` |
| `0x146247493` | `call 0x1461C5500` |
| `0x146247498` | `call 0x146247488` |
| `0x1462474AD` | `call 0x1461C3910` |
| `0x1462474C1` | `call 0x1461C5500` |
| `0x1462474C6` | `call 0x1462474A7` |

A mesma decodificação posterior mostra ramos condicionais e saltos diretos, inclusive destinos dentro e fora da janela de 128 bytes. Seus endereços e bytes estão no JSON, classificados como contexto linear após salto indireto. Não foram interpretados como decisões de uma função nem seguidos.

Na janela inicial de 512 bytes, o salto `E9` não tem queda normal para os bytes seguintes. A decodificação desses bytes produz 17 linhas com `(bad)`, instruções diversas e sequências de `NOP`. Esse contexto não sustenta tratá-lo como um bloco contínuo de código executado: pode incluir dados, outro alinhamento ou regiões alcançadas por caminhos não examinados. Não foi inferido mecanismo de proteção, cifragem, ofuscação ou empacotamento a partir desses resultados.

O JSON registra 47 transferências de controle produzidas pela decodificação linear das duas janelas. **47 não é uma contagem de chamadas ou ramos comprovadamente executados.** As diretivas `.byte` próximas ao fim da janela de 128 bytes também não foram tratadas como prova de instruções válidas ou inválidas do corpo completo; a janela é parcial.

## Limites

Esta etapa confirma o mapeamento dos bytes e os destinos de operandos diretos indicados. Não recupera o valor de `RAX`, não identifica importações usadas pelas chamadas, não valida os contratos do kernel e não demonstra inicialização do Vanguard no Linux. Não houve leitura de outros drivers, processos ou memória do host. A comparação com formatos documentados descreve estruturas e campos; não nomeia a intenção arquitetural do programa.
