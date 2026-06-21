# 🛡️ Reliquary

Reliquary é um injetor de segredos agnóstico e um gerenciador de cofres locais. Ele atua como uma ponte segura entre os seus segredos (criptografados *at-rest*) e as suas aplicações ou pipelines de CI/CD.

Em vez de espalhar arquivos `.env` em texto plano pelas máquinas da equipe, o Reliquary centraliza as credenciais em um banco de dados local (ou remoto) e as injeta diretamente na memória (`os.environ`) dos processos filhos durante a execução, orientado por um contrato YAML.

## 📦 Features Principais
* **Injeção Agnóstica:** Funciona com Node.js, Python, automações Bash/Batch ou qualquer processo do Sistema Operacional. Sem plugins, sem SDKs amarrados ao código.
* **Storage Abstraído:** Arquitetura orientada a interfaces. O cofre pode ser um SQLite local ou um servidor remoto consumido via API.
* **Client-Side Encryption:** Criptografia simétrica robusta local; a *Master Password* nunca é enviada ao servidor remoto e nunca é armazenada junto com os dados.
* **Sessões Locais (Host-Bound):** Cache efêmero atrelado à máquina para uma *Developer Experience* (DX) fluida, mitigando a exposição passiva de credenciais em disco.

---

## 🚀 Quickstart & Guia de Uso

### 1. Instalação
Clone o repositório e instale as dependências:
```bash
git clone https://github.com/Psor1107/reliquary
cd reliquary
pip install -r requirements.txt

```

### 2. Inicializando o Cofre (GUI)

Para interagir com o cofre visualmente, criar sua *Master Password* e cadastrar chaves, inicie o aplicativo desktop:

```bash
python -m reliquary

```

*Caso queria utilizar os exemplos:* Crie as chaves `dev/api_key`, `dev/db_mock` e `prod/db_pass` para testar os scripts pré-configurados.

### 3. O Contrato (secrets.yml)

O Reliquary utiliza um arquivo YAML no repositório do seu projeto para mapear o que a aplicação espera versus onde o segredo está no cofre. Veja o arquivo em `examples/demo_secrets.yml`:

```yaml
env:
  API_KEY: "dev/api_key"
  DB_MOCK_URL: "dev/db_mock"
  PROD_DB_PASSWORD: "prod/db_pass"

```

### 4. Demonstração: O Injetor Universal

A pasta `examples/` contém três serviços simulados em linguagens diferentes consumindo o mesmo contrato YAML. O Reliquary envelopa a execução deles:

**Testando um Backend (Python):**

```bash
python -m reliquary.cli --secrets-file examples/demo_secrets.yml -- python examples/backend_service.py

```

**Testando um Frontend (Node.js):**

```bash
python -m reliquary.cli --secrets-file examples/demo_secrets.yml -- node examples/frontend_service.js

```

**Testando Automação/Infra (Batch):**

```bash
python -m reliquary.cli --secrets-file examples/demo_secrets.yml -- examples\deploy_infra.bat

```

*(Nota: Graças ao cache de sessão, você só precisará digitar a senha na primeira execução).*

### 5. Modo API Remota (Servidor de Segredos)

O Reliquary pode atuar como um provedor de segredos em rede. Para iniciar o servidor e rodar a suíte de testes de integração E2E:

```bash
# Terminal 1 (Inicia o Servidor)
uvicorn server:app --port 8000   

# Terminal 2 (Roda a bateria de testes remotos)
python -m examples.test_remote
```

Para usar o servidor remoto no CLI, inclua `--remote-url`:

```bash
python -m reliquary.cli --remote-url http://localhost:8000 --secrets-file examples/demo_secrets.yml -- python examples/app_alvo.py
```

---

## 🧠 Arquitetura e Modelo de Ameaças

O design do Reliquary foi pautado no equilíbrio entre segurança rigorosa e fluidez de uso no dia a dia do desenvolvedor (DX).

### 1. Injeção a nível de OS (Agnosticismo)

Para evitar o acoplamento de bibliotecas (como o `dotenv` faz), o módulo `launcher.py` utiliza o módulo `subprocess` do Python. Ele avalia o contrato YAML, descriptografa os segredos em tempo real e orquestra o *spawn* do processo alvo (seja ele o `npm`, `uv` ou scripts de automação). Os segredos são disponibilizados apenas ao processo filho através de variáveis de ambiente durante sua execução.

### 2. Inversão de Dependência (Storage)

O núcleo de regras de negócios (`vault.py`) não possui conhecimento de como os dados são salvos. O protocolo abstrato em `storage.py` permite que o cofre alterne nativamente entre salvar no disco via `SQLiteStorage` (`database.py`) ou consultar a rede via `RemoteAPIStorage` (`remote.py`).

### 3. Criptografia Master Password-Based
Os dados persistentes (registry.db) são protegidos pelo protocolo Fernet. A chave criptográfica é derivada dinamicamente através do algoritmo **Argon2id** (configurado com custo de memória e paralelismo para dificultar ataques locais de dicionário/força-bruta). A *Master Password* não é armazenada; o desbloqueio do banco é validado por um *Verifier* em HMAC.

### 4. Gestão de Sessão (Host-Bound Cache)
Para evitar que o desenvolvedor digite a senha a cada comando no terminal, foi implementado um cache em `.session`. 
Para mitigar a vulnerabilidade de senhas armazenadas em texto plano (cenário de abandono ou *hard-shutdowns*), a sessão é **criptografada com uma chave derivada localmente de atributos da máquina** (MAC Address + User ID). Se o arquivo for acidentalmente exposto ou movido para outro hardware, a decodificação falha instantaneamente. O arquivo possui validação de TTL passivo de 15 minutos e é destruído na leitura se estiver expirado.

### 5. Pipelines Efêmeros (CI/CD)

O Reliquary foi desenhado para atuar em automações sem interação humana. Na pasta `.github/workflows`, a *action* de CI demonstra a integração de uma variável do *GitHub Secrets* para popular e consumir o banco SQLite (`seed_ci.py`), provando a viabilidade do fluxo em ambientes descartáveis.

---

## 🏗️ Evoluções e Decisões de Escopo

Dadas as restrições de tempo, as seguintes escolhas de escopo e *trade-offs* norteiam as futuras evoluções:

1. **API Remota e Autenticação:** A comunicação atual com o `server.py` adota uma premissa de *Trust Zone* (rede local segura). Para um ambiente de produção em nuvem, a adição de autenticação via mTLS ou middlewares com JWT é fundamental antes de servir o blob criptografado.
2. **Testes Unitários:** A prioridade atual foi validar as pontas da arquitetura com testes de integração (`test_remote.py` e validação do cache local). A próxima etapa de maturidade exigiria uma suíte formal via `pytest` utilizando mocks para I/O e *subprocess*.
3. **Distribuição do Pacote:** O Injetor atual opera via execução de módulo do Python (`python -m reliquary.cli`). Empacotar o projeto utilizando `uv` ou `Poetry` com entrypoints nativos (permitindo comandos globais diretos como `reliquary run -- npm start`) poliria a experiência final de distribuição.