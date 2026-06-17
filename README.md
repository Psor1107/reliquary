# Reliquary 🗝️

Um Registry de Segredos local e remoto focado em **Segurança (Safe)** e **Developer Experience (Smooth)**. 

O Reliquary resolve o problema do vazamento constante de senhas, chaves de API e tokens em arquivos `.env` ou históricos de shell. Ele unifica o armazenamento criptografado em repouso num único cofre local (SQLite) e permite que essas credenciais sejam consumidas dinamicamente sob demanda por ferramentas de automação (como `uv`, `npm` ou `Ansible`), sem deixá-las expostas em texto plano no disco.

---

## 🏗️ Arquitetura e Decisões de Design

O projeto foi construído respeitando a separação de responsabilidades e o Princípio de Responsabilidade Única (SRP), isolando completamente as interfaces, a validação de configurações, o motor criptográfico e o gerenciamento de processos do Sistema Operacional.

```text
reliquary/
├── app.py          # View: Interface Gráfica desktop rica (CustomTkinter)
├── vault.py        # Controller: Orquestração de negócio e controle de sessão em RAM
├── crypto.py       # Lógica: Implementação estrita de KDF (Argon2id) e AEAD (Fernet/AES)
├── database.py     # Model: Camada de persistência e CRUD (SQLite puro)
├── contract.py     # Manifesto: Parsing e validação estrita de contratos YAML
├── launcher.py     # Executor: Isolamento de memória e spawn de subprocessos (Wrapper)
└── cli.py          # Maestro: Ponto de entrada oficial e orquestração do CLI

```

### O Modelo de Ameaças (Segurança)

Para garantir a máxima proteção local (contra cópia não autorizada do banco de dados ou despejos simples de memória):

1. **Derivação de Chave Resistente a Hardware:** A Master Password do usuário NUNCA é armazenada. O sistema utiliza **Argon2id** (`argon2-cffi`) combinado com um *Salt* único de 16 bytes. Este algoritmo foi calibrado (exigindo ~64MB de RAM) para atrasar severamente ataques de força bruta utilizando GPUs.
2. **Criptografia Autenticada (AEAD):** Os segredos são encriptados utilizando o padrão **Fernet** (AES-128-CBC acoplado a um HMAC-SHA256), garantindo tanto a confidencialidade quanto a integridade do texto cifrado.
3. **Validação Rápida via Verifier:** Para verificar se a senha digitada está correta sem a necessidade de expor ou descriptografar todo o banco de dados, utilizamos um `verifier` em HMAC.
4. **Sessão em Memória:** A chave derivada existe apenas na memória RAM enquanto a sessão está ativa (Unlocked) e é destruída instantaneamente no comando de bloqueio (Lock).

---

## 🚀 Como Executar

**Requisitos:** Python 3.10+

### Instalação e Configuração

```bash
# 1. Clone o repositório e acesse a pasta do projeto
cd visio

# 2. Crie e ative um ambiente virtual isolado
python -m venv .venv

# No Windows:
.venv\Scripts\activate
# No Linux / macOS:
source .venv/bin/activate

# 3. Instale as dependências
pip install -r requirements.txt

```

### Interface de Gestão (GUI Desktop)

Para a gestão diária (criar o cofre, adicionar caminhos e visualizar segredos), o Reliquary possui uma interface Desktop fluida que roda de forma assíncrona para não travar a UI durante o processamento pesado do Argon2id:

```bash
python -m reliquary

```

*O arquivo `registry.db` será criado automaticamente na raiz do projeto na primeira execução.*

---

## 🔌 Consumo e Integrações (O Motor)

O grande diferencial do Reliquary está na sua capacidade de atuar como um **Wrapper/Injetor de Ambientes**. Em vez de salvar chaves secretas em arquivos `.env` locais (vulneráveis a vazamentos), as ferramentas externas consomem os dados diretamente da memória RAM através de um contrato de manifesto YAML.

O `launcher.py` do Reliquary cria uma bolha invisível e isolada de variáveis de ambiente no Sistema Operacional, executa o comando alvo (como scripts em Node, Python, etc.) e descarta as chaves da memória assim que o processo termina.

**Exemplo de consumo automatizado via CLI:**

```bash
# Execução padrão (Usa o secrets.yml da pasta atual ou da /client).
# A senha mestra é opcional na linha de comando — o CLI vai pedir com input invisível
# se omitida e armazenará em cache por 15 minutos.
python -m reliquary.cli -- python client/app_alvo.py

# (Opcional, desencorajado) Fornecer a senha inline — pode vazar no histórico do shell:
python -m reliquary.cli --password minha_senha_mestra -- python client/app_alvo.py

```

### Parâmetros Avançados de Linha de Comando:

O injetor é totalmente flexível e aceita caminhos customizados para se adaptar a diferentes esteiras de CI/CD ou estruturas de repositório:

```bash
# Especificando um manifesto YAML customizado
python -m reliquary.cli --password "..." --secrets-file ./outro/secrets.yml -- python client/app_alvo.py

# Especificando um arquivo de banco de dados específico
python -m reliquary.cli --password "..." --db-path ./custom_registry.db -- python client/app_alvo.py

```

---

*Desenvolvido para o Desafio Técnico de Infraestrutura - Visio.IA.*
