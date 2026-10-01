================================
PHASE 3: REFACTORING COMPLETE
================================
## Strategy
A) Decomposição completa: o monolito de 4 arquivos (app.py, controllers.py, models.py, database.py) foi dividido por domínio nas camadas da §4 do mvc-guidelines; `controllers.py` e `models.py` da raiz foram removidos.

## New Project Structure
```
code-smells-project/
├── app.py                       # Entry point: create_app() + app = create_app() + __main__
├── config/
│   └── settings.py              # Config: Settings lidas do ambiente
├── database.py                  # Database: conexão por requisição (flask.g), schema, seed com hash
├── models/                      # Model: SQL parametrizado + regras de domínio
│   ├── produto_model.py
│   ├── usuario_model.py         # hash/verificação de senha, serializador sem senha
│   ├── pedido_model.py          # pedido transacional, listagem com JOIN, totais, calcular_desconto
│   └── sistema_model.py         # contagens do health, limpeza do reset
├── controllers/                 # Controller: fluxo do caso de uso + validação de entrada
│   ├── validacao.py             # obter_json, validar_produto, validar_itens_pedido
│   ├── produto_controller.py
│   ├── usuario_controller.py
│   ├── pedido_controller.py
│   ├── relatorio_controller.py
│   └── sistema_controller.py    # index, health, reset
├── views/                       # View: Blueprints por domínio, só delegam (URLs inalteradas)
│   ├── __init__.py              # register_blueprints(app)
│   ├── produto_routes.py
│   ├── usuario_routes.py
│   ├── pedido_routes.py
│   ├── relatorio_routes.py
│   └── sistema_routes.py
├── services/
│   └── notificacao_service.py   # Service: notificações de pedido (simuladas via logging)
├── middlewares/
│   ├── error_handler.py         # Middleware: AppError + handlers centralizados
│   └── auth.py                  # Middleware: require_admin_token (Bearer ADMIN_TOKEN)
├── utils/
│   └── constants.py             # Utils: categorias, status, faixas de desconto, limites
├── .env.example
├── README.md
└── requirements.txt             # inalterado (werkzeug.security vem com o Flask)
```

## Findings Resolved
| ID | Severity | Anti-pattern | Status | How (PT-xx) |
|----|----------|--------------|--------|-------------|
| F-01 | CRITICAL | SQL Injection (AP-01) | RESOLVED | PT-01: as 19 queries usam placeholders `?`. A sonda `email = "admin@loja.com' --"` passou de 200 (login como admin) para 401 |
| F-02 | CRITICAL | Credenciais hardcoded (AP-02) | RESOLVED | PT-02: `config/settings.py` + `.env.example`; nenhum segredo literal no código |
| F-03 | CRITICAL | Senha em texto puro (AP-03) | RESOLVED | PT-03: `werkzeug.security` no cadastro, no seed e no login; comparação fora do SQL |
| F-04 | CRITICAL | Exposição de dados sensíveis (AP-04) | RESOLVED | PT-04: `senha` fora das respostas de usuário; `/health` sem `secret_key`/`db_path`/`debug`; e-mail fora dos logs |
| F-05 | CRITICAL | Endpoint sensível sem autenticação (AP-05) | RESOLVED | PT-05: `/admin/query` removido; `/admin/reset-db` com `require_admin_token` |
| F-06 | CRITICAL | God File (AP-06) | RESOLVED | PT-06: decomposição em config/models/controllers/views/services/middlewares/utils |
| F-07 | HIGH | Regra na camada errada (AP-07) | RESOLVED | PT-07: `calcular_desconto` no model, montagem do relatório no controller, notificações em service, SQL fora de controllers e rotas |
| F-08 | HIGH | Estado global mutável (AP-08) | RESOLVED | PT-08: conexão por requisição em `flask.g` com teardown; sem `global` nem `check_same_thread=False` |
| F-09 | HIGH | Multi-etapa sem transação (AP-09) | PARTIAL | PT-09: pedido inteiro em `with db:` (rollback provado) + baixa condicional `estoque >= ?`. Não corrigido de propósito: a exclusão de produto mantém os `itens_pedido` como histórico ("Desconhecido"), como previsto no plano aprovado. A correção completa seria soft delete via coluna `ativo`, que muda o contrato |
| F-10 | MEDIUM | N+1 / queries repetidas (AP-10) | RESOLVED | PT-10: listagem de pedidos em 1 query com JOIN; relatório em 1 agregação; health em 1 query; pedido busca os produtos num único `IN` |
| F-11 | MEDIUM | Código duplicado (AP-11) | RESOLVED | PT-11: `validar_produto` único para create/update; um `to_dict` por entidade; uma função `listar` para pedidos |
| F-12 | MEDIUM | Erro engolido / validação ausente (AP-12) | RESOLVED | PT-12: `middlewares/error_handler.py`; 0 `except Exception` devolvendo `str(e)`; validação de tipo/faixa na borda |
| F-13 | LOW | Magic numbers (AP-14) | RESOLVED | PT-14: `utils/constants.py` |
| F-14 | LOW | Logging inadequado / debug fixo (AP-14) | RESOLVED | PT-14: `logging` com logger por módulo; `FLASK_DEBUG=false` por padrão; 0 `print` |
| F-15 | LOW | Imports sem uso (AP-14) | RESOLVED | PT-14: removidos na decomposição |

## Contract Changes Applied
- `POST /admin/query` removido (agora 404).
- `POST /admin/reset-db` exige `Authorization: Bearer <ADMIN_TOKEN>`: 401 `{"erro","sucesso"}` sem token ou com token inválido; 200 com o token. Sem `ADMIN_TOKEN` no ambiente, a rota fica sempre bloqueada.
- `senha` removido dos itens de `GET /usuarios` e `GET /usuarios/<id>`.
- `secret_key`, `db_path` e `debug` removidos de `GET /health`.
- `PUT /produtos/<id>` aplica a mesma validação do `POST` (categoria inválida: 200 → 400).
- Entrada malformada passa a 400 em vez de 500: `preco_min=abc`, JSON malformado no `/login`, `preco` não numérico, item sem `quantidade`. `quantidade` negativa: 201 → 400. `PUT /pedidos/<id>/status` com pedido inexistente: 200 → 404. Respostas 500 inesperadas trazem `{"erro": "Erro interno do servidor"}` sem detalhe interno.
- Efeito colateral de configuração: `debug` agora é `false` por padrão (`FLASK_DEBUG=true` reativa). O `loja.db` antigo (senhas em texto puro) precisa ser recriado.

## Validation
  ✓ Application boots without errors
  ✓ All endpoints respond as baseline (43/43: 30 idênticas em status + chaves, 13 diferenças, todas mudanças aprovadas)
  ✓ Approved contract changes verified (reset-db: 401 sem token, 401 com token errado, 200 com token; /admin/query 404; senha e segredos ausentes)
  ✓ No deprecation warnings from project code (`python -W default`, antes e depois; só o aviso padrão de "development server" do Werkzeug)
  ✓ No CRITICAL/HIGH anti-patterns remaining (sinais rodados de novo: 0 SQL concatenado com entrada externa, 0 segredo literal, 0 `global`, 0 `print`, 0 `except` genérico; F-09 parcial só na retenção intencional de histórico descrita acima)
  ✓ MVC structure checklist complete (§7: config, models por domínio sem HTTP, views só delegam, controllers sem SQL, handler central, app factory, service isolado, sem estado global, `python app.py` inalterado)

Checagem adicional de conteúdo: o mesmo cenário (3 pedidos, mudança de status, exclusão de produto com pedidos, relatório, buscas, login, validações) foi rodado no código original (extraído do git) e no refatorado. Resultado: **20/20 corpos JSON idênticos**, ignorando `criado_em` e `senha`.
Não há script auxiliar (seed) no projeto: o seed roda no boot via `database.init_app` e foi exercitado em toda execução.
Ciclos de validação: 2 (o 2º após remover a query por item no pedido e o DELETE com nome de tabela concatenado).

## Endpoint Comparison
| Método | Rota | Baseline | Depois | OK |
|--------|------|----------|--------|----|
| GET | / | 200 | 200 | ✓ |
| GET | /health | 200 (com secret_key, db_path, debug) | 200 (sem esses campos) | ✓ aprovado |
| GET | /produtos | 200 | 200 | ✓ |
| GET | /produtos/busca?q=Mouse | 200 | 200 | ✓ |
| GET | /produtos/busca?categoria&preco_min&preco_max | 200 | 200 | ✓ |
| GET | /produtos/1 | 200 | 200 | ✓ |
| GET | /produtos/9999 | 404 | 404 | ✓ |
| POST | /produtos (válido) | 201 | 201 | ✓ |
| POST | /produtos ({}) | 400 | 400 | ✓ |
| POST | /produtos (categoria inválida) | 400 | 400 | ✓ |
| PUT | /produtos/1 | 200 | 200 | ✓ |
| PUT | /produtos/9999 | 404 | 404 | ✓ |
| GET | /usuarios | 200 (com senha) | 200 (sem senha) | ✓ aprovado |
| GET | /usuarios/1 | 200 (com senha) | 200 (sem senha) | ✓ aprovado |
| GET | /usuarios/9999 | 404 | 404 | ✓ |
| POST | /usuarios (válido) | 201 | 201 | ✓ |
| POST | /usuarios (sem senha) | 400 | 400 | ✓ |
| POST | /login (admin) | 200 | 200 | ✓ |
| POST | /login (usuário recém-criado) | 200 | 200 | ✓ |
| POST | /login (senha errada) | 401 | 401 | ✓ |
| POST | /login (SQLi `' --`) | 200 | 401 | ✓ correção F-01 |
| POST | /pedidos (válido) | 201 | 201 | ✓ |
| POST | /pedidos (produto inexistente) | 400 | 400 | ✓ |
| POST | /pedidos (sem estoque) | 400 | 400 | ✓ |
| POST | /pedidos (sem itens) | 400 | 400 | ✓ |
| GET | /pedidos | 200 | 200 | ✓ |
| GET | /pedidos/usuario/2 | 200 | 200 | ✓ |
| PUT | /pedidos/1/status (aprovado) | 200 | 200 | ✓ |
| PUT | /pedidos/1/status (inválido) | 400 | 400 | ✓ |
| GET | /relatorios/vendas | 200 | 200 | ✓ |
| DELETE | /produtos/10 | 200 | 200 | ✓ |
| DELETE | /produtos/9999 | 404 | 404 | ✓ |
| GET | /produtos/busca?preco_min=abc | 500 | 400 | ✓ aprovado (F-12) |
| POST | /login (JSON malformado) | 500 | 400 | ✓ aprovado (F-12) |
| POST | /produtos (preco "abc") | 500 | 400 | ✓ aprovado (F-12) |
| POST | /pedidos (quantidade -1) | 201 | 400 | ✓ aprovado (F-12) |
| POST | /pedidos (item sem quantidade) | 500 | 400 | ✓ aprovado (F-12) |
| PUT | /pedidos/9999/status | 200 | 404 | ✓ aprovado (F-12) |
| PUT | /produtos/1 (categoria inválida) | 200 | 400 | ✓ aprovado (F-11) |
| POST | /produtos/1 (método não permitido) | 405 | 405 | ✓ |
| GET | /rota-inexistente | 404 | 404 | ✓ |
| POST | /admin/query | 200 | 404 | ✓ aprovado (F-05) |
| POST | /admin/reset-db (sem token) | 200 | 401 | ✓ aprovado (F-05) |
| POST | /admin/reset-db (token errado) | n/a | 401 | ✓ aprovado (F-05) |
| POST | /admin/reset-db (com token) | n/a | 200 | ✓ aprovado (F-05) |

## How to run
```bash
pip install -r requirements.txt
python app.py                      # http://localhost:5000
```
Variáveis de ambiente (todas opcionais; ver `.env.example`):
- `SECRET_KEY`: aleatória a cada boot se ausente
- `ADMIN_TOKEN`: necessário para `POST /admin/reset-db` (`Authorization: Bearer <token>`)
- `FLASK_DEBUG` (padrão `false`), `HOST` (`0.0.0.0`), `PORT` (`5000`), `DATABASE_PATH` (`loja.db`), `AMBIENTE` (`producao`)

Apague um `loja.db` criado pela versão anterior para que o seed regrave as senhas com hash.
================================
