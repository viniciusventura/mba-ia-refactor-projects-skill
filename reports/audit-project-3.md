================================
ARCHITECTURE AUDIT REPORT
================================
Project:  task-manager-api
Stack:    Python 3.14 + Flask 3.0.0 + Flask-SQLAlchemy 3.1.1 (SQLAlchemy 2.1.1)
Files:    15 analyzed | ~1158 lines of code (inclui seed.py)
Date:     2026-10-01
Architecture: B) Parcialmente em camadas: models/, routes/, services/ e utils/ existem, mas as rotas concentram ORM, validação e regra de negócio, não há controllers/, e services/ e quase todo utils/ nunca são importados

## Summary
CRITICAL: 5 | HIGH: 2 | MEDIUM: 4 | LOW: 3

| ID | Severity | Anti-pattern | Location |
|----|----------|--------------|----------|
| F-01 | CRITICAL | Credenciais hardcoded (AP-02) | app.py:13, services/notification_service.py:7-10 |
| F-02 | CRITICAL | Armazenamento inseguro de senha (AP-03) | models/user.py:29, 32 |
| F-03 | CRITICAL | Exposição de dados sensíveis (AP-04) | models/user.py:21; routes/user_routes.py:33, 85, 129, 209 |
| F-04 | CRITICAL | Endpoint sensível sem autenticação (AP-05) | routes/user_routes.py:52, 71-78, 119-125, 210; routes/task_routes.py:225; routes/user_routes.py:134; routes/report_routes.py:211 |
| F-05 | CRITICAL | God File (AP-06) | routes/report_routes.py:1-223 |
| F-06 | HIGH | Regra de negócio na camada errada (AP-07) | routes/task_routes.py, routes/user_routes.py, routes/report_routes.py (linhas no finding); services/notification_service.py |
| F-07 | HIGH | Exclusão física de entidades com histórico (AP-09) | routes/task_routes.py:232; routes/user_routes.py:140-145; routes/report_routes.py:218 |
| F-08 | MEDIUM | Query N+1 / queries repetidas (AP-10) | routes/task_routes.py:42, 51, 275-279; routes/user_routes.py:22; routes/report_routes.py:15-28, 56, 163 |
| F-09 | MEDIUM | Código duplicado (AP-11) | routes/task_routes.py:30-39, 71-80, 284-287; routes/user_routes.py:171-180; routes/report_routes.py:34-36, 132-135 (+ listas e validações) |
| F-10 | MEDIUM | Erro engolido / sem handler central / validação ausente (AP-12) | 16 `except` genéricos + routes/task_routes.py:96, 113, 182, 261, 264; routes/report_routes.py:196-197; routes/user_routes.py:115 |
| F-11 | MEDIUM | Uso de API deprecated (AP-13) | 23× `datetime.utcnow`, 16× `Model.query.get` |
| F-12 | LOW | Código morto e dependências sem uso (AP-14) | services/notification_service.py; utils/helpers.py; models/task.py:38-60; models/user.py:34-38; imports; requirements.txt:4-6 |
| F-13 | LOW | Logging inadequado / debug fixo (AP-14) | 13× `print(`; app.py:34 |
| F-14 | LOW | Magic numbers, verbosidade e nomes curtos (AP-14) | routes/task_routes.py:96-114, 141, 167-183, 210; routes/user_routes.py:64, 115; routes/report_routes.py:24-28, 45, 129; models/task.py:39-48; models/user.py:34-38 |

## Findings

### F-01 [CRITICAL] Credenciais hardcoded (AP-02)
File: app.py:13, services/notification_service.py:7-10
Principle: OWASP A07 / 12-Factor App (Config)
Description: 2 segredos literais no código, sem leitura de ambiente: a `SECRET_KEY` do Flask e as credenciais SMTP (usuário + senha) do serviço de notificação. A URI do banco (app.py:11) e `debug=True` (app.py:34) também estão fixos no código. O serviço de notificação é código morto (F-12), mas a senha continua versionada no repositório; a `SECRET_KEY` está ativa.
Evidence:
```python
app.config['SECRET_KEY'] = 'super-secret-key-123'          # app.py:13
self.email_password = 'senha123'                           # services/notification_service.py:10
```
Impact: quem tem acesso ao repositório pode forjar qualquer dado assinado com a `SECRET_KEY` (inclusive o token que F-04 vai introduzir) e usar a conta SMTP.
Recommendation: criar `config/settings.py` lendo do ambiente (`SECRET_KEY`, `DATABASE_URL`, `DEBUG`, `HOST`, `PORT`) via python-dotenv, com `.env.example` (PT-02). Remover o serviço SMTP morto junto com a credencial (F-12).
Contract change: NO

### F-02 [CRITICAL] Armazenamento inseguro de senha (AP-03)
File: models/user.py:3, 29, 32
Principle: OWASP A02 Cryptographic Failures
Description: as senhas são gravadas como MD5 sem salt. Não existe bcrypt/argon2/scrypt/pbkdf2/werkzeug.security em nenhum lugar do projeto. Os hashes ainda vazam pela API (F-03), o que agrava o problema.
Evidence:
```python
self.password = hashlib.md5(pwd.encode()).hexdigest()               # models/user.py:29
return self.password == hashlib.md5(pwd.encode()).hexdigest()       # models/user.py:32
```
Impact: md5('1234') e md5('abcd'), senhas do seed, estão em qualquer rainbow table. Um vazamento do banco ou da API revela as senhas em segundos.
Recommendation: `werkzeug.security.generate_password_hash` / `check_password_hash`, já disponíveis com o Flask (PT-03). O banco não é versionado e é recriado pelo `seed.py`, que usa `set_password`, então não há hashes antigos a migrar.
Contract change: NO

### F-03 [CRITICAL] Exposição de dados sensíveis (AP-04)
File: models/user.py:21; serializador usado em routes/user_routes.py:33 (GET /users/<id>), 85 (POST /users), 129 (PUT /users/<id>), 209 (POST /login)
Principle: OWASP A01/A09
Description: `User.to_dict()` inclui o hash da senha, que chega à resposta de 4 endpoints. O GET /users monta um dict próprio sem a senha, o que mostra a inconsistência.
Evidence:
```python
'password': self.password,                 # models/user.py:21
data = user.to_dict()                      # routes/user_routes.py:33 → jsonify(data)
'user': user.to_dict(),                    # routes/user_routes.py:209 (login)
```
Impact: qualquer cliente, sem autenticação (F-04), obtém o hash MD5 de qualquer usuário via GET /users/<id> e o quebra (F-02).
Recommendation: remover `password` do `to_dict()` (serializador de saída, PT-04).
Contract change: YES: o campo `password` deixa de aparecer em GET /users/<id>, POST /users, PUT /users/<id> e em `user` do POST /login.

### F-04 [CRITICAL] Endpoint sensível sem autenticação (AP-05)
File: routes/user_routes.py:210 (token); routes/user_routes.py:52, 71-78 (role no POST /users); routes/user_routes.py:119-125 (role/active no PUT /users/<id>); routes/task_routes.py:225, routes/user_routes.py:134, routes/report_routes.py:211 (DELETEs)
Principle: OWASP A01 Broken Access Control
Description: o projeto não tem nenhum mecanismo de autenticação (0 ocorrências de `login_required`, `before_request`, verificação de token). Três problemas se combinam:
1. O "token" do login é previsível e não assinado: `'fake-jwt-token-' + id`, e nenhuma rota o verifica.
2. O campo de privilégio `role` é aceito do body: qualquer pessoa cria um usuário `admin` (POST /users) ou se promove/reativa (PUT /users/<id> com `role`/`active`).
3. As 3 rotas destrutivas (DELETE /tasks/<id>, /users/<id>, /categories/<id>) são públicas.
Evidence:
```python
role = data.get('role', 'user')                          # routes/user_routes.py:52
user.role = role                                         # routes/user_routes.py:78
'token': 'fake-jwt-token-' + str(user.id)                # routes/user_routes.py:210
```
Impact: qualquer cliente anônimo cria administradores, altera privilégios e apaga usuários (com todas as suas tasks) e categorias.
Recommendation: emitir no /login um token assinado com a `SECRET_KEY` (`itsdangerous.URLSafeTimedSerializer`, já dependência do Flask) e criar `middlewares/auth.py` com `require_auth(roles=...)` (PT-05). Proteger: os 3 DELETEs (autenticado; `admin` para usuários e categorias) e a definição de `role`/`active` (somente `admin`). O usuário autenticado também alimenta o `deleted_by` do soft delete (F-07).
Contract change: YES:
- POST /login: a chave `token` continua, mas o valor passa a ser um token assinado (não mais `fake-jwt-token-<id>`).
- DELETE /tasks/<id>: exige `Authorization: Bearer <token>` (401 sem token/token inválido).
- DELETE /users/<id> e DELETE /categories/<id>: exigem token de `admin` (401 sem token, 403 sem papel).
- POST /users com `role` diferente de `user` e PUT /users/<id> com `role` ou `active`: exigem token de `admin` (401/403). Criação de usuário comum e as demais edições continuam públicas.

### F-05 [CRITICAL] God File (AP-06)
File: routes/report_routes.py:1-223
Principle: SRP (SOLID) + MVC
Description: um arquivo de 223 linhas que mistura 2 domínios e 3 camadas: relatórios (12-155) e CRUD de categorias (157-223); roteamento (12, 103, 157, 167, 190, 211); acesso a dados ORM (15-30, 46-56, 105-109, 159-163, 177-184, 192, 205, 213, 218); e regras de agregação/negócio (atraso 33-43 e 132-135, produtividade 57-67, contagens por status/prioridade 119-130, taxa de conclusão 67 e 151). Um cliente que procura "categorias" não as encontra em `report_routes.py`. `task_routes.py` e `user_routes.py` têm um único domínio cada; a mistura de camadas deles está no F-06.
Evidence:
```python
report_bp = Blueprint('reports', __name__)                   # :10
@report_bp.route('/reports/summary', methods=['GET'])        # :12
@report_bp.route('/categories', methods=['POST'])            # :167
```
Impact: alto acoplamento; qualquer mudança em categorias ou em relatórios mexe no mesmo arquivo, sem fronteira clara de camada.
Recommendation: separar em `routes/category_routes.py` + `controllers/category_controller.py` e `routes/report_routes.py` + `controllers/report_controller.py`, com as agregações em métodos de model, **sem mudar URLs** (PT-06 / §6-B).
Contract change: NO

### F-06 [HIGH] Regra de negócio na camada errada (AP-07)
File: routes/task_routes.py:11-299; routes/user_routes.py:10-211; routes/report_routes.py:12-223; services/notification_service.py (não importado)
Principle: SRP (SOLID) + MVC
Description: todas as 20 rotas dos blueprints executam ORM, validação e regra de domínio no próprio handler; não existe camada de controller. Regras de domínio fora do model:
- atraso (`overdue`): routes/task_routes.py:30-39, 71-80, 284-287; routes/user_routes.py:171-180; routes/report_routes.py:33-43, 132-135, enquanto `Task.is_overdue()` (models/task.py:50) nunca é chamado;
- estatísticas/taxa de conclusão: routes/task_routes.py:275-296; routes/report_routes.py:15-99, 111-151;
- validações de domínio inline: routes/task_routes.py:89-124, 166-213; routes/user_routes.py:54-72, 102-125; routes/report_routes.py:170-175, enquanto `Task.validate_status/validate_priority` (models/task.py:38-48) e `process_task_data` (utils/helpers.py:57) nunca são usados.
A pasta `services/` existe, mas nenhum módulo a importa (0 referências a `NotificationService`).
Evidence:
```python
@task_bp.route('/tasks', methods=['GET'])
def get_tasks():
    tasks = Task.query.all()                                     # :14 acesso a dados
    if t.due_date < datetime.utcnow(): ...                       # :31 regra de domínio
```
Impact: regra não reutilizável e não testável fora do HTTP; já gera inconsistência (F-09).
Recommendation: criar `controllers/` (fluxo + validação de entrada) e mover regras para os models (`Task.is_overdue`, consultas de agregação), deixando os blueprints só com a delegação (PT-07, §6-B).
Contract change: NO

### F-07 [HIGH] Exclusão física de entidades com histórico (AP-09)
File: routes/task_routes.py:232; routes/user_routes.py:140-145; routes/report_routes.py:218
Principle: Integridade (ACID) / preservação de histórico
Description: 3 rotas apagam fisicamente entidades com histórico de negócio:
- DELETE /users/<id> apaga o usuário **e todas as suas tasks** (cascata física, 140-142);
- DELETE /tasks/<id> apaga a task (232);
- DELETE /categories/<id> apaga a categoria (218); pelo comportamento padrão do relacionamento `backref='tasks'` do SQLAlchemy, as tasks dela têm `category_id` anulado, perdendo a classificação histórica.
Os passos do DELETE /users estão na mesma sessão (um único commit), então o problema não é atomicidade, e sim a perda de histórico.
Evidence:
```python
for t in tasks:
    db.session.delete(t)                       # routes/user_routes.py:141-142
db.session.delete(user)                        # routes/user_routes.py:145
```
Impact: relatórios de produtividade (/reports/summary, /reports/user/<id>) perdem os dados do usuário removido e de suas tasks; não há registro de quando nem de quem removeu.
Recommendation: soft delete (PT-09) com colunas `deleted_at` (DateTime) e `deleted_by` (FK users.id) em `users`, `tasks` e `categories`, preenchidas com o usuário autenticado (F-04). Ver o plano abaixo.
Contract change: NO no status/corpo das rotas de DELETE (mesmo 200 e mesma mensagem); efeitos colaterais no plano.

### F-08 [MEDIUM] Query N+1 / queries repetidas (AP-10)
File: routes/task_routes.py:42, 51, 275-279; routes/user_routes.py:22; routes/report_routes.py:15-28, 56, 163
Principle: Performance
Description:
- GET /tasks: `User.query.get` (42) e `Category.query.get` (51) dentro do loop: 1 + 2N queries.
- GET /users: `len(u.tasks)` (22) carrega o relacionamento lazy por usuário: 1 + N.
- GET /categories: `COUNT` por categoria (163): 1 + N.
- GET /reports/summary: `Task.query.filter_by(user_id=...)` por usuário (56), mais 12 COUNTs sequenciais (15-28) e uma leitura completa de tasks (30).
- GET /tasks/stats: 5 COUNTs (275-279) + leitura completa (281).
Evidence:
```python
for t in tasks:
    user = User.query.get(t.user_id)          # routes/task_routes.py:42
    cat = Category.query.get(t.category_id)   # routes/task_routes.py:51
```
Impact: o número de queries cresce linearmente com os dados (~21 queries para 10 tasks só no GET /tasks).
Recommendation: `joinedload`/`selectinload` dos relacionamentos e agregações com `GROUP BY` (`func.count`) em métodos de model (PT-10).
Contract change: NO

### F-09 [MEDIUM] Código duplicado (AP-11)
File: ver lista
Principle: DRY
Description:
- Regra de atraso copiada 6 vezes: routes/task_routes.py:30-39, 71-80, 284-287; routes/user_routes.py:171-180; routes/report_routes.py:34-36, 132-135. `Task.is_overdue()` (models/task.py:50-60) já existe e não é usado.
- Lista de status em 5 lugares: models/task.py:39; routes/task_routes.py:110, 177; utils/helpers.py:75, 110.
- Lista de roles em 3 lugares: routes/user_routes.py:71, 120; utils/helpers.py:111.
- Regex de e-mail em 3 lugares: routes/user_routes.py:61, 106; utils/helpers.py:21.
- Validação de título/prioridade/tags duplicada entre create e update: routes/task_routes.py:96-114 × 166-184, 140-144 × 209-213 (e utils/helpers.py:60-106).
- Taxa de conclusão em 3 lugares: routes/task_routes.py:296; routes/report_routes.py:67, 151; `calculate_percentage` (utils/helpers.py:14) é importado e nunca chamado.
- Serialização manual de task: routes/task_routes.py:17-28 e routes/user_routes.py:162-169 repetem `Task.to_dict()`.
Evidence:
```python
if t.due_date < datetime.utcnow():
    if t.status != 'done' and t.status != 'cancelled':        # 6 cópias
```
Impact: duplicação de **regra de negócio**: mudar o que é "atrasada" ou um status válido exige editar 5-6 lugares, com risco de divergência.
Recommendation: centralizar regras no model (`Task.is_overdue`, `Task.STATUSES`), constantes em `utils/constants.py` e validação de entrada em funções únicas do controller (PT-11).
Contract change: NO

### F-10 [MEDIUM] Erro engolido / sem handler central / validação ausente (AP-12)
File: `except:` sem tipo em routes/report_routes.py:186, 207, 221; routes/task_routes.py:62, 137, 204, 236; routes/user_routes.py:130, 149; utils/helpers.py:46, 49, 88. `except Exception` em routes/task_routes.py:151, 221; routes/user_routes.py:87; services/notification_service.py:23. Entrada não validada em routes/task_routes.py:96, 99, 113, 182, 261, 264; routes/report_routes.py:196-197; routes/user_routes.py:115.
Principle: Robustez / Fail-fast
Description: 16 `except` genéricos (12 sem tipo), nenhum `@app.errorhandler`/`register_error_handler`. O GET /tasks embrulha o handler inteiro num `except:` que devolve 500 sem registrar nada. Entradas que deveriam gerar 400 geram 500:
- `?priority=abc` / `?user_id=abc` em GET /tasks/search → `ValueError` em `int()` (261, 264);
- `"priority": "2"` em POST/PUT /tasks → `TypeError` em `priority < 1` (113, 182);
- `"title": 123` → `TypeError` em `len()` (96, 99, 167);
- body `null` em PUT /categories/<id> → `TypeError` em `'name' in data` (196-197);
- `"password": 1234` no PUT /users/<id> → `TypeError` em `len()` (115).
Evidence:
```python
if priority:
    tasks = tasks.filter(Task.priority == int(priority))   # routes/task_routes.py:261
```
Impact: falhas reais ficam invisíveis (sem log) e o cliente recebe 500 para erros de entrada.
Recommendation: `middlewares/error_handler.py` com `AppError`/`ValidationError`/`NotFoundError` e handler de 500 com log; validação de tipo na borda (controller); remover os `try/except` genéricos (PT-12).
Contract change: YES: entradas inválidas que hoje retornam 500 passam a retornar 400 com `{"error": ...}` (search com priority/user_id não numérico, priority/title de tipo errado em tasks, body ausente em PUT /categories, password não-string em PUT /users).

### F-11 [MEDIUM] Uso de API deprecated (AP-13)
File: ver tabela "Deprecated APIs"
Principle: Manutenibilidade
Description: o projeto roda em Python 3.14 e SQLAlchemy 2.1.1. `datetime.utcnow()` é deprecated desde o Python 3.12 (23 ocorrências, incluindo os 5 `default=`/`onupdate=` das colunas) e `Model.query.get()` é API legada do SQLAlchemy 2.x, que emite `LegacyAPIWarning` (16 ocorrências). Detecção estática; a prova por warnings em execução será feita no baseline da Fase 3.
Evidence:
```python
task = Task.query.get(task_id)                             # routes/task_routes.py:67
created_at = db.Column(db.DateTime, default=datetime.utcnow)   # models/task.py:15
```
Impact: as chamadas vão ser removidas em versões futuras; os warnings poluem o log.
Recommendation: `db.session.get(Model, id)` e um helper `utils/time.py::utc_now()` que preserve o formato atual (UTC naive) (PT-13).
Contract change: NO

### F-12 [LOW] Código morto e dependências sem uso (AP-14)
File: services/notification_service.py:1-48; utils/helpers.py:9-116; models/task.py:38-60; models/user.py:34-38; imports em app.py:7, routes/task_routes.py:7, routes/user_routes.py:6, routes/report_routes.py:7-8, models/task.py:3, utils/helpers.py:3-7; requirements.txt:4-6
Principle: Clean Code
Description:
- `NotificationService`: módulo inteiro nunca importado (0 referências).
- `utils/helpers.py`: as 9 funções e as 7 constantes não são usadas fora do arquivo (`format_date` e `calculate_percentage` são importados em routes/report_routes.py:7, mas nunca chamados).
- `Task.validate_status`, `Task.validate_priority`, `Task.is_overdue`, `User.is_admin`: nunca chamados.
- Imports sem uso: `os, sys, json, datetime` só usa `datetime` (app.py:7); `json, os, sys, time` (routes/task_routes.py:7); `hashlib, json` (routes/user_routes.py:6); `json` (routes/report_routes.py:8, models/task.py:3); `os, json, sys, math, hashlib` (utils/helpers.py:3-7).
- Dependências declaradas e nunca importadas: `marshmallow`, `requests`, `python-dotenv` (requirements.txt:4-6).
Evidence:
```python
from utils.helpers import format_date, calculate_percentage     # routes/report_routes.py:7, nunca usados
```
Impact: ruído na leitura, superfície de ataque e dependências desnecessárias.
Recommendation: remover o código morto ou reaproveitá-lo onde há duplicação (`is_overdue`, `calculate_percentage`, `is_admin` no auth); `python-dotenv` passa a ser usado pela config; remover `marshmallow` e `requests` (PT-14).
Contract change: NO

### F-13 [LOW] Logging inadequado / debug fixo (AP-14)
File: routes/task_routes.py:149, 153, 219, 234; routes/user_routes.py:83, 89, 147; services/notification_service.py:21, 24; utils/helpers.py:39, 41; app.py:34
Principle: Clean Code
Description: 11 `print(` como log de aplicação no código servido (fora o seed.py, onde `print` é saída de CLI legítima) e `debug=True` fixo com `host='0.0.0.0'`, o que expõe o debugger do Werkzeug na rede.
Evidence:
```python
app.run(debug=True, host='0.0.0.0', port=5000)     # app.py:34
print(f"Task deletada: {task_id}")                 # routes/task_routes.py:234
```
Impact: sem nível nem destino configurável; o debugger interativo fica acessível se a aplicação for exposta.
Recommendation: módulo `logging` com logger por módulo; `DEBUG`/`HOST`/`PORT` vindos da config com default seguro (PT-14 / PT-02).
Contract change: NO

### F-14 [LOW] Magic numbers, verbosidade e nomes curtos (AP-14)
File: routes/task_routes.py:96-114, 141, 167-183, 210; routes/user_routes.py:64, 115; routes/report_routes.py:24-28, 45, 129; models/task.py:39-48; models/user.py:34-38
Principle: Clean Code
Description: limites de domínio inline (título 3/200, prioridade 1-5, prioridade padrão 3, senha mínima 4, janela de 7 dias, "alta prioridade" `<= 2`); 3 `type(x) == list` em vez de `isinstance` (routes/task_routes.py:141, 210; utils/helpers.py:103); 3 `if cond: return True else: return False` (models/task.py:39-43, 46-48; models/user.py:35-38); nomes `p1..p5`, `u`, `t`, `c`, `cat` em funções longas.
Evidence:
```python
p1 = Task.query.filter_by(priority=1).count()      # routes/report_routes.py:24
if t.priority <= 2:                                # routes/report_routes.py:129
```
Impact: regras implícitas e espalhadas, difíceis de alterar.
Recommendation: constantes nomeadas em `utils/constants.py`, `isinstance`, retorno direto de expressões booleanas (PT-14).
Contract change: NO

## Deprecated APIs
| API em uso | Ocorrências | Local | Equivalente moderno |
|------------|-------------|-------|---------------------|
| `datetime.utcnow` (Python 3.12+) | 23 | models/category.py:11; models/task.py:15, 16 (×2), 52; models/user.py:14; routes/report_routes.py:35, 42, 45, 71, 133; routes/task_routes.py:31, 72, 215, 285; routes/user_routes.py:172; seed.py:66, 67, 69, 70, 74; services/notification_service.py:35; utils/helpers.py:38 | `datetime.now(timezone.utc)` (via `utils/time.py::utc_now()`, mantendo UTC naive para não mudar o formato das datas) |
| `Model.query.get(id)` (SQLAlchemy 2.x, `LegacyAPIWarning`) | 16 | routes/report_routes.py:105, 192, 213; routes/task_routes.py:42, 51, 67, 117, 122, 158, 188, 195, 227; routes/user_routes.py:29, 94, 136, 155 | `db.session.get(Model, id)` |

## Positive Points
- Não há SQL Injection: todo acesso a dados usa o ORM (`filter_by`, `filter`, `like(f'%{q}%')`, que é parametrizado) (AP-01 ausente).
- Não há estado global mutável compartilhado entre requisições: `db = SQLAlchemy()` está em módulo próprio com `init_app`, o que já evita import circular (AP-08 ausente).
- Models ORM por domínio (`models/task.py`, `user.py`, `category.py`) com relacionamentos declarados: serão mantidos.
- Blueprints por domínio já existem em `routes/`.
- Unicidade de e-mail tratada com 409; respostas de erro já seguem um formato único `{"error": ...}`.

## Refactoring Plan (Phase 3 preview)
Strategy: B) evolução incremental (§6-B): manter models ORM, blueprints e o nome `routes/` (equivalente a `views/` da §4), criar a camada que falta (`controllers/`) e a infraestrutura (`config/`, `middlewares/`, app factory).
Target structure:
```
app.py                        # create_app() + app = create_app() (mantém "from app import app, db" do seed.py)
config/__init__.py, config/settings.py   # Settings do ambiente (SECRET_KEY, DATABASE_URL, DEBUG, HOST, PORT, TOKEN_MAX_AGE)
database.py                   # db = SQLAlchemy() + init_app (create_all + migração idempotente das colunas de soft delete)
models/task.py, user.py, category.py     # mantidos (nomes existentes; desvio da §4 "<dominio>_model.py" justificado pela estratégia B:
                              #   o seed.py importa models.task/models.user/models.category); recebem regras (is_overdue,
                              #   STATUSES, consultas ativas, agregações) e soft delete
controllers/task_controller.py, user_controller.py, category_controller.py, report_controller.py, health_controller.py
routes/__init__.py            # register_blueprints(app)
routes/task_routes.py, user_routes.py, report_routes.py, category_routes.py (novo), health_routes.py (/health e /, saem do app.py)
middlewares/error_handler.py  # AppError, ValidationError, NotFoundError... + register_error_handlers
middlewares/auth.py           # emissão/verificação de token assinado + require_auth(roles)
utils/constants.py, utils/time.py (utc_now)   # utils/helpers.py reduzido ao que for reutilizado
services/                     # removido: NotificationService é código morto, com credencial hardcoded e sem integração ativa
.env.example; README.md atualizado; requirements.txt sem marshmallow/requests
```
Soft delete (F-07, PT-09):
- `users`, `tasks`, `categories` ganham `deleted_at` (DateTime, nulo = ativo) e `deleted_by` (FK `users.id`, o autenticado que removeu).
- DELETE /users/<id>: marca o usuário e, em **cascata lógica**, as tasks ativas dele (mesmo `deleted_at`/`deleted_by`), preservando o efeito visível de hoje (as tasks somem de GET /tasks). Nada é apagado.
- DELETE /tasks/<id>: marca a task. DELETE /categories/<id>: marca a categoria; as tasks mantêm o `category_id` (não é mais anulado).
- Leituras de negócio (GET /tasks, /tasks/<id>, /tasks/search, /tasks/stats, /users, /users/<id>, /users/<id>/tasks, /categories, PUT/DELETE por id, validação de `user_id`/`category_id` em POST/PUT /tasks, /login) ignoram registros removidos → 404/401 como se não existissem.
- Relatórios (/reports/summary, /reports/user/<id>) são o histórico: continuam mostrando usuários removidos e contando suas tasks.
- Migração: o `create_all` não adiciona colunas a tabelas existentes; `database.py` executa `ALTER TABLE ... ADD COLUMN deleted_at/deleted_by` só quando a coluna não existe (idempotente). Num banco novo (seed), o `create_all` já cria as colunas.
- Efeito colateral: o e-mail de um usuário removido continua reservado (POST /users com o mesmo e-mail → 409), para preservar o histórico.
Contract changes requiring approval:
- F-03: `password` removido das respostas de GET /users/<id>, POST /users, PUT /users/<id> e POST /login.
- F-04: o `token` do /login passa a ser assinado; DELETE /tasks/<id> exige token (401); DELETE /users/<id> e DELETE /categories/<id> exigem token de admin (401/403); definir `role` ≠ `user` no POST /users ou `role`/`active` no PUT /users/<id> exige token de admin (401/403).
- F-10: entradas inválidas que hoje dão 500 passam a dar 400 `{"error": ...}`.
- F-07: e-mail de usuário removido continua indisponível para novo cadastro (409); relatórios continuam incluindo dados de usuários removidos.
Out of scope: leituras públicas que expõem nome/e-mail (GET /users, /reports/*) continuam sem autenticação para não ampliar a mudança de contrato (recomendação: protegê-las numa próxima etapa); paginação; envio real de e-mail (o serviço morto é removido; se a notificação for desejada, deve ser reintroduzida com config do ambiente).

================================
Total: 14 findings
================================
