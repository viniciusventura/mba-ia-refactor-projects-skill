================================
PHASE 3: REFACTORING COMPLETE
================================
## Strategy
A) Decomposição completa: o monolito de 4 arquivos (app.py, controllers.py, models.py, database.py) virou camadas MVC por domínio. `controllers.py` e `models.py` da raiz foram removidos.

## New Project Structure
```
code-smells-project/
├── app.py                         # Entry point: create_app() + app = create_app() + __main__
├── config/settings.py             # Config: Settings lidas do ambiente
├── database.py                    # Database: conexão por requisição (flask.g), schema, migrações, seed
├── models/                        # Model: SQL parametrizado + regras de domínio
│   ├── produto_model.py           #   validar(), soft delete, baixa atômica de estoque
│   ├── usuario_model.py           #   hash de senha, serializador sem senha
│   ├── pedido_model.py            #   pedido em transação única, listagem com JOIN, totais agregados
│   ├── relatorio_model.py         #   calcular_desconto() + relatório
│   └── admin_model.py             #   reset do banco em transação
├── controllers/                   # Controller: fluxo do caso de uso + validação de entrada
│   ├── comum.py                   #   ler_json(), eh_inteiro()
│   ├── produto_controller.py
│   ├── usuario_controller.py
│   ├── pedido_controller.py
│   ├── relatorio_controller.py
│   ├── health_controller.py
│   └── admin_controller.py
├── views/                         # View: Blueprints que só ligam URL → controller (+ auth por rota)
│   ├── __init__.py                #   register_blueprints(app)
│   ├── produto_routes.py, usuario_routes.py, pedido_routes.py
│   ├── relatorio_routes.py, health_routes.py, admin_routes.py
├── services/notificacao_service.py   # Service: e-mail/SMS/push (simulados em log)
├── middlewares/
│   ├── error_handler.py           # Middleware: AppError + handler central
│   └── auth.py                    # Middleware: token assinado, require_auth(papel), dono-ou-admin
├── utils/constants.py             # Utils: status, categorias, faixas de desconto, versão
├── requirements.txt               # inalterado (werkzeug.security e itsdangerous já vêm com o Flask)
└── .env.example
```

## Findings Resolved
| ID | Severity | Anti-pattern | Status | How (PT-xx) |
|----|----------|--------------|--------|-------------|
| F-01 | CRITICAL | SQL Injection (AP-01) | RESOLVED | PT-01: as 19 queries usam `?`; a busca monta fragmentos com lista de params; `IN` com marcadores gerados |
| F-02 | CRITICAL | Credenciais hardcoded (AP-02) | RESOLVED | PT-02: `config/settings.py` lê do ambiente; chave aleatória + aviso quando ausente; DEBUG default false; `.env.example` |
| F-03 | CRITICAL | Senha em texto puro (AP-03) | RESOLVED | PT-03: `generate_password_hash` no cadastro e no seed, `check_password_hash` no login, migração no boot |
| F-04 | CRITICAL | Exposição de dados sensíveis (AP-04) | RESOLVED | PT-04: serializador de usuário sem `senha`; `/health` sem `secret_key`/`debug`/`db_path` |
| F-05 | CRITICAL | Endpoint sensível sem auth (AP-05) | RESOLVED | PT-05: token itsdangerous no login; `require_auth`; `/admin/query` removida; 6 rotas admin + 2 dono-ou-admin |
| F-06 | CRITICAL | God File (AP-06) | RESOLVED | PT-06: camadas da §4; arquivos antigos removidos |
| F-07 | HIGH | Leitura de dados de terceiros (AP-05) | RESOLVED | PT-05: `/pedidos` e `/relatorios/vendas` admin; `/pedidos/usuario/<id>` dono ou admin |
| F-08 | HIGH | Regra na camada errada (AP-07) | RESOLVED | PT-07: desconto em `relatorio_model`, categorias em `produto_model`, notificações em service, SQL de health/admin em models |
| F-09 | HIGH | Estado global mutável (AP-08) | RESOLVED | PT-08: conexão em `flask.g` + `teardown_appcontext`; sem `global` nem `check_same_thread=False` |
| F-10 | HIGH | Sem transação + exclusão física (AP-09) | RESOLVED | PT-09: pedido em `with db:` com baixa condicional (rollback testado); soft delete com `removido`/`removido_em`/`removido_por` + migração |
| F-11 | MEDIUM | Query N+1 (AP-10) | RESOLVED | PT-10: listagem de pedidos em 1 query com JOIN; produtos do pedido em 1 `IN`; relatório em 1 agregação |
| F-12 | MEDIUM | Código duplicado (AP-11) | RESOLVED | PT-11: `produto_model.validar` única; `_to_dict` por entidade; `pedido_model.listar(usuario_id=None)` |
| F-13 | MEDIUM | Erro engolido / validação (AP-12) | RESOLVED | PT-12: `register_error_handlers`, nenhum `str(e)` de exceção interna; validação de body/tipos/itens; 404 no status |
| F-14 | LOW | Magic numbers (AP-14) | RESOLVED | PT-14: `utils/constants.py`; `ambiente` via `APP_ENV` |
| F-15 | LOW | Código morto (AP-14) | RESOLVED | PT-14: imports sem uso e `SELECT 1` removidos (verificado por AST: 0 imports sem uso) |
| F-16 | LOW | Logging inadequado (AP-14) | RESOLVED | PT-14: `logging` em todo o projeto, 0 `print`; logs de login/cadastro sem e-mail |

## Contract Changes Applied
- F-04: `senha` removido de `GET /usuarios` e `GET /usuarios/<id>`; `secret_key`, `debug` e `db_path` removidos de `GET /health`.
- F-05: `POST /admin/query` removida (404); `POST /login` devolve `dados.token`; `Authorization: Bearer <token>` exigido. Admin: `POST /admin/reset-db`, `POST /produtos`, `PUT /produtos/<id>`, `DELETE /produtos/<id>`, `PUT /pedidos/<id>/status`, `GET /usuarios`. Dono ou admin: `GET /usuarios/<id>`, `POST /pedidos`.
- F-07: admin em `GET /pedidos` e `GET /relatorios/vendas`; dono ou admin em `GET /pedidos/usuario/<id>`.
- F-10: `DELETE /produtos/<id>` é soft delete; os pedidos antigos mostram o nome real do produto (antes: "Desconhecido").
- F-12: `PUT /produtos/<id>` valida categoria e tamanho do nome como o `POST` (400).
- F-13: entrada malformada 500 → 400; 500 com mensagem genérica; `PUT /pedidos/999/status` 200 → 404.

## Validation
  ✓ Application boots without errors (`python -W default app.py`, porta 5000 respondeu)
  ✓ All endpoints respond as baseline (37/37: 27 idênticas + 10 diferenças, todas mudanças aprovadas)
  ✓ Approved contract changes verified (50/50 checks: 33 chamadas sem token/token inválido/papel errado → 401/403, rotas com credencial → status original, `/admin/query` 404, campos sensíveis ausentes, soft delete no banco com quando/quem)
  ✓ No deprecation warnings from project code (baseline e depois: nenhum DeprecationWarning; só o aviso padrão de servidor de desenvolvimento do Werkzeug)
  ✓ No CRITICAL/HIGH anti-patterns remaining (sinais rodados de novo; os que bateram eram falsos positivos: f-strings só com constantes internas, `print(` dentro de `register_blueprint(`)
  ✓ Every CRITICAL recommendation fully applied (18/18 itens de Recommendation + 5/5 mudanças de contrato dos CRITICAL)
  ✓ MVC structure checklist complete (§7: config sem segredo literal; models sem HTTP; views só delegam; controllers sem SQL; handler central; app factory; service isolado; sem estado global; `python app.py` mantido)

Verificações extras:
- `email = "admin@loja.com' --"` → 401; busca com `' UNION SELECT` → lista vazia.
- Um banco no formato antigo (sem as colunas novas, senha em texto puro) foi migrado no boot, e o login com a senha antiga funcionou.
- Pedido com item repetido estourando o estoque → 400, com rollback total (estoque intacto, 0 pedidos e 0 itens gravados).
- Item com `produto_id` string ou quantidade negativa → 400 (antes: SQL injection / aumento de estoque).
- Valores de negócio idênticos ao baseline: total do pedido, preço unitário, relatório de vendas e contagens do health.

Script auxiliar: o projeto não tem `seed.py`. O seed roda no boot e foi validado pelo login com as senhas geradas por hash.

## Endpoint Comparison
| Método | Rota | Baseline | Depois | OK |
|--------|------|----------|--------|----|
| GET | / | 200 | 200 | ✓ |
| GET | /health | 200 (com secret_key, debug, db_path) | 200 (sem os 3 campos) | ✓ aprovado F-04 |
| GET | /produtos | 200 | 200 | ✓ |
| GET | /produtos/busca?q=Mouse | 200 | 200 | ✓ |
| GET | /produtos/busca?preco_min=abc | 500 (str(e)) | 400 | ✓ aprovado F-13 |
| GET | /produtos/1 | 200 | 200 | ✓ |
| GET | /produtos/999 | 404 | 404 | ✓ |
| POST | /produtos | 201 | 201 (admin) | ✓ |
| POST | /produtos sem preco | 400 | 400 | ✓ |
| PUT | /produtos/11 | 200 | 200 (admin) | ✓ |
| PUT | /produtos/999 | 404 | 404 | ✓ |
| PUT | /produtos/11 categoria inválida | 200 | 400 | ✓ aprovado F-12 |
| GET | /usuarios | 200 (com senha) | 200 sem senha (admin) | ✓ aprovado F-04/F-05 |
| GET | /usuarios/1 | 200 (com senha) | 200 sem senha (dono/admin) | ✓ aprovado F-04/F-05 |
| GET | /usuarios/999 | 404 | 404 | ✓ |
| POST | /usuarios | 201 | 201 | ✓ |
| POST | /usuarios sem senha | 400 | 400 | ✓ |
| POST | /login | 200 | 200 (+ dados.token) | ✓ aprovado F-05 |
| POST | /login senha errada | 401 | 401 | ✓ |
| POST | /login sem body | 500 (str(e)) | 400 | ✓ aprovado F-13 |
| POST | /login usuário novo | 200 | 200 (+ dados.token) | ✓ aprovado F-05 |
| POST | /pedidos | 201 | 201 (dono/admin) | ✓ |
| POST | /pedidos estoque insuficiente | 400 | 400 | ✓ |
| POST | /pedidos produto inexistente | 400 | 400 | ✓ |
| GET | /pedidos | 200 | 200 (admin) | ✓ |
| GET | /pedidos/usuario/2 | 200 | 200 (dono/admin) | ✓ |
| PUT | /pedidos/1/status | 200 | 200 (admin) | ✓ |
| PUT | /pedidos/1/status inválido | 400 | 400 | ✓ |
| PUT | /pedidos/999/status | 200 | 404 | ✓ aprovado F-13 |
| GET | /relatorios/vendas | 200 | 200 (admin, valores idênticos) | ✓ |
| DELETE | /produtos/2 | 200 | 200 (admin, soft delete) | ✓ |
| GET | /produtos/2 após delete | 404 | 404 | ✓ |
| GET | /pedidos/usuario/2 após delete | 200 ("Desconhecido") | 200 ("Mouse Wireless") | ✓ aprovado F-10 |
| GET | /relatorios/vendas após delete | 200 | 200 (valores idênticos) | ✓ |
| DELETE | /produtos/2 de novo | 404 | 404 | ✓ |
| POST | /admin/query | 200 | 404 | ✓ aprovado F-05 |
| POST | /admin/reset-db | 200 | 200 (admin) | ✓ |

## How to run
```bash
pip install -r requirements.txt
python app.py
```
Variáveis (opcionais, ver `.env.example`): `SECRET_KEY` (defina em produção; sem ela, uma chave aleatória por processo invalida os tokens a cada restart), `FLASK_DEBUG` (default `false`), `HOST`, `PORT`, `DB_PATH` (default `loja.db`), `TOKEN_MAX_AGE` (default `3600`), `APP_ENV` (default `producao`).
Rotas protegidas: `POST /login` → `Authorization: Bearer <dados.token>`. Admin de exemplo: `admin@loja.com` / `admin123`.
O banco `loja.db` existente é migrado no boot (colunas de soft delete e hash das senhas) e pode também ser apagado para recriar com o seed.

Observações:
- Unicidade de e-mail e devolução de estoque no cancelamento continuam fora do escopo, como registrado no relatório.
- Registros removidos por soft delete continuam no banco.
================================
