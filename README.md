# ODIN

**Assistente pessoal inteligente desenvolvido em Python, LangGraph, LangChain, OpenAI e Supabase.**

O ODIN é um projeto de agente inteligente orientado à conversação, planejamento de tarefas, memória persistente e orquestração controlada.

O projeto adota uma arquitetura com separação entre planejamento, política de segurança, integridade de ações, auditoria e execução.

Consulte a [documentação da arquitetura](docs/ARCHITECTURE.md) para visualizar os fluxos e responsabilidades dos componentes.

## Funcionalidades

- Agente conversacional com LangGraph e OpenAI.
- Planejamento estruturado de tarefas.
- Orquestração de planos e etapas.
- Memória persistente e histórico de conversas com Supabase.
- Política de segurança para classificação de ações.
- Controle de integridade de ações por HMAC.
- Estrutura de aprovações e auditoria.
- Modo consultivo com execução externa bloqueada.
- Testes automatizados com Pytest.

## Arquitetura

| Módulo | Responsabilidade |
|---|---|
| `app/agents` | Agente conversacional e processamento de mensagens |
| `app/planning` | Construção e validação de planos |
| `app/orchestration` | Orquestração de tarefas e etapas |
| `app/executor` | Controle do processamento das ações |
| `app/approvals` | Gerenciamento do fluxo de aprovações |
| `app/security` | Políticas, autenticação e integridade de ações |
| `app/audit` | Registro de eventos de auditoria |
| `app/memory` | Memória persistente e histórico de conversas |
| `app/config` | Carregamento das configurações |

## Tecnologias

- Python 3.12
- LangChain
- LangGraph
- OpenAI API
- Supabase
- PostgreSQL
- Pydantic
- Pytest

## Requisitos

- Python 3.12
- Conta e projeto Supabase configurados
- Chave de API da OpenAI

## Instalação

Clone o repositório:

```bash
git clone https://github.com/brunoluigiragazi-beep/odin.git
cd odin
```

Crie o ambiente virtual:

```bash
python -m venv .venv
```

Ative o ambiente no Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Instale as dependências:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Configuração

Crie o arquivo `.env` a partir do modelo:

```powershell
Copy-Item .env.example .env
```

Preencha as variáveis localmente:

```env
OPENAI_API_KEY=
SUPABASE_URL=
SUPABASE_KEY=
ODIN_ACTION_INTEGRITY_KEY=
ODIN_MODEL=gpt-4.1-mini
```

Nunca publique o arquivo `.env` ou compartilhe suas credenciais.

O projeto utiliza as tabelas e operações do Supabase implementadas nos módulos de memória, aprovação e auditoria. A configuração do banco precisa estar compatível com essas operações.

## Execução

Inicie o agente:

```bash
python main.py
```

### Comandos disponíveis

| Comando | Descrição |
|---|---|
| `/ajuda` | Apresenta os comandos disponíveis |
| `/planejar descrição da tarefa` | Elabora um planejamento consultivo |
| `sair` | Encerra a sessão |

## Segurança e modo de operação

O ODIN está configurado em **modo consultivo**.

Nesse modo:

- O agente pode conversar, analisar, organizar e planejar.
- O planejamento não significa execução.
- Operações externas permanecem bloqueadas.
- O executor mantém o processamento em modo de simulação.
- A administração de aprovações pela interface principal está desativada.

Os módulos de aprovação, auditoria e integridade fazem parte da arquitetura, mas não representam autorização para executar operações externas.

## Testes

Execute os testes unitários:

```bash
python -m pytest -v --ignore=tests/test_supabase_claim_integration.py --ignore=tests/test_supabase_request_integration.py --ignore=tests/test_supabase_decide_integration.py
```

Em 16/11/2026, a suíte unitária executada localmente apresentou:

**75 testes aprovados, sem falhas.**

### Testes de integração

Os três testes abaixo dependem de um Supabase real:

- `test_supabase_claim_integration.py`
- `test_supabase_request_integration.py`
- `test_supabase_decide_integration.py`

Eles criam, alteram e excluem registros nas tabelas de aprovação e auditoria. Execute-os somente em um ambiente de testes isolado, nunca diretamente em um banco de produção.

A integração real com Supabase ainda requer validação específica.

## Estrutura do projeto

```text
odin/
├── app/
│   ├── agents/
│   ├── approvals/
│   ├── audit/
│   ├── config/
│   ├── executor/
│   ├── memory/
│   ├── orchestration/
│   ├── planning/
│   └── security/
├── tests/
├── .env.example
├── .gitignore
├── main.py
└── requirements.txt
```

## Objetivo do projeto

Desenvolver uma arquitetura modular de agente inteligente, com planejamento estruturado, memória persistente, governança de ações e mecanismos de segurança.

O ODIN é um projeto em evolução, com foco em confiabilidade, controle e expansão gradual de capacidades.
