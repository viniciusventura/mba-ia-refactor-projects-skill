================================
ARCHITECTURE AUDIT REPORT
================================
Project:  task-manager-api
Stack:    Python 3.14.4 + Flask 3.0.0 + Flask-SQLAlchemy 3.1.1 (SQLAlchemy 2.1.1)
Files:    17 analyzed | ~1158 lines of code (inclui seed.py)
Date:     2026-10-15
Architecture: B) Parcialmente em camadas: existem `models/`, `routes/`, `services/` e `utils/`, mas os handlers de `routes/` concentram ORM, validação e regra de negócio; não há controllers; `services/` e `utils/helpers.py` nunca são importados de forma útil.

## Summary
CRITICAL: 5 | HIGH: 3 | MEDIUM: 4 | LOW: 4

| ID | Severity | Anti-pattern | Location |
|----|----------|--------------|----------|
| F-01 | CRITICAL | Credenciais hardcoded (AP-02) | app.py:13, services/notification_service.py:9-10 |
| F-02 | CRITICAL | Armazenamento inseguro de senha (AP-03) | models/user.py:29, 32 |
| F-03 | CRITICAL | Exposição de dados sensíveis (AP-04) | models/user.py:21; routes/user_routes.py:33, 85, 129, 209 |
| F-04 | CRITICAL | Endpoint sensível sem autenticação (AP-05) | routes/user_routes.py:27, 42-78, 92-125, 134, 210; routes/task_routes.py:85, 156, 225; routes/report_routes.py:167, 190, 211 |
| F-05 | CRITICAL | God File (AP-06) | routes/report_routes.py:1-223 |
| F-06 | HIGH | Leitura de dados de outros usuários sem autenticação (AP-05) | routes/user_routes.py:10, 153; routes/report_routes.py:12, 103 |
| F-07 | HIGH | Regra de negócio na camada errada (AP-07) | routes/task_routes.py:30-39, 71-80, 96-124, 177-198, 275-297; routes/user_routes.py:54-72, 140-142, 171-180, 197-211; services/notification_service.py:1-48 |
| F-08 | HIGH | Exclusão física de entidades com histórico (AP-09) | routes/task_routes.py:232; routes/user_routes.py:140-145; routes/report_routes.py:218 |
| F-09 | MEDIUM | Query N+1 / queries repetidas (AP-10) | routes/task_routes.py:42, 51, 275-281; routes/user_routes.py:22; routes/report_routes.py:15-30, 56, 163 |
| F-10 | MEDIUM | Código duplicado (AP-11) | routes/task_routes.py:30-39, 71-80, 283-287, 110, 177, 96-100, 167-170, 140-144, 209-213, 17-28; routes/user_routes.py:171-180, 61, 106, 71, 120; routes/report_routes.py:33-36, 132-135, 67, 151; models/task.py:39, 50-60 |
| F-11 | MEDIUM | Erro engolido / sem handler central / validação ausente (AP-12) | routes/task_routes.py:62, 113, 137, 151, 167, 182, 204, 221, 236, 261, 264; routes/user_routes.py:87, 130, 149; routes/report_routes.py:186, 196-197, 207, 221 |
| F-12 | MEDIUM | Uso de API deprecated (AP-13) | 34 ocorrências (ver tabela Deprecated APIs) |
| F-13 | LOW | Código morto e imports/dependências sem uso (AP-14) | app.py:7; routes/*.py imports; utils/helpers.py:1-116; models/task.py:3, 38-60; models/user.py:34-38; requirements.txt:4-6 |
| F-14 | LOW | Logging inadequado (AP-14) | routes/task_routes.py:149, 153, 219, 234; routes/user_routes.py:83, 89, 147; app.py:34 |
| F-15 | LOW | Magic numbers / strings (AP-14) | routes/task_routes.py:96, 99, 113, 167, 169, 182; routes/user_routes.py:64, 115; routes/report_routes.py:24-28, 45, 129 |
| F-16 | LOW | Legibilidade: verbosidade e nomes ruins (AP-14) | models/task.py:38-60; models/user.py:34-38; routes/task_routes.py:141, 210; routes/report_routes.py:24-28 |

## Findings

### F-01 [CRITICAL] Credenciais hardcoded (AP-02)
File: app.py:13, services/notification_service.py:9-10
Principle: OWASP A07 / 12-Factor App (config no ambiente)
Description: 3 segredos literais no código-fonte, sem leitura de ambiente: a `SECRET_KEY` do Flask e o usuário/senha SMTP do serviço de notificação. A URI do banco (app.py:11) também é literal (config, não segredo). O `NotificationService` é código morto (nunca importado), mas o segredo continua versionado.
Evidence:
```python
app.config['SECRET_KEY'] = 'super-secret-key-123'          # app.py:13
self.email_user = 'taskmanager@gmail.com'                  # notification_service.py:9
self.email_password = 'senha123'                           # notification_service.py:10
```
Impact: quem tem acesso ao repositório conhece a chave que vai assinar os tokens (F-04) e a senha da conta de e-mail. Trocar o segredo exige alterar código e fazer deploy.
Recommendation: criar `config/settings.py` lendo `SECRET_KEY`, `DATABASE_URL`, `DEBUG`, `HOST`, `PORT` do ambiente (com `python-dotenv`, já declarado), defaults inofensivos só para desenvolvimento, e `.env.example` (PT-02). Remover `services/notification_service.py` (morto, ver F-07/F-13), eliminando a credencial SMTP.
Contract change: NO

### F-02 [CRITICAL] Armazenamento inseguro de senha (AP-03)
File: models/user.py:29, 32
Principle: OWASP A02 Cryptographic Failures
Description: senhas gravadas como MD5 sem salt (2 ocorrências: gravação e verificação). Não há `bcrypt`/`argon2`/`pbkdf2`/`werkzeug.security` no projeto.
Evidence:
```python
self.password = hashlib.md5(pwd.encode()).hexdigest()
return self.password == hashlib.md5(pwd.encode()).hexdigest()
```
Impact: hashes MD5 de senhas curtas (o seed usa `1234`, `abcd`, `pass`) são revertidos instantaneamente por rainbow tables; somado ao F-03, qualquer cliente obtém as senhas.
Recommendation: `werkzeug.security.generate_password_hash`/`check_password_hash` (PBKDF2/scrypt com salt) (PT-03). Hashes MD5 legados (32 hex) continuam aceitos no login e são regravados no formato novo na primeira autenticação bem-sucedida. `seed.py` já usa `set_password`, então passa a gerar o hash novo sem mudança.
Contract change: NO

### F-03 [CRITICAL] Exposição de dados sensíveis (AP-04)
File: models/user.py:21; routes/user_routes.py:33, 85, 129, 209
Principle: OWASP A01/A09
Description: `User.to_dict()` inclui o hash da senha, e o serializador chega a 4 respostas: `GET /users/<id>`, `POST /users`, `PUT /users/<id>` e `POST /login` (objeto `user`).
Evidence:
```python
'password': self.password,          # models/user.py:21
'user': user.to_dict(),             # routes/user_routes.py:209 (login)
```
Impact: qualquer cliente anônimo lê o hash MD5 de qualquer usuário (`GET /users/1` → admin) e, pelo F-02, a senha em texto.
Recommendation: remover `password` do serializador de saída (PT-04).
Contract change: YES: a chave `password` deixa de existir nas respostas de `GET /users/<id>`, `POST /users`, `PUT /users/<id>` e no objeto `user` de `POST /login`.

### F-04 [CRITICAL] Endpoint sensível sem autenticação (AP-05)
File: routes/user_routes.py:27, 42-78, 92-125, 134, 210; routes/task_routes.py:85, 156, 225; routes/report_routes.py:167, 190, 211
Principle: OWASP A01 Broken Access Control
Description: o projeto não tem nenhum mecanismo de autenticação (`grep auth|jwt|login_required|before_request` só encontra o token falso). O login devolve `'fake-jwt-token-' + id`, previsível e não verificado por nenhuma rota. Combinação agravante: `role` é aceito do body na criação e edição de usuário. Classificação das rotas sem auth incluídas aqui (10):
- Classe 2 (destrutiva): `DELETE /tasks/<id>`, `DELETE /users/<id>` (apaga também todas as tasks do usuário), `DELETE /categories/<id>`.
- Classe 3 (escrita em dado compartilhado/de terceiros): `POST /tasks` (cria task para qualquer `user_id`), `PUT /tasks/<id>` (edita task de qualquer pessoa), `POST /categories`, `PUT /categories/<id>`.
- Classe 4 (credencial e privilégio): `PUT /users/<id>` (troca senha, e-mail, `role` e `active` de qualquer usuário, inclusive do admin); `POST /users` com `role: "admin"` (auto-promoção).
- Classe 5 com hash: `GET /users/<id>` (devolve o hash, F-03).
Evidence:
```python
'token': 'fake-jwt-token-' + str(user.id)          # user_routes.py:210
role = data.get('role', 'user')                     # user_routes.py:52
user.role = data['role']                            # user_routes.py:122
```
Impact: um anônimo cria um admin para si, assume a conta de qualquer usuário trocando a senha via `PUT /users/1`, edita/apaga tasks e categorias de todos e apaga usuários com todo o histórico de tasks.
Recommendation (PT-05): token assinado com `SECRET_KEY` (`itsdangerous.URLSafeTimedSerializer`, já instalado com o Flask, com expiração) emitido no login; `middlewares/auth.py` com decorator `require_auth(roles=None)` lendo `Authorization: Bearer <token>`, rejeitando token inválido, expirado ou de usuário inativo/removido. Proteção por rota:
- `DELETE /users/<id>`, `POST /categories`, `PUT /categories/<id>`, `DELETE /categories/<id>`: papel `admin`.
- `POST /tasks`: autenticado.
- `PUT /tasks/<id>`, `DELETE /tasks/<id>`: `admin`, `manager` ou dono da task (`task.user_id`).
- `PUT /users/<id>`: o próprio usuário ou `admin`; os campos `role` e `active` só por `admin`.
- `POST /users`: continua público para `role` `user`; `role` `admin`/`manager` exige token de `admin`.
- `GET /users/<id>`: autenticado.
Contract change: YES: o campo `token` do login passa a ser um token assinado (mesma chave, outro formato); as rotas acima respondem 401 sem token/token inválido e 403 sem o papel/propriedade exigidos; `POST /users` com `role` diferente de `user` responde 401/403 sem token de admin.

Rotas de escrita que ficam públicas (teste "não esqueci nada"): `POST /login` (autenticação) e `POST /users` com `role` `user` (cadastro público de usuário comum). Leituras públicas mantidas: `GET /`, `GET /health`, `GET /tasks`, `GET /tasks/<id>`, `GET /tasks/search`, `GET /tasks/stats`, `GET /categories` (quadro de tarefas compartilhado da equipe, sem senha, e-mail ou token).

### F-05 [CRITICAL] God File (AP-06)
File: routes/report_routes.py:1-223
Principle: SRP (SOLID) + MVC
Description: o arquivo de rotas de relatório acumula 2 domínios e 4 responsabilidades. Mapa: rotas (12, 103, 157, 167, 190, 211); acesso a dados via ORM (15-30, 46-56, 105, 109, 159, 163, 183-184, 192, 205, 213, 218-219); regra de negócio (atraso 33-43 e 132-135, janela de 7 dias 45-51, taxa de conclusão 59-67 e 151, prioridade alta 129-130); validação de entrada (169-175, 196-202). Domínios: relatórios (12-155) e CRUD completo de categorias (157-223). `task_routes.py` e `user_routes.py` também misturam camadas, mas são coesos num único domínio; ficam no F-07.
Evidence:
```python
report_bp = Blueprint('reports', __name__)
@report_bp.route('/categories', methods=['POST'])     # CRUD de categorias dentro do blueprint de relatórios
def create_category(): ...
    db.session.add(category)
```
Impact: qualquer mudança em categorias mexe no módulo de relatórios; regra de atraso e de métricas não é reaproveitável nem testável fora do HTTP.
Recommendation: decompor (PT-06): `routes/report_routes.py` (só relatórios, delegando), `routes/category_routes.py` (novo, mesmas URLs), `controllers/report_controller.py`, `controllers/category_controller.py`; agregações e regra de atraso em `models/` (`Task.is_overdue()`, consultas agregadas no model).
Contract change: NO

### F-06 [HIGH] Leitura de dados de outros usuários sem autenticação (AP-05)
File: routes/user_routes.py:10, 153; routes/report_routes.py:12, 103
Principle: OWASP A01 Broken Access Control
Description: 4 rotas de leitura (classe 5, sem senha/hash) expõem dados pessoais e de produtividade de todos os usuários a anônimos: `GET /users` (nome, e-mail, papel), `GET /users/<id>/tasks`, `GET /reports/summary` (produtividade por usuário) e `GET /reports/user/<id>` (e-mail + estatísticas). Severidade HIGH pela régua do catálogo (classe 5 sem senha/hash/token).
Evidence:
```python
@user_bp.route('/users', methods=['GET'])
def get_users():
    users = User.query.all()          # e-mails de todos, sem autenticação
```
Impact: enumeração de usuários e e-mails (insumo para phishing e para atacar o login) e exposição de métricas individuais.
Recommendation: exigir autenticação (`require_auth()`) nessas 4 rotas (PT-05).
Contract change: YES: `GET /users`, `GET /users/<id>/tasks`, `GET /reports/summary` e `GET /reports/user/<id>` respondem 401 sem token válido.

### F-07 [HIGH] Regra de negócio na camada errada (AP-07)
File: routes/task_routes.py:30-39, 71-80, 96-124, 177-198, 275-297; routes/user_routes.py:54-72, 140-142, 171-180, 197-211; services/notification_service.py:1-48
Principle: SRP (SOLID) + MVC
Description: os handlers de `task_routes.py` (7 handlers) e `user_routes.py` (7 handlers) fazem, no mesmo corpo, acesso ao ORM, validação de entrada, regra de domínio (atraso, taxa de conclusão, verificação de senha, exclusão em cascata) e resposta HTTP. Não existe camada de controller. Os métodos de domínio já existentes no model (`Task.is_overdue`, `Task.validate_status`, `Task.validate_priority`, `User.is_admin`) nunca são chamados. A pasta `services/` existe mas não é importada por nenhum módulo.
Evidence:
```python
if t.due_date:                                   # task_routes.py:30, regra de atraso no handler
    if t.due_date < datetime.utcnow():
        if t.status != 'done' and t.status != 'cancelled':
```
Impact: regras duplicadas e divergentes (F-10), impossíveis de testar sem HTTP; a camada `services/` passa a impressão de uma integração que não existe.
Recommendation: criar `controllers/` (task, user, category, report, health) com o fluxo; rotas só delegam; regra de domínio no model, reutilizando `Task.is_overdue()` (PT-07). Remover `services/notification_service.py` (morto; ligá-lo enviaria e-mails reais, o que muda o comportamento).
Contract change: NO

### F-08 [HIGH] Exclusão física de entidades com histórico (AP-09)
File: routes/task_routes.py:232; routes/user_routes.py:140-145; routes/report_routes.py:218
Principle: Integridade (ACID) / preservação de histórico
Description: 3 exclusões físicas (`db.session.delete`). `DELETE /users/<id>` apaga também todas as tasks do usuário (140-142), destruindo histórico de trabalho; `DELETE /categories/<id>` apaga a categoria e deixa tasks com `category_id` órfão (SQLite sem `PRAGMA foreign_keys`); `DELETE /tasks/<id>` apaga a task.
Evidence:
```python
tasks = Task.query.filter_by(user_id=user_id).all()
for t in tasks:
    db.session.delete(t)                 # user_routes.py:140-142
```
Impact: perda irreversível de histórico (relatórios de produtividade mudam retroativamente) e referências órfãs.
Recommendation: soft delete (PT-09) nas 3 tabelas (`deleted`, `deleted_at`, `deleted_by`), registrando quando e quem removeu; `DELETE /users/<id>` marca as tasks do usuário como removidas na mesma transação (cascata lógica, PT-09 regra 5), em vez de apagá-las. Detalhes e migração no Refactoring Plan.
Contract change: YES (mínima): status e corpo das respostas de `DELETE` não mudam; registros removidos continuam no banco e respondem 404 nas leituras por id e somem das listagens, como antes; os relatórios (`/reports/*`, leituras históricas) passam a continuar contando-os.

### F-09 [MEDIUM] Query N+1 / queries repetidas (AP-10)
File: routes/task_routes.py:42, 51, 275-281; routes/user_routes.py:22; routes/report_routes.py:15-30, 56, 163
Principle: Performance
Description: 4 laços com query por item e 2 sequências de COUNTs repetidos: `GET /tasks` faz `User.query.get` e `Category.query.get` por task (até 2N+1 queries); `GET /users` acessa o relacionamento lazy `u.tasks` por usuário; `GET /reports/summary` faz 12 COUNTs + `Task.query.all()` + 1 query por usuário; `GET /categories` faz 1 COUNT por categoria; `GET /tasks/stats` faz 5 COUNTs + `Task.query.all()`.
Evidence:
```python
for t in tasks:
    user = User.query.get(t.user_id)       # task_routes.py:42
    cat = Category.query.get(t.category_id)  # task_routes.py:51
```
Impact: o número de queries cresce linearmente com o volume (com 10 tasks, `GET /tasks` faz até 21 queries).
Recommendation: eager loading (`joinedload`/`selectinload`) e agregações `GROUP BY` (`func.count` por status/prioridade/usuário/categoria) (PT-10).
Contract change: NO

### F-10 [MEDIUM] Código duplicado (AP-11)
File: routes/task_routes.py:30-39, 71-80, 283-287, 110, 177, 96-100, 167-170, 140-144, 209-213, 17-28; routes/user_routes.py:171-180, 61, 106, 71, 120; routes/report_routes.py:33-36, 132-135, 67, 151; models/task.py:39, 50-60
Principle: DRY
Description: regra de atraso copiada 6 vezes (task_routes 30-39, 71-80, 283-287; user_routes 171-180; report_routes 33-36, 132-135) enquanto `Task.is_overdue()` (models/task.py:50-60) nunca é chamado; lista de status 3 vezes (task_routes 110, 177; models/task.py:39) e mais em utils/helpers.py:75, 110; lista de papéis 2 vezes (user_routes 71, 120); regex de e-mail 2 vezes (user_routes 61, 106) mais `validate_email` não usado; validação de título duplicada em create/update (task_routes 96-100, 167-170); conversão de tags duplicada (140-144, 209-213); serialização de task manual (task_routes 17-28) repetindo `Task.to_dict`; fórmula de taxa de conclusão 3 vezes (task_routes 296; report_routes 67, 151) enquanto `calculate_percentage` é importado e não usado.
Evidence:
```python
if status not in ['pending', 'in_progress', 'done', 'cancelled']:          # task_routes.py:110
if data['status'] not in ['pending', 'in_progress', 'done', 'cancelled']:  # task_routes.py:177
```
Impact: duplicação de regra de negócio: mudar o critério de atraso ou os status válidos exige editar 6 lugares, com risco de relatórios e listagens divergirem.
Recommendation: centralizar regra no model (`Task.is_overdue`), constantes em `utils/constants.py` e validação em funções únicas no controller (PT-11).
Contract change: NO

### F-11 [MEDIUM] Erro engolido / sem handler central / validação ausente (AP-12)
File: routes/task_routes.py:62, 113, 137, 151, 167, 182, 204, 221, 236, 261, 264; routes/user_routes.py:87, 130, 149; routes/report_routes.py:186, 196-197, 207, 221
Principle: Robustez / Fail-fast
Description: 12 `except` genéricos nas rotas (8 `except:` sem tipo, 4 `except Exception`), mais 4 em código morto (utils/helpers.py:46, 49, 88; services/notification_service.py:23). Não há `@app.errorhandler`/`register_error_handler`. Entradas sem validação de tipo que geram 500: `priority` não numérico em `POST/PUT /tasks` (113, 182: comparação `str < int`), `title` não string em `PUT /tasks` (167), `?priority=abc` e `?user_id=abc` em `GET /tasks/search` (261, 264: `int()`), `PUT /categories/<id>` sem body (196-197: `'name' in None`). Prova em execução fica para o baseline da Fase 3.
Evidence:
```python
if priority < 1 or priority > 5:                       # task_routes.py:113, priority="alta" → TypeError → 500
tasks = tasks.filter(Task.priority == int(priority))   # task_routes.py:261
```
Impact: entrada inválida do cliente vira 500 sem log útil; `except:` sem tipo engole até erros de programação.
Recommendation: `middlewares/error_handler.py` com `AppError` + `register_error_handlers` (404/405/500 em JSON `{'error': ...}`), validação de tipos na borda (controller) e remoção dos `except` genéricos (PT-12).
Contract change: YES: as entradas inválidas listadas passam de 500 para 400 com `{'error': ...}`; erros do próprio Flask (404 de rota inexistente, 405) mantêm o status, mas o corpo passa de HTML para JSON `{'error': ...}`; 500 inesperado devolve `{'error': 'Erro interno do servidor'}`.

### F-12 [MEDIUM] Uso de API deprecated (AP-13)
File: ver tabela Deprecated APIs
Principle: Manutenibilidade
Description: 34 ocorrências em código da aplicação: 18 `datetime.utcnow` (deprecated no Python 3.12+, o venv usa 3.14.4) e 16 `Model.query.get()` (`LegacyAPIWarning` no SQLAlchemy 2.x, instalado 2.1.1). Mais 5 `utcnow` em `seed.py`. Detecção estática (versão + padrão); o warning emitido será registrado no baseline da Fase 3.
Evidence:
```python
task = Task.query.get(task_id)                  # task_routes.py:67
if t.due_date < datetime.utcnow():              # task_routes.py:31
```
Impact: as APIs serão removidas em versões futuras; os warnings poluem o log.
Recommendation: `db.session.get(Model, id)` e `utils/time.py` com `utc_now()` baseado em `datetime.now(timezone.utc)` (gravando naive UTC para manter o formato das datas nas respostas) (PT-13).
Contract change: NO

### F-13 [LOW] Código morto e imports/dependências sem uso (AP-14)
File: app.py:7; routes/task_routes.py:7; routes/user_routes.py:6; routes/report_routes.py:7-8; models/task.py:3, 38-60; models/user.py:34-38; utils/helpers.py:1-116; services/notification_service.py:1-48; requirements.txt:4-6
Principle: Clean Code
Description: 13 imports sem uso (app.py: `os`, `sys`, `json`; task_routes: `json`, `os`, `sys`, `time`; user_routes: `hashlib`, `json`; report_routes: `format_date`, `calculate_percentage`, `json`; models/task.py: `json`); todas as 9 funções e 7 constantes de `utils/helpers.py` nunca usadas (o único import, report_routes:7, não as chama); 4 métodos de model nunca chamados (`validate_status`, `validate_priority`, `is_overdue`, `is_admin`); `services/notification_service.py` nunca importado; dependências declaradas e nunca importadas: `marshmallow`, `requests` (requirements.txt:4-5) e `python-dotenv` (6).
Evidence:
```python
import os, sys, json, datetime     # app.py:7, só datetime é usado
```
Impact: ruído de leitura e falsa impressão de funcionalidades existentes.
Recommendation: remover imports e funções mortas; reaproveitar `is_overdue`/`is_admin`; mover constantes úteis para `utils/constants.py`; usar `python-dotenv` no config e remover `marshmallow`/`requests` do manifesto (PT-14).
Contract change: NO

### F-14 [LOW] Logging inadequado (AP-14)
File: routes/task_routes.py:149, 153, 219, 234; routes/user_routes.py:83, 89, 147; app.py:34
Principle: Clean Code
Description: 7 `print` usados como log de aplicação nas rotas (mais 4 em código morto: notification_service.py:21, 24; helpers.py:39, 41) e `debug=True` fixo no entry point. Os `print` do `seed.py` são saída de CLI e não entram.
Evidence:
```python
print(f"Task criada: {task.id} - {task.title}")    # task_routes.py:149
app.run(debug=True, host='0.0.0.0', port=5000)      # app.py:34
```
Impact: sem nível nem destino configurável; debugger do Werkzeug ligado em `0.0.0.0` permite execução de código remoto se exposto.
Recommendation: `logging.getLogger(__name__)` e `DEBUG` vindo de `Settings` (default `False`) (PT-14).
Contract change: NO

### F-15 [LOW] Magic numbers / strings (AP-14)
File: routes/task_routes.py:96, 99, 113, 167, 169, 182; routes/user_routes.py:64, 115; routes/report_routes.py:24-28, 45, 129
Principle: Clean Code
Description: 13 literais de regra: tamanho de título 3/200 (4×), faixa de prioridade 1-5 (2×), tamanho mínimo de senha 4 (2×), mapeamento prioridade→rótulo 1..5 (report_routes 24-28), janela de 7 dias (45), "alta prioridade" `<= 2` (129).
Evidence:
```python
if t.priority <= 2:            # report_routes.py:129
```
Impact: limites espalhados e sem nome; mudar uma regra exige caçar literais.
Recommendation: constantes nomeadas em `utils/constants.py` (PT-14).
Contract change: NO

### F-16 [LOW] Legibilidade: verbosidade e nomes ruins (AP-14)
File: models/task.py:38-60; models/user.py:34-38; routes/task_routes.py:141, 210; routes/report_routes.py:24-28
Principle: Clean Code
Description: `if cond: return True else: return False` (models/task.py:40-43, 46-48; models/user.py:35-38), `if` aninhado em 3 níveis em `is_overdue` (50-60), `type(x) == list` em vez de `isinstance` (task_routes 141, 210), variáveis `p1`..`p5` (report_routes 24-28).
Evidence:
```python
if self.role == 'admin':
    return True
else:
    return False
```
Impact: leitura mais lenta, sem efeito funcional.
Recommendation: expressões booleanas diretas, `isinstance`, nomes descritivos (PT-14).
Contract change: NO

## Deprecated APIs
| API em uso | Ocorrências | Local | Equivalente moderno |
|------------|-------------|-------|---------------------|
| `datetime.utcnow()` | 18 (+5 no seed) | models/category.py:11; models/task.py:15, 16 (2×), 52; models/user.py:14; routes/report_routes.py:35, 42, 45, 71, 133; routes/task_routes.py:31, 72, 215, 285; routes/user_routes.py:172; services/notification_service.py:35; utils/helpers.py:38; seed.py:66, 67, 69, 70, 74 | `datetime.now(timezone.utc)` via `utils/time.utc_now()` |
| `Model.query.get(id)` | 16 | routes/report_routes.py:105, 192, 213; routes/task_routes.py:42, 51, 67, 117, 122, 158, 188, 195, 227; routes/user_routes.py:29, 94, 136, 155 | `db.session.get(Model, id)` |

## Positive Points
- Todo o acesso a dados usa o ORM (`filter_by`, `filter`, `like` parametrizado): nenhuma SQL injection (AP-01 ausente).
- `db = SQLAlchemy()` com `init_app`: sem estado global mutável (AP-08 ausente).
- Models já separados por domínio e Blueprints por domínio em `routes/`.
- Seed em script separado (`seed.py`), reutilizando o app.

## Refactoring Plan (Phase 3 preview)
Strategy: B) evolução incremental: manter `models/`, `routes/` (camada View, equivalente a `views/` da §4), Blueprints e URLs; criar as camadas que faltam.
Target structure (§4 Flask, mantendo `routes/` por já existir):
- `app.py`: só `create_app()` + `app = create_app()` (mantém `from app import app, db` do seed) + `if __name__ == "__main__"`.
- `config/settings.py`: `Settings` lendo o ambiente (`SECRET_KEY`, `DATABASE_URL`, `DEBUG`, `HOST`, `PORT`, `TOKEN_MAX_AGE`), `.env` via `python-dotenv`.
- `database.py`: `db = SQLAlchemy()`, `init_app(app)` com `create_all` e migração das colunas de soft delete.
- `models/`: `task.py`, `user.py`, `category.py` (nomes atuais mantidos) + `soft_delete.py` (mixin); regra de atraso, hash de senha e agregações nos models.
- `controllers/`: `task_controller.py`, `user_controller.py`, `category_controller.py`, `report_controller.py`, `health_controller.py`, `validators.py`.
- `routes/`: `__init__.py` (`register_blueprints`), `task_routes.py`, `user_routes.py`, `report_routes.py`, `category_routes.py` (novo), `health_routes.py` (novo, `/` e `/health` saem do `app.py`); rotas só delegam.
- `middlewares/`: `error_handler.py` (`AppError` + handlers), `auth.py` (token assinado + `require_auth`).
- `utils/`: `constants.py`, `time.py` (`utc_now`); `helpers.py` removido (todo morto).
- `services/`: removido (único serviço é código morto com credencial; não há integração externa em uso).
- `requirements.txt`: remove `marshmallow` e `requests`; `.env.example` novo; README atualizado.
Contract changes requiring approval:
- F-03: chave `password` removida das respostas de `GET /users/<id>`, `POST /users`, `PUT /users/<id>` e do `user` de `POST /login`.
- F-04: `token` do login vira token assinado (header `Authorization: Bearer <token>`); 401 sem token/token inválido e 403 sem papel/propriedade em `DELETE /users/<id>`, `POST|PUT|DELETE /categories[/<id>]` (admin), `POST /tasks` (autenticado), `PUT|DELETE /tasks/<id>` (admin, manager ou dono), `PUT /users/<id>` (próprio ou admin; `role`/`active` só admin), `GET /users/<id>` (autenticado), `POST /users` com `role` ≠ `user` (admin).
- F-06: `GET /users`, `GET /users/<id>/tasks`, `GET /reports/summary`, `GET /reports/user/<id>` exigem autenticação (401).
- F-08: exclusões viram soft delete (com cascata lógica usuário → tasks); registros removidos → 404 nas leituras por id e somem das listagens; `/reports/*` continuam contando-os (histórico).
- F-11: entradas inválidas que hoje dão 500 passam a 400 com `{'error': ...}`; 404/405 do Flask mantêm o status com corpo JSON em vez de HTML.
Soft delete (F-08, PT-09):
- Tabelas `tasks`, `users`, `categories`: colunas novas `deleted BOOLEAN NOT NULL DEFAULT 0` (flag), `deleted_at DATETIME NULL` (quando) e `deleted_by INTEGER NULL` (quem: id do usuário autenticado que chamou o `DELETE`). A coluna `users.active` não é reutilizada.
- Migração: `database.init_app` verifica as colunas com `inspect` e executa `ALTER TABLE <t> ADD COLUMN ...` só quando faltam (idempotente; bancos existentes preservam os dados).
- Cascata lógica (PT-09 regra 5, preserva o comportamento visível do original): `DELETE /users/<id>` marca o usuário e as tasks dele como removidos na mesma transação. Usuário removido some de `GET /users`, `GET /users/<id>`, `/users/<id>/tasks`, não faz login e seu token passa a ser rejeitado. Categoria removida (o original não apagava tasks) some de `GET /categories`; as tasks mantêm `category_id`/`category_name`. Task removida some de `/tasks`, `/tasks/<id>`, `/tasks/search`, `/tasks/stats`, `/users/<id>` e da contagem de `GET /categories`.
- Leituras históricas sem filtro (PT-09 regra 4): `GET /reports/summary` e `GET /reports/user/<id>` continuam contando e mostrando tasks, usuários e categorias removidos.
- O e-mail de usuário removido continua ocupado (`unique`): recadastro com o mesmo e-mail → 409.
Out of scope: nenhum.

================================
Total: 16 findings
================================
