================================
PHASE 3: REFACTORING COMPLETE
================================
## Strategy
A) Decomposição completa: o monolito de 4 arquivos virou camadas MVC por domínio (produto, usuário, pedido, relatório), com config, middlewares e service separados.

## New Project Structure
```
code-smells-project/
├── app.py                      # Entry point: create_app() + app = create_app() + __main__
├── config/settings.py          # Config: Settings lidas do ambiente
├── database.py                 # Database: conexão por requisição (flask.g), transaction(), schema, migrações, seed
├── models/                     # Model: SQL parametrizado + regras de domínio
│   ├── produto_model.py        #   soft delete (removido/removido_em)
│   ├── usuario_model.py        #   hash de senha, serializador sem senha
│   ├── pedido_model.py         #   regra de estoque/total, transação, JOIN sem N+1
│   └── relatorio_model.py      #   agregação única + calcular_desconto()
├── controllers/                # Controller: validação de entrada + fluxo do caso de uso
│   ├── produto_controller.py, usuario_controller.py, pedido_controller.py
│   └── relatorio_controller.py, health_controller.py, admin_controller.py
├── views/                      # View: Blueprints, só delegam (register_blueprints)
│   └── produto_routes.py, usuario_routes.py, pedido_routes.py,
│       relatorio_routes.py, health_routes.py, admin_routes.py
├── services/notificacao_service.py   # Service: e-mail/SMS/push (simulados via logging)
├── middlewares/
│   ├── error_handler.py        # AppError + handler central (mantém 404/405 padrão do Flask)
│   └── auth.py                 # token assinado (itsdangerous) + require_auth(tipo)
├── utils/constants.py          # Utils: categorias, status, limites, faixas de desconto, versão
├── .env.example
└── requirements.txt            # inalterado (nenhuma dependência nova)
```
Removidos: `controllers.py` e `models.py` da raiz (todo o conteúdo migrou para os pacotes).

## Findings Resolved
| ID | Severity | Anti-pattern | Status | How (PT-xx) |
|----|----------|--------------|--------|-------------|
| F-01 | CRITICAL | SQL Injection | RESOLVED | PT-01: todas as queries com `?`; o `IN` usa marcadores gerados; `/admin/query` foi removida |
| F-02 | CRITICAL | Credenciais hardcoded | RESOLVED | PT-02: `config/settings.py` + `.env.example`; SECRET_KEY aleatória se ausente |
| F-03 | CRITICAL | Senha em texto puro | RESOLVED | PT-03: `werkzeug.security` (scrypt); seed com hash; migração de bancos antigos no boot |
| F-04 | CRITICAL | Exposição de dados sensíveis | RESOLVED | PT-04: `senha` fora das respostas; health sem `secret_key`/`debug`/`db_path` |
| F-05 | CRITICAL | Endpoint sem autenticação | PARTIAL | PT-05 no escopo aprovado: `/admin/query` removida; token de admin em `/admin/reset-db`, `DELETE /produtos/<id>`, `GET /relatorios/vendas`. As demais rotas continuam públicas por decisão do usuário (recomendação abaixo) |
| F-06 | CRITICAL | God File | RESOLVED | PT-06: camadas MVC por domínio |
| F-07 | HIGH | Regra na camada errada | RESOLVED | PT-07: desconto em `relatorio_model.calcular_desconto`; notificações em `services/` |
| F-08 | HIGH | Estado global mutável | RESOLVED | PT-08: conexão por requisição em `flask.g` + `teardown_appcontext` |
| F-09 | HIGH | Sem transação / exclusão física | RESOLVED | PT-09: `transaction()` com `BEGIN IMMEDIATE`/rollback; soft delete de produtos. `/admin/reset-db` continua apagando tudo (é a finalidade da rota), agora só para admin |
| F-10 | MEDIUM | N+1 / queries repetidas | RESOLVED | PT-10: pedidos com 1 query (JOIN); relatório com 1 agregação; 1 SELECT de produtos por pedido |
| F-11 | MEDIUM | Código duplicado | PARTIAL | PT-11: 1 serializador por entidade, 1 validador de produto, 1 listagem de pedidos. A divergência de regras entre POST e PUT `/produtos` (tamanho do nome, categoria) foi mantida para não mudar o contrato |
| F-12 | MEDIUM | Erro engolido / validação | RESOLVED | PT-12: handler central, 0 `except Exception`; validação na borda (400/404) |
| F-13 | LOW | Magic numbers | RESOLVED | PT-14: `utils/constants.py` |
| F-14 | LOW | Código morto | RESOLVED | PT-14: imports e `SELECT 1` removidos (checagem via AST: 0 imports sem uso) |
| F-15 | LOW | Logging / debug fixo | RESOLVED | PT-14: `logging` (0 `print`); DEBUG via `FLASK_DEBUG` (default false) |

## Contract Changes Applied
- `GET /usuarios` e `GET /usuarios/<id>`: o campo `senha` foi removido dos objetos (F-04).
- `GET /health`: as chaves `secret_key`, `debug` e `db_path` foram removidas (F-04).
- `POST /admin/query` foi removida e agora responde 404 (F-05).
- `POST /admin/reset-db`, `DELETE /produtos/<id>` e `GET /relatorios/vendas` exigem `Authorization: Bearer <token>` de admin: 401 sem token ou com token inválido, 403 com token de cliente (F-05).
- `POST /login` passou a incluir `token` em `dados` (F-05).
- Entradas inválidas que davam 500 agora dão 400: `preco_min=abc`, `preco` não numérico, `/login` e `PUT /pedidos/<id>/status` sem body, item sem `produto_id` (F-12).
- `quantidade` ≤ 0 em `POST /pedidos` passou de 201 para 400; antes, quantidade negativa aumentava o estoque (F-12).
- `PUT /pedidos/<id>/status` com pedido inexistente passou de 200 para 404 (F-12).
- Erros 500 respondem `{"erro": "Erro interno do servidor"}`, sem a mensagem interna (F-12).
- Efeitos da correção de F-01, que eram bugs: nome com apóstrofo (`D'Avila`) passou de 500 para 201; busca com `'` passou de 500 para 200; login por injeção (`admin@loja.com' --`) passou de 200 para 401.
- Efeito do soft delete (F-09): o histórico de pedidos mostra o nome do produto removido, em vez de `"Desconhecido"`.

## Validation
  ✓ Application boots without errors (`python -W default app.py`, porta respondeu)
  ✓ All endpoints respond as baseline (55/55 chamadas: 42 idênticas em status e chaves; 13 diferenças, todas listadas acima como mudanças aprovadas ou efeito direto das correções)
  ✓ Approved contract changes verified (401 sem token, 403 com token de cliente, 401 com token adulterado, status original com token de admin; `senha` e chaves de config ausentes; `/admin/query` → 404)
  ✓ Soft delete: após o `DELETE /produtos/2`, o `GET /produtos/2` dá 404 e o segundo `DELETE` dá 404. A linha continua no banco (`removido=1`, `removido_em` preenchido), e o `GET /pedidos` e o relatório continuam mostrando "Mouse Wireless"
  ✓ No deprecation warnings from project code (log com `-W default` limpo; teste com `-W error::DeprecationWarning` passou)
  ✓ No CRITICAL/HIGH anti-patterns remaining in the approved scope (sinais de AP-01/02/04/08/12/14 sem ocorrências confirmadas). F-05 fica PARTIAL por decisão do usuário
  ✓ MVC structure checklist complete (§7: config sem segredo literal; models sem HTTP; views só delegam; controllers sem SQL; handler central; app factory; service isolado; sem estado global; `python app.py` mantido)
  ✓ Migração de banco antigo: colunas `removido` e `removido_em` adicionadas, senhas em texto puro convertidas para scrypt, seed não duplicado, login funcionando
  ✓ Atomicidade: pedido com o 2º item inexistente não grava pedido nem baixa estoque
  – Scripts auxiliares: o projeto não tem nenhum

## Endpoint Comparison
| Método | Rota | Baseline | Depois | OK |
|--------|------|----------|--------|----|
| GET | / | 200 | 200 | ✓ |
| GET | /produtos | 200 | 200 (corpo idêntico) | ✓ |
| GET | /produtos/busca | 200 / `preco_min=abc` 500 / `q='...` 500 | 200 / 400 / 200 | ✓ (aprovado) |
| GET | /produtos/<id> | 200 / 404 | 200 / 404 | ✓ |
| POST | /produtos | 201 / 400 / 400 / aspas 500 / preço texto 500 | 201 / 400 / 400 / 201 / 400 | ✓ (aprovado) |
| PUT | /produtos/<id> | 200 / 404 / 400 | 200 / 404 / 400 | ✓ |
| DELETE | /produtos/<id> | 200 / 404 / 404 | sem token 401; admin 200 / 404 / 404 | ✓ (aprovado) |
| GET | /usuarios | 200 | 200 (sem `senha`) | ✓ (aprovado) |
| GET | /usuarios/<id> | 200 / 404 | 200 (sem `senha`) / 404 | ✓ (aprovado) |
| POST | /usuarios | 201 / 400 | 201 / 400 | ✓ |
| POST | /login | 200 / 401 / 400 / injeção 200 / sem body 500 | 200 (+token) / 401 / 400 / 401 / 400 | ✓ (aprovado) |
| POST | /pedidos | 201 / 400 ×4 / sem produto_id 500 / qtd negativa 201 | 201 / 400 ×4 / 400 / 400 | ✓ (aprovado) |
| GET | /pedidos | 200 | 200 (corpo idêntico) | ✓ |
| GET | /pedidos/usuario/<id> | 200 / 200 vazio | 200 / 200 vazio | ✓ |
| PUT | /pedidos/<id>/status | 200 / 400 / sem body 500 / inexistente 200 | 200 / 400 / 400 / 404 | ✓ (aprovado) |
| GET | /relatorios/vendas | 200 | sem token 401; admin 200 (corpo idêntico) | ✓ (aprovado) |
| GET | /health | 200 (8 chaves) | 200 (5 chaves) | ✓ (aprovado) |
| POST | /admin/reset-db | 200 | sem token 401; admin 200 | ✓ (aprovado) |
| POST | /admin/query | 200 | 404 (removida) | ✓ (aprovado) |
| GET/PATCH | rota inexistente / método errado | 404 / 405 (HTML Flask) | 404 / 405 (HTML Flask) | ✓ |

## How to run
```bash
pip install -r requirements.txt
python app.py                      # http://localhost:5000
```
Variáveis (todas opcionais, ver `.env.example`): `SECRET_KEY`, `FLASK_DEBUG` (default false), `DATABASE_PATH` (default loja.db), `HOST`, `PORT`, `APP_ENV`, `TOKEN_MAX_AGE`.
Sem `SECRET_KEY`, uma chave aleatória é gerada a cada boot, e os tokens deixam de valer quando o servidor reinicia. Bancos `loja.db` existentes são migrados automaticamente no boot.

## Recomendações fora do escopo
- Autenticar `GET /usuarios`, `GET /usuarios/<id>`, `GET /pedidos`, `GET /pedidos/usuario/<id>`, `POST`/`PUT /produtos` e `PUT /pedidos/<id>/status` (F-05). Hoje continuam públicas por decisão do usuário.
- Devolver o estoque ao cancelar um pedido. A regra é anunciada no log, mas nunca foi implementada.
- Unificar as validações de `POST` e `PUT /produtos` (categoria e tamanho do nome).
- Validar formato e unicidade de e-mail no cadastro.
- Restringir o CORS (`CORS(app)` aceita qualquer origem).
================================
