# Reliquary 🗝️

Um Registry de Segredos local e remoto focado em **Segurança (Safe)** e **Developer Experience (Smooth)**. 

O Reliquary resolve o problema do vazamento constante de senhas, chaves de API e tokens em arquivos `.env` ou históricos de shell. Ele unifica o armazenamento criptografado em repouso num único cofre (SQLite) e permite que essas credenciais sejam consumidas dinamicamente sob demanda por ferramentas de automação (como `uv`, `npm` ou `Ansible`), sem deixá-las expostas em texto plano no disco.

---

## 🏗️ Arquitetura e Decisões de Design

O projeto foi construído respeitando a separação de responsabilidades e o Princípio de Inversão de Dependências (SOLID), isolando completamente as interfaces, o motor criptográfico e o armazenamento. O banco de dados opera sob uma interface via `Protocol`, permitindo plugar repositórios locais ou remotos sem alterar o núcleo de segurança.

```text
reliquary/
├── app.py          # View: Interface Gráfica desktop rica (CustomTkinter)
├── vault.py        # Controller: Orquestração de negócio e controle de sessão em RAM
├── crypto.py       # Lógica: Implementação estrita de KDF (Argon2id) e AEAD (Fernet/AES)
├── database.py     # Local Storage: Camada de persistência (SQLite puro)
├── remote.py       # Remote Storage: Cliente HTTP para consumo de API externa
├── storage.py      # Interface: Contrato de armazenamento (Dependency Inversion)
├── contract.py     # Manifesto: Parsing e validação estrita de contratos YAML
├── launcher.py     # Executor: Isolamento de memória e spawn de subprocessos
└── cli.py          # Maestro: Ponto de entrada oficial e orquestração do CLI
server.py           # Entrypoint: API FastAPI para o modo distribuído

```

### O Modelo de Ameaças (Segurança e Zero-Knowledge)

Para garantir a máxima proteção local e remota:

1. **Derivação de Chave Resistente a Hardware:** A Master Password do usuário NUNCA é armazenada. Utilizamos **Argon2id** (`argon2-cffi`) combinado com um *Salt* único de 16 bytes.
2. **Criptografia Autenticada (AEAD):** Padrão **Fernet** (AES-128-CBC acoplado a um HMAC-SHA256).
3. **Criptografia Ponta-a-Ponta (E2EE):** No modo Servidor Remoto, a API atua como *Zero-Knowledge*. O servidor armazena e trafega apenas o *ciphertext* em Base64. A chave de sessão e o texto plano nunca saem da memória RAM do cliente executando o CLI.

---

## 🚀 Como Executar

**Requisitos:** Python 3.10+

### Instalação e Configuração

```bash
# 1. Clone o repositório e acesse a pasta do projeto
cd visio

# 2. Crie e ative um ambiente virtual isolado
python -m venv .venv
source .venv/bin/activate  # No Windows: .venv\Scripts\activate

# 3. Instale as dependências
pip install -r requirements.txt

```

### Interface de Gestão (GUI Desktop)

Para a gestão diária local:

```bash
python -m reliquary

```

---

## 🌐 Modo Servidor (Distribuído)

O Reliquary pode operar em rede para o compartilhamento seguro de segredos entre uma equipe.

**1. Subindo a API (Servidor):**

```bash
# Inicia o servidor FastAPI na porta 8000
uvicorn server:app --port 8000

```

**2. Consumindo via Cliente Remoto:**

```bash
python -m reliquary.cli --remote-url http://localhost:8000 -- python client/app_alvo.py

```

---

## 🔌 Consumo Local e Integrações (Injetor)

O `launcher.py` atua como um **Wrapper de Ambientes**, consumindo o contrato `secrets.yml` e injetando as variáveis estritamente na memória do processo filho.

```bash
# Execução padrão (Usa o secrets.yml local)
# A senha mestra usa input invisível e cache de sessão seguro por 15 minutos.
python -m reliquary.cli -- python client/app_alvo.py

# Especificando um manifesto YAML customizado e um banco específico
python -m reliquary.cli --secrets-file ./outro/secrets.yml --db-path ./custom_registry.db -- python client/app_alvo.py

```

---

*Desenvolvido para o Desafio Técnico de Infraestrutura - Visio.IA.*
