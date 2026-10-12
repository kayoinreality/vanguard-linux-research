# Registro da publicação

A publicação inicial foi preparada a partir do material local existente em 12 de outubro de 2026. Os arquivos privados mantidos fora do repositório estão descritos abaixo.

## Continuação em 12/10/2026

A retomada acrescenta evidências sanitizadas de reparo do lançador e avanço da atualização, uma avaliação do REA por leitura de fontes primárias e critérios de continuação. O coletor autoral de estado foi atualizado para reconhecer o ASAR obtido no reparo oficial e exportar campos públicos adicionais. O manifesto reflete os arquivos incluídos nesta continuação; não houve alteração do protótipo ArchGuard.

## Material preservado

Relatórios, inventários PE, hashes e versões de referência, desassemblagem limitada, matriz de interfaces, código original do ArchGuard e seus resultados históricos de teste, scripts autorais de coleta/análise, wrappers de compatibilidade de interface e metadados técnicos da VM.

As informações refletem coletas em momentos diferentes. Consulte o diagnóstico mais recente para o estado de lançamento. O login no cliente, a presença de arquivos e os testes do ArchGuard não demonstram entrada em partida nem aceitação pelo Vanguard.

## Sanitização

- Caminhos com o perfil Windows pessoal foram substituídos por uma raiz neutra ou por referências relativas.
- O endereço privado da VM foi substituído por `192.0.2.10`, reservado para documentação.
- A identificação da conta Riot e as capturas de tela ficaram somente no ambiente privado.
- Trechos brutos de bundles de terceiros no campo `context` dos resultados de busca estática foram omitidos; nomes, offsets e metadados técnicos permanecem.
- Dois caminhos fixos de scripts foram adaptados para PowerShell 7 e para o diretório do checkout.
- Diagnósticos operacionais de SSH, logs brutos de instalação/host e saída de túnel foram excluídos. Logs técnicos pequenos previamente sanitizados e resultados de validação foram preservados.

O manifesto informa SHA-256 do arquivo textual de origem e do arquivo publicado. Sanitização e normalização de novas linhas podem alterar o hash do documento; os hashes dos binários estudados, registrados dentro dos inventários, foram preservados.

## Mantido somente localmente

- Chave SSH privada, chave pública local e registros de confiança SSH.
- Discos, snapshots e estado da VM (~93,6 GiB), ISOs e mídia de inicialização.
- Executáveis, driver, bibliotecas, instalador e demais amostras proprietárias Riot; ASAR original e pequenas janelas binárias da análise.
- Capturas da conta/interface, frames de console, caches, diretórios de dependências e arquivos de execução temporária.
- ZIP anterior do ArchGuard, que duplicava os fontes; os fontes publicados são a cópia revisada.

As exclusões são parte da preparação para publicação pública. O repositório não é uma cópia integral da máquina virtual ou da sessão autenticada.
