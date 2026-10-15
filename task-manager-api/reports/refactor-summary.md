================================
PHASE 3: REFACTORING COMPLETE
================================
## Strategy
B) Evolução incremental: `models/`, `routes/` (camada View, equivalente a `views/` da §4), Blueprints e URLs mantidos; criadas as camadas que faltavam (`config/`, `controllers/`, `middlewares/`) e removidas as camadas mortas (`services/`, `utils/helpers.py`).

## New Project Structure
```
task-manager-api/
├── app.py                      # entry point: create_app() + app = create_app() (composition root)
├── database.py                 # db = SQLAlchemy(), init_app, create_all + migração idempotente do soft delete
├── seed.py                     # script auxiliar (inalterado no uso: python seed.py)
├── config/settings.py          # Config: Settings lidas do ambiente (.env via python-dotenv)
├── models/                     # Model: entidades, regras de domínio e consultas
│   ├── soft_delete.py          #   SoftDeleteMixin (deleted, deleted_at, deleted_by)
│   ├── task.py  user.py  category.py
├── controllers/                # Controller: fluxo do caso de uso, validação, decisão da resposta
│   ├── task_controller.py  user_controller.py  category_controller.py
│   ├── report_controller.py  health_controller.py  validators.py
├── routes/                     # View: Blueprints, só URL → controller (+ proteção)
│   ├── __init__.py (register_blueprints)
│   ├── task_routes.py  user_routes.py  report_routes.py
│   ├── category_routes.py (novo)  health_routes.py (novo)
├── middlewares/                # transversais
│   ├── error_handler.py        #   AppError + handlers 4xx/5xx em JSON
│   └── auth.py                 #   token assinado (itsdangerous) + require_auth
├── utils/constants.py  utils/time.py   # constantes de domínio, utc_now()
├── requirements.txt  .env.example  README.md
```
Removidos: `utils/helpers.py` (100% morto), `services/notification_service.py` (morto, com credencial SMTP).

## Findings Resolved
| ID | Severity | Anti-pattern | Status | How (PT-xx) |
|----|----------|--------------|--------|-------------|
| F-01 | CRITICAL | Credenciais hardcoded (AP-02) | RESOLVED | PT-02: `config/settings.py` + `.env.example`; serviço com senha SMTP removido |
| F-02 | CRITICAL | Senha em MD5 (AP-03) | RESOLVED | PT-03: werkzeug (scrypt com salt); MD5 legado só é verificado e regravado no login |
| F-03 | CRITICAL | Exposição de dados sensíveis (AP-04) | RESOLVED | PT-04: `password` fora de `User.to_dict` (4 respostas) |
| F-04 | CRITICAL | Endpoint sensível sem autenticação (AP-05) | RESOLVED | PT-05: token assinado + `require_auth` em 10 rotas, dono/papel no controller |
| F-05 | CRITICAL | God File (AP-06) | RESOLVED | PT-06: report/category separados em routes + controllers; regras nos models |
| F-06 | HIGH | Leitura de dados de outros sem auth (AP-05) | RESOLVED | PT-05: 4 rotas exigem token |
| F-07 | HIGH | Regra de negócio na camada errada (AP-07) | RESOLVED | PT-07: controllers criados; `Task.is_overdue()` reutilizado; `services/` morto removido |
| F-08 | HIGH | Exclusão física (AP-09) | RESOLVED | PT-09: soft delete nas 3 tabelas, cascata lógica usuário → tasks, migração idempotente |
| F-09 | MEDIUM | N+1 / queries repetidas (AP-10) | RESOLVED | PT-10: joinedload + GROUP BY (GET /tasks: 21 → 1 query; /reports/summary: constante, 11) |
| F-10 | MEDIUM | Código duplicado (AP-11) | RESOLVED | PT-11: `is_overdue`, `utils/constants.py`, `controllers/validators.py` |
| F-11 | MEDIUM | Erro engolido / validação ausente (AP-12) | RESOLVED | PT-12: `middlewares/error_handler.py`; 0 `except` genérico; 5 entradas 500 → 400 |
| F-12 | MEDIUM | API deprecated (AP-13) | RESOLVED | PT-13: `utc_now()` e `db.session.get` (incl. seed.py); 0 warnings |
| F-13 | LOW | Código morto / deps sem uso (AP-14) | RESOLVED | PT-14: imports, helpers, métodos mortos, marshmallow/requests removidos; python-dotenv passou a ser usado |
| F-14 | LOW | Logging inadequado (AP-14) | RESOLVED | PT-14: `logging`; `DEBUG` do ambiente (default false) |
| F-15 | LOW | Magic numbers (AP-14) | RESOLVED | PT-14: `utils/constants.py` |
| F-16 | LOW | Legibilidade (AP-14) | RESOLVED | PT-14: booleanos diretos, `isinstance`, nomes descritivos |

## Contract Changes Applied
- F-03: `password` removido de `GET /users/<id>`, `POST /users`, `PUT /users/<id>` e do `user` de `POST /login`.
- F-04: `token` do login é assinado (`Authorization: Bearer <token>`, validade `TOKEN_MAX_AGE`); 401 sem token/token inválido; 403 sem papel/propriedade: `DELETE /users/<id>`, `POST|PUT|DELETE /categories` (admin); `PUT|DELETE /tasks/<id>` (admin, manager ou dono); `POST /tasks`, `GET /users/<id>` (autenticado); `PUT /users/<id>` (próprio ou admin; `role`/`active` só admin); `POST /users` com `role` ≠ `user` (admin).
- F-06: `GET /users`, `GET /users/<id>/tasks`, `GET /reports/summary`, `GET /reports/user/<id>` exigem token.
- F-08: `DELETE` faz soft delete (status e mensagens iguais); leituras se comportam como antes (404 por id, somem das listagens, tasks do usuário removido somem); `/reports/*` passam a contar registros removidos (histórico). E-mail de usuário removido continua ocupado (409).
- F-11: 5 entradas inválidas passam de 500 (página HTML de debug) para 400 `{'error': ...}`; 404/405 do Flask com corpo JSON.

## Validation
  ✓ Application boots without errors
  ✓ All endpoints respond as baseline (42/50 idênticos; os 8 restantes são mudanças aprovadas F-03/F-11 e foram verificados)
  ✓ Approved contract changes verified (14 chamadas sem token → 401, token falso → 401, 9 chamadas com token de usuário comum → 403, dono/próprio/admin → status original)
  ✓ No deprecation warnings from project code (log do app vazio de warnings; import com `-W error::DeprecationWarning` ok)
  ✓ No CRITICAL/HIGH anti-patterns remaining (sinais re-executados; restam só MD5 de verificação legada e `query.delete()` do reset no seed.py, ambos intencionais)
  ✓ Every CRITICAL recommendation fully applied (25/25)
  ✓ MVC structure checklist complete

Soft delete verificado no banco após a rodada: tasks 3, 7, 9 (7 e 9 por cascata), user 3 e category 4 com `deleted=1`, `deleted_at` preenchido e `deleted_by=1`; `GET /reports/summary` e `GET /reports/user/3` continuam mostrando-os. Migração testada num banco com o schema antigo: colunas adicionadas, dados e login com MD5 legado preservados (hash regravado em scrypt). Seed executa sem erro.

## Endpoint Comparison
| Método | Rota | Baseline | Depois | OK |
|--------|------|----------|--------|----|
| POST | /login | 200 | 200 | ✓ |
| POST | /login | 401 | 401 | ✓ |
| GET | / | 200 | 200 | ✓ |
| GET | /health | 200 | 200 | ✓ |
| POST | /health | 405 | 405 | ✓ F-11 (corpo JSON) |
| GET | /tasks | 200 | 200 | ✓ |
| GET | /tasks/1 | 200 | 200 | ✓ |
| GET | /tasks/999 | 404 | 404 | ✓ |
| POST | /tasks | 201 | 201 | ✓ |
| POST | /tasks | 400 | 400 | ✓ |
| POST | /tasks | 400 | 400 | ✓ |
| POST | /tasks | 500 | 400 | ✓ F-11 |
| PUT | /tasks/1 | 200 | 200 | ✓ |
| PUT | /tasks/999 | 404 | 404 | ✓ |
| PUT | /tasks/1 | 500 | 400 | ✓ F-11 |
| GET | /tasks/search?q=API | 200 | 200 | ✓ |
| GET | /tasks/search?priority=abc | 500 | 400 | ✓ F-11 |
| GET | /tasks/stats | 200 | 200 | ✓ |
| GET | /users | 200 | 200 | ✓ |
| GET | /users/1 | 200 | 200 | ✓ F-03 (sem password) |
| GET | /users/999 | 404 | 404 | ✓ |
| POST | /users | 201 | 201 | ✓ F-03 (sem password) |
| POST | /users | 409 | 409 | ✓ |
| POST | /users | 400 | 400 | ✓ |
| PUT | /users/2 | 200 | 200 | ✓ F-03 (sem password) |
| PUT | /users/999 | 404 | 404 | ✓ |
| GET | /users/1/tasks | 200 | 200 | ✓ |
| GET | /users/999/tasks | 404 | 404 | ✓ |
| GET | /reports/summary | 200 | 200 | ✓ |
| GET | /reports/user/1 | 200 | 200 | ✓ |
| GET | /reports/user/999 | 404 | 404 | ✓ |
| GET | /categories | 200 | 200 | ✓ |
| POST | /categories | 201 | 201 | ✓ |
| POST | /categories | 400 | 400 | ✓ |
| PUT | /categories/1 | 200 | 200 | ✓ |
| PUT | /categories/999 | 404 | 404 | ✓ |
| PUT | /categories/1 | 500 | 400 | ✓ F-11 |
| DELETE | /tasks/999 | 404 | 404 | ✓ |
| DELETE | /tasks/3 | 200 | 200 | ✓ |
| GET | /tasks/3 | 404 | 404 | ✓ |
| DELETE | /tasks/3 | 404 | 404 | ✓ |
| DELETE | /categories/999 | 404 | 404 | ✓ |
| DELETE | /categories/4 | 200 | 200 | ✓ |
| GET | /categories | 200 | 200 | ✓ |
| DELETE | /users/999 | 404 | 404 | ✓ |
| DELETE | /users/3 | 200 | 200 | ✓ |
| GET | /users/3 | 404 | 404 | ✓ |
| GET | /tasks | 200 | 200 | ✓ |
| POST | /login | 401 | 401 | ✓ |
| GET | /reports/summary | 200 | 200 | ✓ |
| GET | /users/1/tasks | — | 200 | ✓ (token user/admin) |
| GET | /users/999/tasks | — | 404 | ✓ (token user/admin) |
| POST | /tasks | — | 401 | ✓ (sem token) |
| PUT | /tasks/1 | — | 401 | ✓ (sem token) |
| DELETE | /tasks/1 | — | 401 | ✓ (sem token) |
| GET | /users | — | 401 | ✓ (sem token) |
| GET | /users/1 | — | 401 | ✓ (sem token) |
| PUT | /users/1 | — | 401 | ✓ (sem token) |
| DELETE | /users/1 | — | 401 | ✓ (sem token) |
| GET | /users/1/tasks | — | 401 | ✓ (sem token) |
| POST | /users | — | 401 | ✓ (sem token) |
| GET | /reports/summary | — | 401 | ✓ (sem token) |
| GET | /reports/user/1 | — | 401 | ✓ (sem token) |
| POST | /categories | — | 401 | ✓ (sem token) |
| PUT | /categories/1 | — | 401 | ✓ (sem token) |
| DELETE | /categories/1 | — | 401 | ✓ (sem token) |
| GET | /users | — | 401 | ✓ (sem token) |
| PUT | /tasks/1 | — | 403 | ✓ (token user/admin) |
| DELETE | /tasks/1 | — | 403 | ✓ (token user/admin) |
| PUT | /users/1 | — | 403 | ✓ (token user/admin) |
| PUT | /users/2 | — | 403 | ✓ (token user/admin) |
| DELETE | /users/1 | — | 403 | ✓ (token user/admin) |
| POST | /users | — | 403 | ✓ (token user/admin) |
| POST | /categories | — | 403 | ✓ (token user/admin) |
| PUT | /categories/1 | — | 403 | ✓ (token user/admin) |
| DELETE | /categories/1 | — | 403 | ✓ (token user/admin) |
| PUT | /tasks/2 | — | 200 | ✓ (token user/admin) |
| PUT | /users/2 | — | 200 | ✓ (token user/admin) |
| POST | /users | — | 201 | ✓ (token user/admin) |
## How to run
```bash
pip install -r requirements.txt
cp .env.example .env      # defina SECRET_KEY (sem ela, chave aleatória por boot)
python seed.py
python app.py             # http://localhost:5000
```
Variáveis: `SECRET_KEY`, `DATABASE_URL` (default `sqlite:///tasks.db` → `instance/tasks.db`), `TOKEN_MAX_AGE` (3600), `DEBUG` (false), `HOST` (0.0.0.0), `PORT` (5000).
Seed: admin `joao@email.com`/`1234`, user `maria@email.com`/`abcd`, manager `pedro@email.com`/`pass`.
================================
