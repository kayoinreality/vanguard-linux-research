# ArchGuard Lab 0.1

Primeiro protótipo original iniciado na VM Arch-Lab-Vanguard, em 12 de outubro de 2026. Ele demonstra comunicação cliente–serviço e detecção de mudanças em um arquivo próprio do laboratório.

## Resultado verificado

O serviço `archguard-lab.service` está ativo no Arch Linux, com usuário dedicado `archguard-lab`, sem capabilities e com `NoNewPrivileges=yes`. Está habilitado no systemd para iniciar junto com a VM. O cliente usado por `lab` conseguiu consultar o serviço.

Os 18 testes de integração passaram. Eles verificaram alteração de mesmo tamanho, persistência do alerta após reiniciar, referência mantida, exclusão, symlink com conteúdo correto, FIFO, arquivo grande, mensagens inválidas, cliente lento, usuário sem acesso ao socket e restauração do arquivo. O estado final também foi consultado depois da limpeza dos testes.

As evidências estão em `validation.json`, `runtime-state.json` e `service-properties.txt`.

## Consultar

No Windows, execute `consultar-prototipo.ps1` pelo PowerShell. Ele usa a conexão SSH já configurada para essa VM e mostra o estado atual.

Dentro do Arch:

```sh
python /opt/archguard-lab/archguard.py ping
python /opt/archguard-lab/archguard.py status
python /opt/archguard-lab/archguard.py check
systemctl status archguard-lab.service
sudo journalctl -u archguard-lab.service -n 30
```

`status` mostra a última amostragem e sua idade. `check` pede uma verificação nova. `clean` significa que os bytes do arquivo conferiram com a referência naquele instante; uma alteração posterior precisa de outra amostragem. O monitor automático verifica uma vez por segundo.

## Componentes

| Componente | Função |
| --- | --- |
| `archguard.py` | Serviço e cliente em Python, usando bibliotecas padrão |
| `archguard-lab.service` | Inicialização, usuário dedicado e restrições do processo |
| `install.sh` | Instalação no laboratório e criação explícita da primeira referência |
| `verify.py` | Testes comportamentais contra o serviço instalado |

O protocolo original usa JSON, uma mensagem terminada por nova linha por conexão, no socket Unix `/run/archguard-lab/control.sock`. Só há as operações `ping`, `status` e `check`. O cliente não escolhe caminhos de arquivo, não executa comandos no serviço e não pode alterar a referência.

O alvo desta versão é `/var/lib/archguard-lab/demo.bin`, uma amostra de 34 bytes criada pelo instalador. Sua referência SHA-256 fica em `/etc/archguard-lab/manifest.json`, separada do alvo e pertencente a root. Reiniciar o serviço não recalcula essa referência.

O socket tem permissão `0660`, em diretório `0750`; o usuário `lab` foi incluído no grupo do serviço. As mensagens têm limite de 4 KiB e timeout de leitura de 1 segundo. Arquivos têm limite de 16 MiB e a leitura rejeita links simbólicos e arquivos especiais. A comparação registra erro ou indisponibilidade quando não consegue verificar os bytes.

## Limites desta etapa

É uma demonstração em espaço de usuário, com arquivo de teste próprio. Não protege um jogo completo, não atesta o kernel contra um administrador e não implementa um driver de kernel. Também não reproduz interfaces ou protocolos da Riot. A compatibilidade com LoL/Vanguard segue sem demonstração.

O resultado útil para a próxima etapa é uma base local funcionando: inicialização do serviço, permissões, comunicação, verificação, alerta e recuperação. Isso permite estudar contratos específicos em programas próprios, um de cada vez.

## Reinstalação e controles

```sh
sudo bash install.sh
sudo systemctl stop archguard-lab.service
sudo systemctl start archguard-lab.service
```

O instalador preserva a referência existente. Execute `verify.py` com sudo apenas na VM dedicada: os testes alteram temporariamente a amostra própria e restauram seus bytes ao final.

O monitor usa o servidor de sockets Unix e SHA-256 fornecidos pela biblioteca padrão do Python. [socketserver](https://docs.python.org/3.14/library/socketserver.html), [hashlib](https://docs.python.org/3.14/library/hashlib.html).
