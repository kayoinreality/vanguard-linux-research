# Vanguard Linux Research

Arquivo do estudo de engenharia reversa e compatibilidade entre Riot Vanguard, League of Legends e Arch Linux, realizado em 11–12 de outubro de 2026. Inclui os relatórios, inventários, ferramentas de análise e o protótipo original ArchGuard Lab.

## Estado registrado

| Etapa | Evidência disponível |
| --- | --- |
| Binários de referência | Inventário de seis arquivos oficiais, versões, assinaturas, SHA-256, cabeçalhos PE e importações |
| Driver `vgk.sys` | Análise estática da entrada e de duas janelas de código, com desassemblagem e limites documentados |
| ArchGuard Lab 0.1 | Serviço original em espaço de usuário; comunicação por socket Unix e integridade de arquivo próprio; 18 testes de integração registrados |
| Riot Client no Arch | Login observado com interface original em Electron Linux e serviço Windows pelo Wine |
| Instalação e lançamento do LoL | Lançador reparado; avanço de bytes confirmado; `Play` solicitou região Brasil/português, seguida de atualização; abertura do jogo ainda pendente |
| Partida e integração com Vanguard | Compatibilidade ainda não demonstrada; nenhum substituto do Vanguard ou bypass implementado |

Os estados, versões e resultados refletem as coletas datadas. Os testes do ArchGuard e os inventários iniciais são históricos; a retomada do lançador e do download tem novas evidências de 12/10/2026.

## Começar a leitura

- [Estudo inicial e inventário](outputs/estudo-vanguard-arch.md)
- [Matriz inicial de interfaces](outputs/matriz-inicial-vanguard.md)
- [Análise do driver](outputs/analise-driver-vgk.md) e [rotina chamada](outputs/vgk-callee-estatico.md)
- [Viabilidade da interface nativa](outputs/viabilidade-ui-nativa.md)
- [Cliente Riot, instalação e limites](outputs/lol-arch-lab/README.md)
- [Diagnóstico histórico de atualização e lançamento](outputs/lol-arch-lab/diagnostico-atualizacao-launch.md)
- [Retomada e progresso da atualização](outputs/lol-arch-lab/retomada-download.md)
- [Contrato estático do GET do Patcher, progresso e CA local](outputs/patcher-get-contrato-estatico.md)
- [ArchGuard Lab: código, protocolo e testes](outputs/archguard-lab/README.md)
- [Laboratório Arch/Hyper-V](outputs/arch-lab/LEIA-ME.md)
- [Próximos passos e critérios de conclusão](outputs/PROXIMOS_PASSOS.md)
- [Avaliação do REA para análise estática do ASAR e do driver](outputs/avaliacao-rea.md)

## Retomar o estudo

Os fontes do ArchGuard continuam em `outputs/archguard-lab/`; esta etapa não os duplica ou reorganiza. Seu instalador atual exige Arch em Hyper-V e uma conta de laboratório genérica chamada `lab`. A abertura da interface Riot com Electron Linux manteve o backend Windows sob Wine. O jogo ainda não foi validado de ponta a ponta e nenhum substituto do Vanguard foi implementado.

A retomada reparou o lançador preservando os volumes. As consultas GET confirmaram avanço de bytes em etapas de atualização; `Play` mostrou a escolha de região, e Brasil/português foram aplicados. A coleta seguinte mostrou atualização em andamento. A conclusão da instalação, a abertura do jogo e a partida exigem evidências separadas. Consulte a [evidência da retomada](outputs/lol-arch-lab/retomada-download.md) e os [critérios de continuação](outputs/PROXIMOS_PASSOS.md).

O REA foi avaliado por leitura de documentação e código. O piloto proposto começa pela análise estática do ASAR e segue para cópias do driver com Ghidra; nenhuma instalação ou execução do REA foi realizada nesta etapa.

## Organização

```text
outputs/                 Relatórios e evidências técnicas sanitizadas
  archguard-lab/         Protótipo próprio, serviço, instalador e testes
  arch-lab/              Scripts e metadados históricos da VM Arch
  lol-arch-lab/          Wrappers e registros técnicos Riot/Wine/Electron
work/
  vanguard-estudo/       Ferramentas PE, análise estática e coleta sanitizada
  lol-client/            Ferramentas de diagnóstico e preparação do cliente
  arch-lab/              Ferramentas de preparação do laboratório
PUBLICATION.md           Escopo, sanitização e arquivos mantidos localmente
publication-manifest.json Lista dos arquivos publicados e hashes
```

A estrutura original foi conservada para manter as referências entre os scripts. O diretório `work/` contém ferramentas e evidências intermediárias do estudo, não executáveis da Riot.

## Reproduzir etapas

O analisador PE lê um arquivo como dados, sem executá-lo:

```sh
python work/vanguard-estudo/inspect_pe.py --help
```

Para ArchGuard, consulte seu README. Ele usa Python e systemd no Linux; `verify.py` altera temporariamente a amostra própria e deve ser executado apenas na VM dedicada.

As demais ferramentas preservam hipóteses e caminhos do laboratório histórico. Algumas exigem Windows com PowerShell 7/Hyper-V/SSH; outras exigem Arch, Wine, Electron, `pefile`, `capstone` ou `pycdlib`. Binários e pacotes de terceiros devem ser obtidos separadamente de suas fontes oficiais. Não há um instalador completo ou um comando único que reproduza todo o experimento.

Scripts de preparação de discos e instalação modificam a VM dedicada. Leia seus pré-requisitos antes de executá-los. As chaves SSH e as configurações locais precisam ser recriadas; `192.0.2.10` é apenas um endereço de documentação. Caminhos de inventários que começam com `C:\vanguard-linux-research` são referências neutralizadas da coleta, e podem ser adaptados ao checkout.

Este arquivo reúne pesquisa independente. Os nomes Riot Games, Vanguard e League of Legends identificam os componentes estudados; o projeto não é uma distribuição desses produtos nem uma integração aprovada pela Riot.
