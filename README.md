# Reliquary 🗝️

Um Registry de Segredos local e remoto focado em **Segurança (Safe)** e **Developer Experience (Smooth)**. 

O Reliquary resolve o problema do vazamento constante de senhas, chaves de API e tokens em arquivos `.env` ou históricos de shell. Ele unifica o armazenamento criptografado em repouso num único cofre (SQLite) e permite que essas credenciais sejam consumidas dinamicamente sob demanda por ferramentas de automação, sem deixá-las espalhadas em texto plano no disco.

---

## 🏗️ Arquitetura e Decisões de Design

O projeto foi construído respeitando rigorosamente o modelo de Separação de Responsabilidades (MVC), isolando as interfaces (GUI/CLI) das operações criptográficas e do banco de dados.

```text
reliquary/
├── app.py          # View: Interface Gráfica rica (CustomTkinter)
├── vault.py        # Controller: Orquestração de negócio e controle de sessão em RAM
├── crypto.py       # Lógica: Implementação estrita de KDF (Argon2id) e AEAD (Fernet/AES)
└── database.py     # Model: Camada de persistência (SQLite CRUD puro)

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

### Interface de Gestão (GUI)

Para a gestão diária (criar o cofre, adicionar caminhos e visualizar segredos), o Reliquary possui uma interface Desktop fluida que não bloqueia o cursor durante o processamento criptográfico:

```bash
python -m reliquary

```

*O arquivo `registry.db` será criado automaticamente na raiz do projeto na primeira execução.*

---

## 🔌 Consumo e Integrações (O Motor)

O objetivo central do Reliquary é ser consumido por ferramentas externas (npm, uv, Ansible). A arquitetura permite que scripts de linha de comando extraiam os segredos dinamicamente injetando a Master Password, sem depender da interface gráfica.

**Exemplo de consumo bruto via CLI (Prova de Conceito):**

```bash
# Uso: python client/consumidor_cli.py <MASTER_PASSWORD> <PATH_DO_SEGREDO>
python client/consumidor_cli.py minha_senha_mestra dev/aws_key

```

*(O output deste script é estritamente o texto plano do segredo, permitindo ser capturado via `stdout` para injeção de variáveis de ambiente no Linux/Windows).*

---

*Desenvolvido para o Desafio Técnico de Infraestrutura - Visio.IA.*