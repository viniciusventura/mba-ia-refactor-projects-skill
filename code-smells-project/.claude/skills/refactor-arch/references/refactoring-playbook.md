# Playbook de Refatoração

Referência da **Fase 3 (Refatoração)**. Para cada anti-pattern do catálogo (AP-xx) existe um padrão de transformação (PT-xx) com código **antes → depois**. Os exemplos usam Python/Flask e Node/Express, e a ideia se aplica a qualquer stack. A estrutura de destino (onde cada arquivo mora) está em `mvc-guidelines.md`.

## Índice

| PT | Transformação | Corrige |
|---|---|---|
| [PT-01](#pt-01) | Parametrizar queries | AP-01 SQL Injection |
| [PT-02](#pt-02) | Extrair configuração para ambiente | AP-02 Credenciais hardcoded |
| [PT-03](#pt-03) | Hash de senha adequado | AP-03 Senha insegura |
| [PT-04](#pt-04) | Serializador de saída sem dados sensíveis | AP-04 Exposição de dados |
| [PT-05](#pt-05) | Proteger rotas sensíveis | AP-05 Sem autenticação |
| [PT-06](#pt-06) | Decompor God Class em camadas MVC | AP-06 God Class |
| [PT-07](#pt-07) | Extrair regra de negócio para model/controller/service | AP-07 Regra na camada errada |
| [PT-08](#pt-08) | Injeção de dependência / conexão por requisição | AP-08 Estado global |
| [PT-09](#pt-09) | Transação + async/await | AP-09 Sem transação |
| [PT-10](#pt-10) | JOIN, eager loading e agregação | AP-10 N+1 |
| [PT-11](#pt-11) | Centralizar validação e regra | AP-11 Duplicação |
| [PT-12](#pt-12) | Error handler centralizado + validação na borda | AP-12 Erro engolido |
| [PT-13](#pt-13) | Substituir API deprecated | AP-13 API deprecated |
| [PT-14](#pt-14) | Constantes, nomes, código morto e logging | AP-14 Legibilidade |

---

## Regras gerais da refatoração

1. **Preserve o contrato da API.** Mesmas URLs, métodos HTTP, status codes de sucesso e erro, e o mesmo formato de corpo (chaves como `dados`/`sucesso`/`erro` ou `error` continuam iguais). As únicas mudanças de contrato permitidas são as de segurança aprovadas na Fase 2 (ex.: remover `senha` da resposta). Liste cada uma no resumo final.
2. **Preserve as convenções do projeto:** idioma dos identificadores (português continua português), sistema de módulos (CommonJS continua CommonJS), framework de roteamento (Blueprints continuam Blueprints) e comandos de execução (`python app.py`, `npm start`). Scripts auxiliares que importam o app (ex.: `seed.py` com `from app import app, db`) devem continuar funcionando.
3. **Não adicione dependências** se a biblioteca padrão ou uma dependência já instalada resolve. Exemplos: `werkzeug.security` já vem com o Flask, `itsdangerous` também, e `crypto` é nativo do Node. Se uma nova dependência for indispensável, adicione-a ao manifesto (`requirements.txt`/`package.json`) e instale.
4. **Transforme em passos pequenos e verificáveis.** Ordem recomendada: config (PT-02) → estrutura de camadas (PT-06/PT-08) → segurança (PT-01, 03, 04, 05) → integridade e performance (PT-09, PT-10) → erros (PT-12) → duplicação, deprecated e legibilidade (PT-11, 13, 14). Após cada bloco, verifique que o app ainda importa/inicia.
5. **Dados existentes.** Mudanças de armazenamento (ex.: hash de senha) exigem que o seed gere dados no novo formato. Bancos locais de desenvolvimento (`*.db`) podem ser recriados; informe isso no resumo.

---

<a id="pt-01"></a>
## PT-01 · Parametrizar queries (corrige AP-01)

Passe os valores **separados** do SQL. O driver faz o escape, e o valor nunca vira parte da estrutura da query.

**Antes (Python / sqlite3)**
```python
cursor.execute("SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'")

query = "SELECT * FROM produtos WHERE 1=1"
if termo:
    query += " AND (nome LIKE '%" + termo + "%')"
if categoria:
    query += " AND categoria = '" + categoria + "'"
cursor.execute(query)
```

**Depois**
```python
cursor.execute("SELECT * FROM usuarios WHERE email = ?", (email,))   # senha verificada fora do SQL (PT-03)

query = "SELECT * FROM produtos WHERE 1=1"
params = []
if termo:
    query += " AND (nome LIKE ? OR descricao LIKE ?)"
    params += [f"%{termo}%", f"%{termo}%"]
if categoria:
    query += " AND categoria = ?"
    params.append(categoria)
cursor.execute(query, params)
```

**Node (sqlite3 / pg / mysql2)**
```js
// Antes
db.all(`SELECT * FROM users WHERE email = '${email}'`);
// Depois
db.all("SELECT * FROM users WHERE email = ?", [email]);     // pg usa $1, $2...
```

**Endpoint que executa SQL recebido no body:** não há parametrização possível. Remova o endpoint ou, se o contrato precisar ser mantido, aplique PT-05 e restrinja a consultas somente leitura. A decisão é do usuário na Fase 2.

---

<a id="pt-02"></a>
## PT-02 · Extrair configuração para ambiente (corrige AP-02)

Toda configuração fica num único módulo que lê variáveis de ambiente. Segredos **não** têm default real no código; defaults só para valores inofensivos de desenvolvimento.

**Antes**
```python
app.config["SECRET_KEY"] = "minha-chave-super-secreta-123"
app.config["DEBUG"] = True
```
```js
const config = { dbPass: "senha_super_secreta_prod_123", paymentGatewayKey: "pk_live_123...", port: 3000 };
```

**Depois (Python: `config/settings.py`)**
```python
import os
import secrets

class Settings:
    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)   # sem segredo fixo no código
    DEBUG = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    DATABASE_PATH = os.environ.get("DATABASE_PATH", "loja.db")
    HOST = os.environ.get("HOST", "0.0.0.0")
    PORT = int(os.environ.get("PORT", "5000"))
```

**Depois (Node: `src/config/index.js`)**
```js
module.exports = {
  port: Number(process.env.PORT) || 3000,
  db: { user: process.env.DB_USER, pass: process.env.DB_PASS },
  paymentGatewayKey: process.env.PAYMENT_GATEWAY_KEY,
};
```

**Complementos:**
- Crie `.env.example` com as chaves (sem valores reais) e garanta `.env` no `.gitignore`.
- Se `python-dotenv`/`dotenv` já for dependência, carregue o `.env` no entry point. Caso contrário, use apenas `os.environ`/`process.env`.
- Um segredo gerado aleatoriamente no boot (`secrets.token_hex`) mantém o app funcional sem configuração, mas invalida sessões a cada restart. Documente isso.

---

<a id="pt-03"></a>
## PT-03 · Hash de senha adequado (corrige AP-03)

Use um algoritmo lento e com salt (scrypt, bcrypt, argon2, pbkdf2). Nunca MD5/SHA simples, base64 ou algoritmo caseiro. Compare no código, não no SQL.

**Antes (Python)**
```python
self.password = hashlib.md5(pwd.encode()).hexdigest()
...
cursor.execute("SELECT * FROM usuarios WHERE email = '...' AND senha = '...'")
```

**Depois (Python: `werkzeug.security`, já instalado com o Flask)**
```python
from werkzeug.security import generate_password_hash, check_password_hash

def set_password(self, pwd):
    self.password = generate_password_hash(pwd)          # scrypt/pbkdf2 com salt

def check_password(self, pwd):
    return check_password_hash(self.password, pwd)

# login: busca por e-mail, verifica o hash no código
row = cursor.execute("SELECT * FROM usuarios WHERE email = ?", (email,)).fetchone()
if row is None or not check_password_hash(row["senha"], senha):
    return None
```

**Antes (Node)**
```js
function badCrypto(pwd) { /* base64 truncado */ }
let hash = badCrypto(p || "123456");
```

**Depois (Node: `crypto.scrypt`, nativo)**
```js
const crypto = require("crypto");
const { promisify } = require("util");
const scrypt = promisify(crypto.scrypt);

async function hashPassword(password) {
  const salt = crypto.randomBytes(16).toString("hex");
  const derived = await scrypt(password, salt, 64);
  return `${salt}:${derived.toString("hex")}`;
}
async function verifyPassword(password, stored) {
  const [salt, hash] = stored.split(":");
  const derived = await scrypt(password, salt, 64);
  return crypto.timingSafeEqual(Buffer.from(hash, "hex"), derived);
}
// senha obrigatória: sem default "123456" (validação → PT-12)
```

**Seeds:** gere os usuários de exemplo com a nova função, para que o login continue funcionando.

---

<a id="pt-04"></a>
## PT-04 · Serializador de saída sem dados sensíveis (corrige AP-04)

A resposta é montada por uma função/método explícito que **só inclui campos públicos**. Logs nunca recebem segredo, senha ou cartão.

**Antes**
```python
def to_dict(self):
    return {"id": self.id, "email": self.email, "password": self.password, ...}
```
```python
return jsonify({"status": "ok", "secret_key": "minha-chave...", "debug": True, "db_path": "loja.db"})
```
```js
console.log(`Processando cartão ${cc} na chave ${config.paymentGatewayKey}`);
```

**Depois**
```python
def to_dict(self):
    return {"id": self.id, "name": self.name, "email": self.email, "role": self.role,
            "active": self.active, "created_at": str(self.created_at)}      # sem password

return jsonify({"status": "ok", "database": "connected", "counts": counts})   # sem config interna
```
```js
const masked = `**** **** **** ${card.slice(-4)}`;
logger.info(`Processando pagamento do cartão ${masked}`);                     // nunca a chave
```

**Nota de contrato:** remover campo sensível da resposta é uma mudança aprovada (Fase 2). Mantenha todos os outros campos.

---

<a id="pt-05"></a>
## PT-05 · Proteger rotas sensíveis (corrige AP-05)

Autenticação/autorização como **middleware/decorator** reutilizável, aplicado na camada de rotas. Tokens assinados, nunca strings previsíveis. Privilégio nunca vem do body de um usuário não autorizado.

**Antes**
```python
@app.route("/admin/reset-db", methods=["POST"])
def reset_database(): ...

return jsonify({"token": "fake-jwt-token-" + str(user.id)})
role = data.get("role", "user")        # qualquer um cria admin
```

**Depois (Python: `middlewares/auth.py`, com `itsdangerous`, já instalado com o Flask)**
```python
from functools import wraps
from flask import current_app, request, g
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

def _serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="auth")

def issue_token(user):
    return _serializer().dumps({"id": user.id, "role": user.role})

def require_auth(role=None):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            header = request.headers.get("Authorization", "")
            token = header.removeprefix("Bearer ").strip()
            try:
                g.user = _serializer().loads(token, max_age=3600)
            except (BadSignature, SignatureExpired):
                raise UnauthorizedError("Token inválido ou ausente")        # → handler PT-12 (401)
            if role and g.user.get("role") != role:
                raise ForbiddenError("Acesso negado")                        # → 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator

# views: a rota declara a proteção
admin_bp.post("/admin/reset-db")(require_auth(role="admin")(admin_controller.reset_database))

# controller: cadastro público não escolhe privilégio
role = "user"          # role só pode ser alterada por rota protegida com require_auth(role="admin")
```

**Depois (Node: `src/middlewares/auth.js`, token de admin vindo da config/ambiente)**
```js
const crypto = require("crypto");

function safeEqual(a, b) {
  const x = Buffer.from(String(a)), y = Buffer.from(String(b));
  return x.length === y.length && crypto.timingSafeEqual(x, y);      // comparação em tempo constante
}
function requireAdmin(req, res, next) {
  const token = req.get("x-admin-token");
  if (!token || !config.adminToken || !safeEqual(token, config.adminToken)) {
    return next(new AppError("Não autorizado", 401));
  }
  next();
}
router.get("/api/admin/financial-report", requireAdmin, reportController.financial);
```

**Contrato:** proteger uma rota muda a resposta de chamadas anônimas (passam a receber 401/403). Isso é uma mudança de segurança que precisa ser listada na Fase 2 e aprovada. A validação da Fase 3 deve testar a rota **com** credencial (espera o status original) e **sem** credencial (espera 401/403).

---

<a id="pt-06"></a>
## PT-06 · Decompor God Class em camadas MVC (corrige AP-06)

Mapeie cada responsabilidade do arquivo e mova-a para a camada correspondente. O entry point vira um **composition root** que só monta as peças.

**Antes (Node: `AppManager.js`, 140 linhas)**
```js
class AppManager {
  constructor() { this.db = new sqlite3.Database(':memory:'); }
  initDb() { /* CREATE TABLE ... INSERT seed ... */ }
  setupRoutes(app) {
    app.post('/api/checkout', (req, res) => { /* validação + SQL + pagamento + auditoria */ });
    app.get('/api/admin/financial-report', (req, res) => { /* SQL em loop + cálculo */ });
    app.delete('/api/users/:id', (req, res) => { /* SQL */ });
  }
}
```

**Depois**
```
src/
├── app.js                         # composition root: cria express, injeta dependências, registra rotas e erro
├── config/index.js                # PT-02
├── database/connection.js         # abre conexão, helpers promisificados (PT-09)
├── database/schema.js             # CREATE TABLE + seed
├── models/courseModel.js          # SQL de courses
├── models/userModel.js            # SQL de users
├── models/enrollmentModel.js      # SQL de enrollments/payments
├── services/paymentService.js     # "gateway" de pagamento
├── controllers/checkoutController.js
├── controllers/reportController.js
├── controllers/userController.js
├── routes/index.js                # views: URL → controller
└── middlewares/errorHandler.js    # PT-12
```
```js
// src/app.js (composition root)
const express = require("express");
const config = require("./config");
const { createConnection } = require("./database/connection");
const { initSchema } = require("./database/schema");
const buildRoutes = require("./routes");
const errorHandler = require("./middlewares/errorHandler");

async function main() {
  const db = await createConnection();
  await initSchema(db);
  const app = express();
  app.use(express.json());
  app.use(buildRoutes({ db }));        // dependências injetadas (PT-08)
  app.use(errorHandler);
  app.listen(config.port, () => console.log(`LMS API rodando na porta ${config.port}`));
}
main();
```
```js
// src/routes/index.js (view = roteamento)
const { Router } = require("express");
module.exports = ({ db }) => {
  const checkout = require("../controllers/checkoutController")({ db });
  const router = Router();
  router.post("/api/checkout", checkout.create);
  return router;
};
```

**Python (monolito `app.py` + `controllers.py` + `models.py`)**: o mesmo mapa. `models.py` é dividido por domínio (`models/produto_model.py`, `models/usuario_model.py`, `models/pedido_model.py`), as rotas vão para `views/*_routes.py` com Blueprints, e o `app.py` passa a ter só o `create_app()`.

---

<a id="pt-07"></a>
## PT-07 · Extrair regra de negócio para model/controller/service (corrige AP-07)

- **Regra de domínio** (cálculo, decisão que vale independente de HTTP) → método no **model** ou função de domínio.
- **Fluxo do caso de uso** (validar entrada → chamar models → disparar efeitos → montar resultado) → **controller**.
- **Integração externa** (e-mail, SMS, pagamento) → **service**, chamado pelo controller.
- **Rota** só liga URL ao controller.

**Antes (regra dentro do acesso a dados)**
```python
def relatorio_vendas():
    ...
    faturamento = cursor.fetchone()[0] or 0
    desconto = 0
    if faturamento > 10000: desconto = faturamento * 0.1
    elif faturamento > 5000: desconto = faturamento * 0.05
```

**Depois**
```python
# models/pedido_model.py: só dados
def totais_por_status(db): ...

# models/regras_desconto.py (ou método de domínio)
FAIXAS_DESCONTO = [(10000, 0.10), (5000, 0.05), (1000, 0.02)]

def calcular_desconto(faturamento):
    for limite, taxa in FAIXAS_DESCONTO:
        if faturamento > limite:
            return faturamento * taxa
    return 0

# controllers/relatorio_controller.py: orquestra
def relatorio_vendas():
    totais = pedido_model.totais_por_status(get_db())
    desconto = calcular_desconto(totais["faturamento"])
    return {...}
```

**Antes (efeito colateral no handler)**
```python
print("ENVIANDO EMAIL: Pedido ...")
print("ENVIANDO SMS: ...")
```
**Depois**
```python
# services/notificacao_service.py
def notificar_pedido_criado(pedido_id, usuario_id):
    logger.info("Notificação de pedido %s para usuário %s", pedido_id, usuario_id)

# controller
resultado = pedido_model.criar(db, usuario_id, itens)
notificacao_service.notificar_pedido_criado(resultado["pedido_id"], usuario_id)
```

**Rota gorda (projeto já em camadas):** o corpo do blueprint vai para `controllers/<dominio>_controller.py`, e o blueprint fica com uma linha por rota. Se existir `services/` não utilizado, conecte-o ao controller ou remova-o (PT-14).

---

<a id="pt-08"></a>
## PT-08 · Injeção de dependência / conexão por requisição (corrige AP-08)

Dependências são criadas no composition root e passadas adiante. Recursos por requisição (conexão SQLite) vivem no contexto da requisição, não numa global.

**Antes (Python)**
```python
db_connection = None
def get_db():
    global db_connection
    if db_connection is None:
        db_connection = sqlite3.connect(db_path, check_same_thread=False)
    return db_connection
```

**Depois (Python: conexão por requisição com `flask.g`)**
```python
import sqlite3
from flask import g, current_app

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE_PATH"])
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_app(app):
    app.teardown_appcontext(close_db)
    with app.app_context():
        init_schema(get_db())            # CREATE TABLE IF NOT EXISTS + seed
```

**Antes (Node)**
```js
let globalCache = {};
function logAndCache(key, data) { globalCache[key] = data; }
module.exports = { globalCache, totalRevenue };
```

**Depois (Node: dependência injetada, estado encapsulado)**
```js
// cache com dono e escopo definidos, criado no composition root
function createCache() {
  const store = new Map();
  return { set: (k, v) => store.set(k, v), get: (k) => store.get(k) };
}
module.exports = ({ db, cache }) => ({
  async create(req, res) { /* usa db e cache recebidos, sem import global */ },
});
```
Remova globais exportadas que nunca são atualizadas (ex.: `totalRevenue`).

---

<a id="pt-09"></a>
## PT-09 · Transação + async/await (corrige AP-09)

Operações com várias escritas rodam dentro de uma transação: ou tudo grava, ou nada grava. Em Node, troque o callback hell por `async/await` sobre helpers promisificados.

**Antes (Node: 6 níveis de callback, sem transação)**
```js
db.get("SELECT * FROM courses ...", [cid], (err, course) => {
  db.get("SELECT id FROM users ...", [e], (err, user) => {
    db.run("INSERT INTO enrollments ...", [userId, cid], function (err) {
      self.db.run("INSERT INTO payments ...", [this.lastID, ...], function (err) {
        self.db.run("INSERT INTO audit_logs ...", ...
```

**Depois (Node: `database/connection.js` + controller)**
```js
// helpers promisificados
function wrap(db) {
  return {
    get: (sql, p = []) => new Promise((ok, ko) => db.get(sql, p, (e, r) => (e ? ko(e) : ok(r)))),
    all: (sql, p = []) => new Promise((ok, ko) => db.all(sql, p, (e, r) => (e ? ko(e) : ok(r)))),
    run: (sql, p = []) => new Promise((ok, ko) => db.run(sql, p, function (e) { e ? ko(e) : ok({ lastID: this.lastID, changes: this.changes }); })),
    async transaction(fn) {
      await this.run("BEGIN");
      try { const r = await fn(this); await this.run("COMMIT"); return r; }
      catch (e) { await this.run("ROLLBACK"); throw e; }
    },
  };
}

// controller: fluxo linear e atômico
const enrollmentId = await db.transaction(async (tx) => {
  const { lastID } = await tx.run("INSERT INTO enrollments (user_id, course_id) VALUES (?, ?)", [userId, courseId]);
  await tx.run("INSERT INTO payments (enrollment_id, amount, status) VALUES (?, ?, ?)", [lastID, course.price, "PAID"]);
  await tx.run("INSERT INTO audit_logs (action, created_at) VALUES (?, datetime('now'))", [`Checkout curso ${courseId} por ${userId}`]);
  return lastID;
});
```

**Depois (Python: sqlite3)**
```python
with db:                                   # commit se ok, rollback em exceção
    cur = db.execute("INSERT INTO pedidos (usuario_id, status, total) VALUES (?, 'pendente', ?)", (usuario_id, total))
    pedido_id = cur.lastrowid
    db.executemany("INSERT INTO itens_pedido (...) VALUES (?, ?, ?, ?)", linhas)
    db.executemany("UPDATE produtos SET estoque = estoque - ? WHERE id = ?", baixas)
```
Com SQLAlchemy: um único `db.session.commit()` no fim do caso de uso, e `rollback()` no handler de erro.

**Exclusão com dependentes:** remova os dependentes na mesma transação (ou use `ON DELETE CASCADE`).
```js
await db.transaction(async (tx) => {
  await tx.run("DELETE FROM payments WHERE enrollment_id IN (SELECT id FROM enrollments WHERE user_id = ?)", [id]);
  await tx.run("DELETE FROM enrollments WHERE user_id = ?", [id]);
  await tx.run("DELETE FROM users WHERE id = ?", [id]);
});
```

---

<a id="pt-10"></a>
## PT-10 · JOIN, eager loading e agregação (corrige AP-10)

Traga os dados relacionados numa única ida ao banco e agrupe no código. Contagens por categoria usam `GROUP BY`.

**Antes (Python: SQL cru, 1 + N + N×M queries)**
```python
for row in pedidos:
    itens = db.execute("SELECT * FROM itens_pedido WHERE pedido_id = ?", (row["id"],)).fetchall()
    for item in itens:
        prod = db.execute("SELECT nome FROM produtos WHERE id = ?", (item["produto_id"],)).fetchone()
```

**Depois (1 query + agrupamento)**
```python
rows = db.execute("""
    SELECT p.id, p.usuario_id, p.status, p.total, p.criado_em,
           i.produto_id, i.quantidade, i.preco_unitario, pr.nome AS produto_nome
    FROM pedidos p
    LEFT JOIN itens_pedido i ON i.pedido_id = p.id
    LEFT JOIN produtos pr    ON pr.id = i.produto_id
    WHERE p.usuario_id = ?
    ORDER BY p.id
""", (usuario_id,)).fetchall()

pedidos = {}
for r in rows:
    pedido = pedidos.setdefault(r["id"], {"id": r["id"], "usuario_id": r["usuario_id"], "status": r["status"],
                                          "total": r["total"], "criado_em": r["criado_em"], "itens": []})
    if r["produto_id"] is not None:
        pedido["itens"].append({"produto_id": r["produto_id"], "produto_nome": r["produto_nome"] or "Desconhecido",
                                "quantidade": r["quantidade"], "preco_unitario": r["preco_unitario"]})
return list(pedidos.values())
```

**Depois (SQLAlchemy: eager loading e agregação)**
```python
from sqlalchemy.orm import joinedload
from sqlalchemy import func

tasks = Task.query.options(joinedload(Task.user), joinedload(Task.category)).all()   # 1 query
# t.user.name e t.category.name não disparam novas queries

por_status = dict(db.session.query(Task.status, func.count(Task.id)).group_by(Task.status).all())
pending = por_status.get("pending", 0)                     # 1 query no lugar de 4 counts
```

**Depois (Node: relatório com JOIN)**
```js
const rows = await db.all(`
  SELECT c.id AS course_id, c.title, u.name AS student, p.amount, p.status
  FROM courses c
  LEFT JOIN enrollments e ON e.course_id = c.id
  LEFT JOIN users u       ON u.id = e.user_id
  LEFT JOIN payments p    ON p.enrollment_id = e.id
  ORDER BY c.id`);
// agrupa por curso em memória, mantendo o formato de resposta original
```

**Preserve a forma da resposta:** mesma ordem, mesmos campos, mesmos defaults (ex.: `"Unknown"`/`"Desconhecido"` quando o relacionamento não existe).

---

<a id="pt-11"></a>
## PT-11 · Centralizar validação e regra (corrige AP-11)

Uma regra = um lugar. Constantes de domínio num módulo, validação num validador reutilizado por create/update, regra de domínio num método do model, serialização num único `to_dict`.

**Antes**
```python
# task_routes.py (3x), report_routes.py (2x), user_routes.py (1x)
if t.due_date and t.due_date < datetime.utcnow() and t.status != 'done' and t.status != 'cancelled': ...
if status not in ['pending', 'in_progress', 'done', 'cancelled']: ...
```

**Depois**
```python
# models/task.py
from utils.constants import TASK_STATUSES, CLOSED_STATUSES

class Task(db.Model):
    def is_overdue(self, now=None):
        now = now or utc_now()
        return bool(self.due_date and self.due_date < now and self.status not in CLOSED_STATUSES)

    def to_dict(self):
        return {..., "overdue": self.is_overdue()}

# controllers/task_controller.py: um validador para create e update
def validar_task(data, parcial=False):
    if not parcial or "title" in data:
        title = (data.get("title") or "").strip()
        if not MIN_TITLE <= len(title) <= MAX_TITLE:
            raise ValidationError(f"Título deve ter entre {MIN_TITLE} e {MAX_TITLE} caracteres")
    if "status" in data and data["status"] not in TASK_STATUSES:
        raise ValidationError("Status inválido")
    ...
```

**Mensagens de erro:** se o original tinha mensagens diferentes para o mesmo erro em endpoints diferentes, mantenha a mensagem de cada endpoint (contrato) ou unifique-as e liste a mudança no resumo.

---

<a id="pt-12"></a>
## PT-12 · Error handler centralizado + validação na borda (corrige AP-12)

Controllers **levantam** erros de domínio tipados. Um único handler converte erro → resposta HTTP no formato do projeto. Erros inesperados viram 500 genérico **sem** detalhes internos, e o detalhe vai para o log.

**Antes**
```python
def listar_produtos():
    try:
        ...
    except Exception as e:
        return jsonify({"erro": str(e)}), 500       # repetido em 16 funções, vazando detalhes
```
```js
db.all(sql, [id], (err, rows) => { let n = rows.length; });   // err ignorado → crash
```

**Depois (Python: `middlewares/error_handler.py`)**
```python
import logging
from flask import jsonify
from werkzeug.exceptions import HTTPException

logger = logging.getLogger(__name__)

class AppError(Exception):
    status_code = 400
    def __init__(self, message): super().__init__(message); self.message = message

class ValidationError(AppError): status_code = 400
class UnauthorizedError(AppError): status_code = 401
class ForbiddenError(AppError): status_code = 403
class NotFoundError(AppError): status_code = 404
class ConflictError(AppError): status_code = 409

def register_error_handlers(app, error_key="erro", extra=None):
    """error_key/extra preservam o formato de erro original do projeto (ex.: {"erro": ..., "sucesso": False})."""
    extra = extra or {}

    @app.errorhandler(AppError)
    def handle_app_error(err):
        return jsonify({error_key: err.message, **extra}), err.status_code

    @app.errorhandler(HTTPException)            # 404, 405, 400 do próprio Flask mantêm o status
    def handle_http_error(err):
        return jsonify({error_key: err.description, **extra}), err.code

    @app.errorhandler(Exception)
    def handle_unexpected(err):
        logger.exception("Erro inesperado")
        return jsonify({error_key: "Erro interno do servidor", **extra}), 500

# controller: sem try/except de ruído
def buscar_produto(id):
    produto = produto_model.buscar_por_id(get_db(), id)
    if produto is None:
        raise NotFoundError("Produto não encontrado")
    return jsonify({"dados": produto, "sucesso": True}), 200
```
Com SQLAlchemy, o handler de `Exception` também faz `db.session.rollback()`.

**Armadilha (Flask):** um `@app.errorhandler(Exception)` sozinho também captura as `HTTPException` do framework. Um `POST` numa rota só-`GET` passaria a responder **500 em vez de 405**, mudando o contrato. Sempre registre o handler de `HTTPException` (como acima) junto com o genérico.

**Depois (Node: `src/middlewares/errorHandler.js`)**
```js
class AppError extends Error { constructor(message, status = 400) { super(message); this.status = status; } }

function errorHandler(err, req, res, next) {
  if (err instanceof AppError) return res.status(err.status).send(err.message);   // mantém texto puro se o original era texto
  const status = err.status || err.statusCode;                                     // erros do próprio Express (ex.: JSON malformado = 400)
  if (status && status < 500) return res.status(status).send(err.message);
  console.error(err);
  res.status(500).send("Erro interno");
}
// Express 4 não captura rejeições de async: envolva os handlers
const asyncHandler = (fn) => (req, res, next) => Promise.resolve(fn(req, res, next)).catch(next);
router.post("/api/checkout", asyncHandler(checkout.create));
```

**Validação na borda:** converta e valide tipos antes de usar.
```python
priority = request.args.get("priority")
if priority:
    try:
        priority = int(priority)
    except ValueError:
        raise ValidationError("Prioridade inválida")
```

---

<a id="pt-13"></a>
## PT-13 · Substituir API deprecated (corrige AP-13)

Troque pela alternativa indicada na tabela do catálogo (AP-13). Atenção aos efeitos colaterais de tipo.

**Antes**
```python
user = User.query.get(user_id)
if t.due_date < datetime.utcnow(): ...
created_at = db.Column(db.DateTime, default=datetime.utcnow)
```

**Depois**
```python
user = db.session.get(User, user_id)

# utils/time.py: helper único, compatível com colunas DateTime "naive" do SQLite
from datetime import datetime, timezone

def utc_now():
    """UTC atual sem tzinfo, para comparar com datetimes naive gravados no banco."""
    return datetime.now(timezone.utc).replace(tzinfo=None)

if t.due_date < utc_now(): ...
created_at = db.Column(db.DateTime, default=utc_now)
```

**Cuidado:** `datetime.now(timezone.utc)` é *aware*, e SQLite/SQLAlchemy devolvem datetimes *naive*. Compará-los gera `TypeError: can't compare offset-naive and offset-aware datetimes`. Use o helper acima (ou torne todas as colunas `DateTime(timezone=True)`) de forma consistente.

**Node**
```js
new Buffer(str)          →  Buffer.from(str)
url.parse(req.url)       →  new URL(req.url, `http://${req.headers.host}`)
app.use(bodyParser.json()) → app.use(express.json())
```

**Verificação:** após a troca, execute com warnings visíveis (`python -W default`, `node --trace-deprecation`). Não pode sobrar warning vindo do código do projeto.

---

<a id="pt-14"></a>
## PT-14 · Constantes, nomes, código morto e logging (corrige AP-14)

**Magic numbers → constantes nomeadas**
```python
# Antes
if faturamento > 10000: desconto = faturamento * 0.1
categorias_validas = ["informatica", "moveis", ...]      # inline no controller
# Depois (utils/constants.py ou config de domínio)
CATEGORIAS_VALIDAS = ("informatica", "moveis", "vestuario", "geral", "eletronicos", "livros")
STATUS_PEDIDO = ("pendente", "aprovado", "enviado", "entregue", "cancelado")
```
```js
// Antes
let status = cc.startsWith("4") ? "PAID" : "DENIED";
// Depois (services/paymentService.js)
const APPROVED_CARD_PREFIX = "4";           // regra do gateway simulado
function charge(cardNumber) { return cardNumber.startsWith(APPROVED_CARD_PREFIX) ? "PAID" : "DENIED"; }
```

**Nomes claros (sem mudar o contrato)**
```js
// Antes
let u = req.body.usr; let e = req.body.eml; let cc = req.body.card;
// Depois: o contrato (usr/eml/pwd) continua; só as variáveis internas ganham nome
const { usr: name, eml: email, pwd: password, c_id: courseId, card: cardNumber } = req.body;
```

**Código morto:** remova funções, classes, constantes e imports sem uso, ou conecte-os se eram a intenção original (ex.: usar `Task.is_overdue()` em vez da lógica duplicada). Antes de remover, confirme com uma busca no projeto inteiro.

**Logging**
```python
# Antes
print("Produto criado com ID: " + str(id))
app.run(debug=True)
# Depois
import logging
logger = logging.getLogger(__name__)
logger.info("Produto criado com ID %s", produto_id)
app.run(host=settings.HOST, port=settings.PORT, debug=settings.DEBUG)   # debug vem do ambiente
```
Configure `logging.basicConfig(level=...)` uma única vez no entry point.

**Verbosidade**
```python
# Antes
if self.role == 'admin':
    return True
else:
    return False
if type(tags) == list: ...
# Depois
return self.role == 'admin'
if isinstance(tags, list): ...
```
