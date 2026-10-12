# Laboratório Arch Linux

Preparação em 12 de outubro de 2026, America/Sao_Paulo.

A configuração está pronta para criar a VM **Arch-Lab-Vanguard** no Hyper-V que já está instalado neste computador. A sessão do Codex não tem os privilégios de administrador exigidos pelo Hyper-V. O arquivo `iniciar-laboratorio.ps1` solicita essa autorização ao Windows e inicia a preparação em segundo plano.

**Estado atual: instalado e validado.** A VM iniciou pelo disco virtual com kernel `7.2.9-arch1-1`. O acesso SSH e os testes de C, Rust e Python passaram em 12/10/2026 às 01:02, America/Sao_Paulo. Foi criado o checkpoint **Arch instalado e laboratorio validado**.

Para entrar no sistema já preparado, execute `abrir-laboratorio.ps1`. Ele usa a chave local e verifica a identidade SSH da VM. O usuário é `lab`; o acesso inicial é pelo terminal, sem interface gráfica.

## Configuração prevista

- Hyper-V Geração 2, com UEFI.
- 4 processadores virtuais e memória entre 2 e 4 GiB. A primeira tentativa com 4 GiB não iniciou por falta de RAM disponível no Windows; o início foi ajustado para 2 GiB.
- Um único disco virtual dinâmico de 50 GiB, salvo na subpasta `vm` deste laboratório. O tamanho máximo não é reservado de uma vez no disco físico.
- Rede pelo switch NAT padrão já existente do Hyper-V.
- Secure Boot desativado somente no firmware desta VM, para inicializar a ISO Arch. A configuração do firmware físico do computador não é alterada.
- Arch sem interface gráfica nesta primeira etapa; acesso por SSH com o usuário `lab` e uma chave criada exclusivamente para este laboratório.
- GCC, Rust/Cargo, Python, leitor PE, radare2, GDB e strace.

O instalador só aceita o ambiente live Arch dentro de Hyper-V, quatro CPUs e um único disco de exatamente 50 GiB sem partições ou assinaturas existentes. A instalação usa uma ISO auxiliar `CIDATA`, que contém o instalador e a chave **pública**. A chave privada permanece em `work\arch-lab\keys`, com acesso restrito no Windows.

## Mídias verificadas

Foi baixada a ISO oficial `archlinux-2026.10.01-x86_64.iso`, com o SHA-256 publicado pelo Arch:

`684ded26c63240ff4a41e8c25ee84ea6da233f557364821f13d12c2b0a9059a5`

A assinatura PGP foi validada com a chave obtida via WKD para `pierre@archlinux.org`, fingerprint `3E80CA1A8B89F69CBA57D98A76A5EF9054449A5C`. O verificador não possui uma cadeia pessoal de confiança para essa identidade; a origem usada foi o WKD do domínio oficial. [Versão oficial](https://archlinux.org/releng/releases/2026.10.01/), [Verificação de downloads](https://archlinux.org/download/).

O procedimento `CIDATA` para configurar o live por cloud-init está documentado pelo Arch. [Instalação via SSH](https://wiki.archlinux.org/title/Install_Arch_Linux_via_SSH).

## Iniciar e acompanhar

Execute `iniciar-laboratorio.ps1` pelo PowerShell. O Windows exibirá a autorização de administrador. Se ela for aceita, o helper cria a VM e começa a instalação automática. Não é necessário fornecer senha de conta Riot ou senha Linux.

O estado real fica em `status.json`:

| Estado | Significado |
| --- | --- |
| `awaiting_admin` | Mídias e configuração prontas; criação ainda não iniciada |
| `installing` | VM iniciada; instalação e acesso SSH ainda em andamento |
| `ready` | Sistema instalado, acesso SSH e ferramentas validados; checkpoint criado |
| `attention` | Tempo de espera terminou; precisa conferir o console e os logs |
| `failed` | Houve erro; a mensagem indica o ponto da falha |

Os registros do Windows ficam em `host-setup.log`. Depois do acesso SSH, o resultado dos testes fica em `guest-validation.log` e a lista de pacotes em `guest-packages.txt`. Dentro do Arch, os registros ficam em `/var/lib/arch-lab`.

A validação compila e executa pequenos programas nossos em C e Rust, carrega o leitor PE do Python e verifica os serviços necessários. O helper só declara `ready` após esses testes. Na preparação inicial foram verificados a sintaxe dos scripts, as mídias e o conteúdo da ISO auxiliar; isso não substitui a inicialização e os testes reais dentro da VM.

Durante esta instalação, o agente de verificação de pacotes manteve a raiz ocupada ao final do preparo. O processo foi identificado dentro da VM, encerrado e a inicialização pelo disco foi concluída. A rotina de preparo foi corrigida para encerrar apenas agentes ligados à chave de pacotes dessa instalação. Também foi ajustada a troca da identidade SSH entre o ambiente live e o sistema instalado.

Este ambiente serve para pesquisa e protótipos próprios. A criação da VM não demonstra execução do LoL no Linux nem compatibilidade de um substituto do Vanguard.
