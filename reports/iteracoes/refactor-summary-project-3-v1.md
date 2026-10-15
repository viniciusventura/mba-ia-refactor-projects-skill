================================
PHASE 3: REFACTORING COMPLETE
================================
## Strategy
B) Evolução incremental: mantidos os models ORM, os Blueprints e o nome `routes/` (papel de View da §4); criadas as camadas que faltavam (`controllers/`, `config/`, `middlewares/`) e o app factory, sem mudar URLs nem comandos de execução.

## New Project Structure
```
task-manager-api/
├── app.py                      # Entry point / composition root: create_app() + app = create_app()
├── config/settings.py          # Config: tudo lido do ambiente (.env via python-dotenv)
├── database.py                 # Database: db = SQLAlchemy(), create_all + migração idempotente das colunas de soft delete
├── models/                     # Model: entidades ORM + regras de domínio + consultas
│   ├── soft_delete.py          #   SoftDeleteMixin (deleted, deleted_at, deleted_by)
│   ├── task.py                 #   is_overdue, serializações, agregações (GROUP BY), cascata lógica
│   ├── user.py                 #   hash scrypt (werkzeug), to_dict sem password
│   └── category.py
├── controllers/                # Controller: fluxo do caso de uso + validação de entrada
│   ├── task_controller.py, user_controller.py, category_controller.py,
│   ├── report_controller.py, health_controller.py
│   └── validators.py           #   leitura do body / parse de data / int de query string
├── routes/                     # View: só URL → controller (+ require_auth)
│   ├── __init__.py             #   register_blueprints(app)
│   ├── task_routes.py, user_routes.py, report_routes.py,
│   ├── category_routes.py      #   (novo: CRUD de categorias saiu de report_routes.py, mesmas URLs)
│   └── health_routes.py        #   (/health e / saíram do app.py)
├── middlewares/                # Transversais
│   ├── error_handler.py        #   AppError/ValidationError/... + handlers (AppError, HTTPException, Exception)
│   └── auth.py                 #   token assinado (itsdangerous) + require_auth(roles)
├── utils/                      # Puros: constants.py, time.py (utc_now), helpers.py (calculate_percentage)
├── seed.py                     # Script auxiliar (inalterado no uso: python seed.py)
├── .env.example, requirements.txt, README.md
```
Removido: `services/` (NotificationService era código morto, nunca importado, com credencial SMTP hardcoded).

## Origem → destino (principais)
| Origem | Destino |
|---|---|
| app.py: config literal | config/settings.py |
| app.py: /health, / | routes/health_routes.py → controllers/health_controller.py |
| routes/task_routes.py: corpo dos 7 handlers | controllers/task_controller.py (fluxo/validação) + models/task.py (consultas, is_overdue, serialização) |
| routes/user_routes.py: corpo dos 7 handlers | controllers/user_controller.py + models/user.py |
| routes/report_routes.py: relatórios | controllers/report_controller.py + agregações em models/task.py |
| routes/report_routes.py: CRUD de categorias | routes/category_routes.py + controllers/category_controller.py |
| `except:` espalhados | middlewares/error_handler.py |
| token `fake-jwt-token-<id>` | middlewares/auth.py (issue_token/require_auth) |
| listas/limites inline, utils/helpers.py morto | utils/constants.py, utils/time.py, utils/helpers.py (só calculate_percentage) |

## Findings Resolved
| ID | Severity | Anti-pattern | Status | How (PT-xx) |
|----|----------|--------------|--------|-------------|
| F-01 | CRITICAL | Credenciais hardcoded (AP-02) | RESOLVED | PT-02: Settings do ambiente, SECRET_KEY aleatória se ausente; SMTP morto removido |
| F-02 | CRITICAL | Senha MD5 (AP-03) | RESOLVED | PT-03: werkzeug `generate_password_hash` (scrypt); seed regera os hashes |
| F-03 | CRITICAL | Hash de senha na resposta (AP-04) | RESOLVED | PT-04: `User.to_dict()` sem `password` |
| F-04 | CRITICAL | Sem autenticação (AP-05) | RESOLVED | PT-05: token assinado + `require_auth`; role/active só por admin. Leituras públicas (GET /users, /reports/*) mantidas, como previsto no plano (fora de escopo) |
| F-05 | CRITICAL | God File report_routes.py (AP-06) | RESOLVED | PT-06: separado em report_* e category_* (rotas + controllers), mesmas URLs |
| F-06 | HIGH | Regra na camada errada (AP-07) | RESOLVED | PT-07: controllers criados; regras em models; services/ morto removido |
| F-07 | HIGH | Exclusão física (AP-09) | RESOLVED | PT-09: soft delete (`deleted`, `deleted_at`, `deleted_by`) em users/tasks/categories, cascata lógica user→tasks, migração idempotente |
| F-08 | MEDIUM | N+1 (AP-10) | RESOLVED | PT-10: joinedload e GROUP BY. Medido com o seed: GET /tasks = 1 query (antes 1+2N), /users = 2, /categories = 2, /tasks/stats = 2, /reports/summary = 9 (constante) |
| F-09 | MEDIUM | Duplicação (AP-11) | RESOLVED | PT-11: `Task.is_overdue` único, constantes, validadores compartilhados por create/update, `calculate_percentage` |
| F-10 | MEDIUM | Erros engolidos (AP-12) | RESOLVED | PT-12: 0 `except` genéricos; handler central com log; entradas inválidas → 400 |
| F-11 | MEDIUM | API deprecated (AP-13) | RESOLVED | PT-13: `utc_now()` e `db.session`/consultas modernas; 0 warnings do projeto em execução |
| F-12 | LOW | Código morto / deps sem uso (AP-14) | RESOLVED | PT-14: services/ e helpers mortos removidos; marshmallow e requests fora do requirements; 0 imports sem uso |
| F-13 | LOW | print / debug fixo (AP-14) | RESOLVED | PT-14: `logging`; DEBUG/HOST/PORT do ambiente (DEBUG padrão false) |
| F-14 | LOW | Magic numbers / verbosidade (AP-14) | RESOLVED | PT-14: utils/constants.py, `isinstance`, retornos booleanos diretos |

## Contract Changes Applied
- F-03: `password` não aparece mais em GET /users/<id>, POST /users, PUT /users/<id> nem em `user` do POST /login.
- F-04: o `token` do POST /login agora é assinado (itsdangerous, validade TOKEN_MAX_AGE). DELETE /tasks/<id> exige `Authorization: Bearer` (401). DELETE /users/<id> e DELETE /categories/<id> exigem admin (401/403). POST /users com `role` ≠ `user` e PUT /users/<id> com `role`/`active` exigem admin (401/403).
- F-10: entradas inválidas que davam 500 (HTML) agora dão 400 `{"error": ...}`.
- F-07: /reports/* incluem usuários/tasks/categorias removidos (/reports/user/<id> de usuário removido → 200 em vez de 404); o e-mail de usuário removido continua reservado (409).
- Efeito colateral do error handler central, fora do inventário: 404/405/415 do próprio Flask mantêm o status, mas respondem `{"error": ...}` em vez da página HTML padrão.

## Validation
  ✓ Application boots without errors (python app.py; porta 5000 responde)
  ✓ All endpoints respond as baseline (22/22 endpoints; 56/56 chamadas conformes: 46 idênticas em status, chaves e corpo, sem contar timestamps; 10 diferem somente pelas mudanças aprovadas acima)
  ✓ Approved contract changes verified (sem token → 401; token de user → 403; token de admin → status original; `password` ausente; 500→400 nos 4 casos)
  ✓ No deprecation warnings from project code (log do app com -W default: nenhum DeprecationWarning/LegacyAPIWarning; baseline tinha 25 linhas distintas)
  ✓ No CRITICAL/HIGH anti-patterns remaining (sinais re-executados: 0 md5, 0 segredos literais, 0 fake token, 0 session.delete nas rotas, 0 ORM em controllers/rotas, 0 `except` genérico, 0 utcnow/query.get)
  ✓ MVC structure checklist complete (§7: config, models sem HTTP, rotas só delegam, controllers sem consulta, handler central, app factory, sem estado global mutável, `python seed.py` + `python app.py` funcionando)

Soft delete verificado no banco após os DELETEs: users 5/5, tasks 11/11, categories 5/5 continuam gravados. User 2, as 3 tasks dele (cascata) e a task 11 estão com `deleted=1`, `deleted_at` e `deleted_by=1`; category 5 também. GET por id → 404, login do removido → 401, e /reports/summary continua listando "Maria Santos" com 4 tasks. A migração foi testada num banco com o schema antigo: as colunas foram adicionadas no boot e os dados preservados.

Observações honestas:
- Os blocos 1 (config/app factory) e 2 (camadas) foram verificados juntos com `import app`, porque o novo `routes/__init__.py` já referenciava as rotas reescritas.
- A validação precisou de 3 ciclos. Ciclo 1: 19 respostas 500, porque a coluna `User.active` sobrescrevia o método `active()` do mixin; o método foi renomeado para `not_deleted()`. Ciclo 2: OK. Ciclo 3: repetido após mover 2 consultas do report_controller para os models, OK.
- O `seed.py` continua apagando fisicamente as tabelas (`query.delete()`): ele é o reset do banco de desenvolvimento, não uma rota de negócio.
- Scripts que importam o app (seed) ainda emitem `ResourceWarning: unclosed database` na saída do interpretador, vindo do pool do SQLAlchemy. Esse aviso já existia no baseline e não é de deprecation.
- O banco local `instance/tasks.db` precisa ser recriado com `python seed.py`: os hashes MD5 antigos não validam com o scrypt. Bancos antigos sobem normalmente (migração automática), mas os logins desses usuários exigem redefinir a senha.

## Endpoint Comparison
| Método | Rota | Baseline | Depois | OK |
|--------|------|----------|--------|----|
| GET | /health | 200 | 200 | ✓ |
| GET | / | 200 | 200 | ✓ |
| GET | /tasks | 200 | 200 | ✓ |
| GET | /tasks/<id> | 200 / 404 | 200 / 404 | ✓ |
| POST | /tasks | 201 / 400 / 400 / 404 / 500 (priority "2") | 201 / 400 / 400 / 404 / 400 | ✓ (500→400 aprovado) |
| PUT | /tasks/<id> | 200 / 404 / 400 | 200 / 404 / 400 | ✓ |
| DELETE | /tasks/<id> | 200 / 404 (sem auth) | 200 / 404 com token; 401 sem | ✓ (auth aprovada) |
| GET | /tasks/search | 200 / 200 / 500 (priority=abc) | 200 / 200 / 400 | ✓ (500→400 aprovado) |
| GET | /tasks/stats | 200 | 200 | ✓ |
| GET | /users | 200 | 200 | ✓ |
| GET | /users/<id> | 200 (+password) / 404 | 200 (sem password) / 404 | ✓ (aprovado) |
| POST | /users | 201 / 409 / 400 / 201 admin (anônimo) | 201 / 409 / 400 / 201 admin com token; 401 sem | ✓ (aprovado) |
| PUT | /users/<id> | 200 / 404 / 500 (password int) | 200 / 404 / 400; role sem admin → 401/403 | ✓ (aprovado) |
| DELETE | /users/<id> | 200 / 404 | 200 / 404 com admin; 401 / 403 sem | ✓ (aprovado) |
| GET | /users/<id>/tasks | 200 / 404 | 200 / 404 | ✓ |
| POST | /login | 200 / 401 / 400 | 200 (token assinado, sem password) / 401 / 400 | ✓ (aprovado) |
| GET | /reports/summary | 200 | 200 (histórico inclui removidos) | ✓ (aprovado) |
| GET | /reports/user/<id> | 200 / 404 | 200 / 404; removido → 200 | ✓ (aprovado) |
| GET | /categories | 200 | 200 | ✓ |
| POST | /categories | 201 / 400 | 201 / 400 | ✓ |
| PUT | /categories/<id> | 200 / 404 / 500 (body null) | 200 / 404 / 400 | ✓ (500→400 aprovado) |
| DELETE | /categories/<id> | 200 / 404 | 200 / 404 com admin; 401 / 403 sem | ✓ (aprovado) |

## How to run
```bash
pip install -r requirements.txt
cp .env.example .env      # opcional; defina SECRET_KEY para tokens sobreviverem a restarts
python seed.py            # recria instance/tasks.db (necessário: hashes agora são scrypt)
python app.py             # http://localhost:5000
```
Variáveis: `SECRET_KEY` (aleatória por boot se ausente), `DATABASE_URL` (sqlite:///tasks.db), `FLASK_DEBUG` (false), `HOST` (0.0.0.0), `PORT` (5000), `TOKEN_MAX_AGE` (3600).
Login admin do seed: `joao@email.com` / `1234`. Use `Authorization: Bearer <token>` nas rotas protegidas.
================================
