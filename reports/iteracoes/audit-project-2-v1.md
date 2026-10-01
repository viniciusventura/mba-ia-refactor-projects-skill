================================
ARCHITECTURE AUDIT REPORT
================================
Project:  ecommerce-api-legacy
Stack:    JavaScript (Node.js v22.17.0) + Express ^4.18.2 (instalado 4.22.1) + sqlite3 ^5.1.6 (instalado 5.1.7)
Files:    3 analyzed | ~180 lines of code
Date:     2026-10-01
Architecture: A) Monolítica / God Class: 3 arquivos; `src/AppManager.js` concentra conexão, DDL, seed, rotas, regra de pagamento e relatório; `src/utils.js` mistura config com segredos, cache global e "hash" de senha.

## Summary
CRITICAL: 5 | HIGH: 3 | MEDIUM: 3 | LOW: 4

| ID | Severity | Anti-pattern | Location |
|----|----------|--------------|----------|
| F-01 | CRITICAL | Credenciais hardcoded (AP-02) | src/utils.js:2-6 |
| F-02 | CRITICAL | Armazenamento inseguro de senha (AP-03) | src/utils.js:17-23, src/AppManager.js:18, 68-69 |
| F-03 | CRITICAL | Exposição de dados sensíveis (AP-04) | src/AppManager.js:45 |
| F-04 | CRITICAL | Endpoint sensível sem autenticação (AP-05) | src/AppManager.js:80-129, 131-137 |
| F-05 | CRITICAL | God Class / God File (AP-06) | src/AppManager.js:4-139 |
| F-06 | HIGH | Regra de negócio na camada errada (AP-07) | src/AppManager.js:35, 45-48, 66-72, 108-115 |
| F-07 | HIGH | Estado global mutável / acoplamento sem DI (AP-08) | src/utils.js:9-15, 25; src/AppManager.js:7, 59 |
| F-08 | HIGH | Operação multi-etapa sem transação (AP-09) | src/AppManager.js:50-61, 66-72, 133 |
| F-09 | MEDIUM | Query N+1 (AP-10) | src/AppManager.js:89-106 |
| F-10 | MEDIUM | Código duplicado (AP-11) | src/AppManager.js:96-98, 119-121 |
| F-11 | MEDIUM | Erro engolido / sem handler central / validação ausente (AP-12) | src/AppManager.js:35, 38, 57, 68, 92-93, 104, 106, 133; src/app.js:5-10 |
| F-12 | LOW | Magic numbers/strings (AP-14) | src/AppManager.js:21, 46, 48, 68, 108; src/utils.js:19, 20, 22 |
| F-13 | LOW | Nomes ruins (AP-14) | src/AppManager.js:26, 29-33 |
| F-14 | LOW | Código morto (AP-14) | src/utils.js:2, 3, 5, 9-10, 14, 25; src/AppManager.js:2 |
| F-15 | LOW | Logging inadequado (AP-14) | src/app.js:13; src/utils.js:13 |

## Findings

### F-01 [CRITICAL] Credenciais hardcoded (AP-02)
File: src/utils.js:2-6
Principle: OWASP A07 / 12-Factor App (Config)
Description: 4 valores de configuração sensíveis escritos como literal, sem leitura de ambiente: `dbUser` (2), `dbPass` (3), `paymentGatewayKey` com prefixo de produção `pk_live_` (4) e `smtpUser` (5). A porta (6) também é fixa. `dbUser`, `dbPass` e `smtpUser` são código morto (F-14), mas `paymentGatewayKey` é usada e ainda vaza em log (F-03), por isso a severidade se mantém.
Evidence:
```js
dbPass: "senha_super_secreta_prod_123",
paymentGatewayKey: "pk_live_1234567890abcdef",
```
Impact: qualquer pessoa com acesso ao repositório obtém a chave do gateway de pagamento e a senha de banco; rotação exige novo deploy.
Recommendation: `src/config/index.js` lendo `process.env` (`PORT`, `PAYMENT_GATEWAY_KEY`, `ADMIN_TOKEN`); remover os segredos não usados; `.env.example` sem valores reais (PT-02).
Contract change: NO

### F-02 [CRITICAL] Armazenamento inseguro de senha (AP-03)
File: src/utils.js:17-23, src/AppManager.js:18, 68-69
Principle: OWASP A02 Cryptographic Failures
Description: `badCrypto` é um "hash" caseiro: repete os 2 primeiros caracteres do base64 da senha 10.000 vezes e trunca em 10. O resultado depende só dos ~12 primeiros bits da senha, então colide massivamente. Além disso, a senha é opcional e ganha o default `"123456"` (68), e o seed grava a senha `'123'` em texto puro (18). Não há `bcrypt`/`scrypt`/`argon2`/`pbkdf2` no projeto.
Evidence:
```js
hash += Buffer.from(pwd).toString('base64').substring(0, 2);   // utils.js:20
let hash = badCrypto(p || "123456");                            // AppManager.js:68
```
Executado isoladamente (`node -e`, só a função): `senhaforte` → `c2c2c2c2c2`, `segredo` → `c2c2c2c2c2`; `123`, `123456` e `19` → `MTMTMTMTMT`.
Impact: senhas triviais de reverter/colidir; um vazamento do banco expõe todas as contas; usuários criados sem senha ficam com uma senha conhecida.
Recommendation: `crypto.scrypt` com salt aleatório (nativo do Node, sem dependência nova) em `src/utils/password.js`; seed com senha já hasheada; não aplicar default de senha (PT-03).
Contract change: NO (não existe endpoint de login; o formato gravado muda apenas internamente)

### F-03 [CRITICAL] Exposição de dados sensíveis (AP-04)
File: src/AppManager.js:45
Principle: OWASP A01/A09
Description: 1 log que grava o número completo do cartão (PAN) e a chave do gateway de pagamento em texto puro a cada checkout.
Evidence:
```js
console.log(`Processando cartão ${cc} na chave ${config.paymentGatewayKey}`);
```
Impact: cartões e chave de produção em logs (violação de PCI-DSS); qualquer pessoa com acesso aos logs pode reutilizá-los.
Recommendation: remover o log ou registrar apenas o cartão mascarado (`**** 4444`) e nunca a chave (PT-04, PT-02).
Contract change: NO

### F-04 [CRITICAL] Endpoint sensível sem autenticação (AP-05)
File: src/AppManager.js:80-129, 131-137
Principle: OWASP A01 Broken Access Control
Description: 2 rotas sensíveis sem nenhum controle de acesso, e o projeto não tem nenhum mecanismo de autenticação (busca por `auth|jwt|session|token` sem resultado): `GET /api/admin/financial-report` expõe receita e nomes de alunos; `DELETE /api/users/:id` apaga qualquer usuário.
Evidence:
```js
app.get('/api/admin/financial-report', (req, res) => {
app.delete('/api/users/:id', (req, res) => {
```
Impact: qualquer cliente anônimo lê os dados financeiros e apaga usuários.
Recommendation: middleware `src/middlewares/auth.js` (`requireAdmin`) que exige `Authorization: Bearer <ADMIN_TOKEN>`, com o token lido do ambiente e comparação em tempo constante; sem `ADMIN_TOKEN` configurado, a rota nega acesso (fail-closed) (PT-05).
Contract change: YES: as duas rotas passam a exigir o header `Authorization: Bearer <ADMIN_TOKEN>`; sem credencial ou com credencial inválida → 401.

### F-05 [CRITICAL] God Class / God File (AP-06)
File: src/AppManager.js:4-139
Principle: SRP (SOLID) + MVC
Description: a classe `AppManager` acumula 7 responsabilidades de camadas diferentes e 4 domínios (usuários, cursos, matrículas/pagamentos, relatório): conexão (7), DDL (12-16), seed (18-21), roteamento HTTP (28, 80, 131), validação de entrada (35), acesso a dados (37, 40, 50, 54, 57, 69, 83, 92, 104, 106, 133), regra de negócio/integração de pagamento (45-48) e agregação do relatório (108-115).
Evidence:
```js
class AppManager {
    constructor() { this.db = new sqlite3.Database(':memory:'); }
    initDb() { ... CREATE TABLE ... INSERT ... }
    setupRoutes(app) { app.post('/api/checkout', ...) app.get(...) app.delete(...) }
```
Impact: qualquer mudança (trocar o gateway, mudar o relatório) mexe no mesmo arquivo; impossível testar regra de pagamento sem HTTP e banco.
Recommendation: decompor na estrutura Express da §4 (config, database, models, controllers, routes, services, middlewares) e remover `AppManager.js` (PT-06).
Contract change: NO

### F-06 [HIGH] Regra de negócio na camada errada (AP-07)
File: src/AppManager.js:35, 45-48, 66-72, 108-115
Principle: SRP (SOLID) + MVC
Description: 4 regras de domínio dentro dos handlers HTTP, misturadas com SQL: aprovação do pagamento pelo prefixo do cartão (46) junto da "integração" com o gateway (45); criação implícita do usuário no checkout com senha default (66-72); cálculo da receita só com pagamentos `PAID` (108-110); montagem do aluno no relatório (112-115). A validação do body (35) está no mesmo corpo que 6 acessos ao banco (37, 40, 50, 54, 57, 69).
Evidence:
```js
let status = cc.startsWith("4") ? "PAID" : "DENIED";
if (payment && payment.status === 'PAID') { courseData.revenue += payment.amount; }
```
Impact: a regra de pagamento não pode ser reutilizada (ex.: fila, CLI) nem testada isoladamente; trocar o gateway exige mexer na rota.
Recommendation: `services/paymentService.js` para a decisão de pagamento; regra de receita no model; controllers só orquestram (PT-07).
Contract change: NO

### F-07 [HIGH] Estado global mutável / acoplamento sem DI (AP-08)
File: src/utils.js:9-15, 25; src/AppManager.js:7, 59
Principle: DIP (SOLID)
Description: `globalCache` é um objeto de módulo, exportado, sem limite de tamanho, mutado a cada checkout via `logAndCache` (14, chamado em AppManager.js:59); `totalRevenue` é um `let` de módulo exportado (10, 25). A conexão com o banco é criada dentro do construtor (`new sqlite3.Database(':memory:')`, AppManager.js:7), sem injeção.
Evidence:
```js
let globalCache = {};
function logAndCache(key, data) { globalCache[key] = data; }
```
Impact: crescimento de memória ilimitado (uma chave por usuário que compra); estado compartilhado entre requisições; impossível trocar o banco (ex.: em testes) sem editar a classe.
Recommendation: remover o cache (é escrito e nunca lido, ver F-14); abrir a conexão em `database/connection.js` e injetá-la nos models/controllers pelo composition root `app.js` (PT-08).
Contract change: NO

### F-08 [HIGH] Operação multi-etapa sem transação (AP-09)
File: src/AppManager.js:50-61, 66-72, 133
Principle: Integridade (ACID)
Description: 3 fluxos sem atomicidade:
1. Checkout grava em até 4 tabelas (`users` 69, `enrollments` 50, `payments` 54, `audit_logs` 57) em callbacks aninhados, sem `BEGIN/COMMIT/ROLLBACK`. Se o `INSERT` de pagamento falhar, a matrícula já existe.
2. O usuário é criado (69) **antes** da decisão de pagamento (46-48): um checkout recusado deixa um usuário gravado.
3. `DELETE FROM users` (133) não remove `enrollments` e `payments` dependentes; a própria resposta admite isso.
Evidence:
```js
this.db.run("INSERT INTO enrollments ...", [userId, cid], function(err) {
    self.db.run("INSERT INTO payments ...", [enrId, course.price, status], function(err) {
res.send("Usuário deletado, mas as matrículas e pagamentos ficaram sujos no banco.");
```
Impact: matrículas sem pagamento, usuários fantasmas e registros órfãos que distorcem o relatório financeiro.
Recommendation: helper `transaction()` com `BEGIN/COMMIT/ROLLBACK` e helpers promisificados em `database/connection.js`; checkout decide o pagamento antes de qualquer escrita e grava tudo numa transação; exclusão de usuário remove pagamentos e matrículas na mesma transação (PT-09).
Contract change: YES: `DELETE /api/users/:id` passa a responder `Usuário deletado` (o texto atual anuncia dados órfãos, que deixam de existir) e 404 `Usuário não encontrado` para id inexistente (hoje responde 200 mesmo sem apagar nada).

### F-09 [MEDIUM] Query N+1 (AP-10)
File: src/AppManager.js:89-106
Principle: Performance
Description: o relatório executa 1 query de cursos, +1 query de matrículas **por curso** (92, dentro do `forEach` de 89) e +2 queries **por matrícula** (users 104 e payments 106, dentro do `forEach` de 102): 1 + C + 2E queries. Com o seed (2 cursos, 1 matrícula): 5 queries; cresce linearmente com as vendas.
Evidence:
```js
courses.forEach(c => { this.db.all("SELECT * FROM enrollments WHERE course_id = ?", ...
    enrollments.forEach(enr => { this.db.get("SELECT name, email FROM users WHERE id = ?", ...
```
Impact: latência proporcional ao número de matrículas; a ordem de alunos/cursos depende da ordem de término dos callbacks (não determinística).
Recommendation: uma única query `courses LEFT JOIN enrollments LEFT JOIN users LEFT JOIN payments ORDER BY` e agregação em memória (PT-10).
Contract change: NO (mesmas chaves `course`, `revenue`, `students[{student, paid}]`; a ordem passa a ser determinística por id)

### F-10 [MEDIUM] Código duplicado (AP-11)
File: src/AppManager.js:96-98, 119-121
Principle: DRY
Description: 2 cópias do mesmo bloco de "fechamento" do relatório com contadores manuais, consequência do callback hell.
Evidence:
```js
report.push(courseData);
coursesPending--;
if (coursesPending === 0) res.json(report);
```
Impact: qualquer ajuste na finalização precisa ser repetido; risco de resposta dupla ou de nunca responder.
Recommendation: eliminado pela query única com agregação (PT-10/PT-11).
Contract change: NO

### F-11 [MEDIUM] Erro engolido / sem handler central / validação ausente (AP-12)
File: src/AppManager.js:35, 38, 57, 68, 92-93, 104, 106, 133; src/app.js:5-10
Principle: Robustez / Fail-fast
Description:
- 5 callbacks em que `err` nunca é testado: 57, 92, 104, 106, 133. Em 92-93, se a query falhar, `enrollments.length` lança `TypeError` dentro de um callback assíncrono, o que derruba o processo inteiro. Em 133, o DELETE responde sucesso mesmo com erro.
- 38: erro de banco é respondido como 404 "Curso não encontrado".
- Não há middleware de erro `(err, req, res, next)` em `app.js`.
- Validação: `pwd` é opcional (35 não o exige; 68 aplica default), `c_id` e `:id` não são validados como inteiros, `eml` sem formato, `card` não é checado como string (`cc.startsWith` em 46 lança `TypeError` → 500 se `card` for número).
Evidence:
```js
this.db.all("SELECT * FROM enrollments WHERE course_id = ?", [c.id], (err, enrollments) => {
    let enrPending = enrollments.length;
```
Impact: uma falha de banco derruba a API; erros silenciosos escondem perda de dados.
Recommendation: `middlewares/errorHandler.js` + `asyncHandler`; `AppError` com status; validação na borda do controller preservando as mensagens atuais (`Bad Request`, `Curso não encontrado`...) (PT-12).
Contract change: NO para as respostas atuais (mesmos status e textos). Entradas hoje não tratadas (ex.: `card` numérico) passam a receber 400 `Bad Request` em vez de 500.

### F-12 [LOW] Magic numbers/strings (AP-14)
File: src/AppManager.js:21, 46, 48, 68, 108; src/utils.js:19, 20, 22
Principle: Clean Code
Description: 8 literais de domínio sem nome: prefixo `"4"` de aprovação (46), status `'PAID'`/`'DENIED'` repetidos (21, 46, 48, 108), senha default `"123456"` (68), `10000`, `2` e `10` do hash caseiro (utils 19, 20, 22).
Evidence:
```js
let status = cc.startsWith("4") ? "PAID" : "DENIED";
```
Impact: regra de aprovação e status espalhados; erro de digitação em um status quebra o relatório silenciosamente.
Recommendation: `utils/constants.js` com `PAYMENT_STATUS` e prefixo aprovado no `paymentService` (PT-14).
Contract change: NO

### F-13 [LOW] Nomes ruins (AP-14)
File: src/AppManager.js:26, 29-33
Principle: Clean Code
Description: variáveis de 1-3 letras para dados de negócio (`u`, `e`, `p`, `cid`, `cc`, 29-33) e `self = this` (26) misturado com `this`. Os campos do contrato (`usr`, `eml`, `pwd`, `c_id`, `card`) também são abreviados, mas fazem parte da API e serão **mantidos**; só os nomes internos mudam.
Evidence:
```js
let u = req.body.usr; let e = req.body.eml; let p = req.body.pwd; let cid = req.body.c_id; let cc = req.body.card;
```
Impact: leitura difícil; `e` e `p` colidem com convenções (evento, promise).
Recommendation: mapear o body para `{ name, email, password, courseId, cardNumber }` no controller (PT-14).
Contract change: NO

### F-14 [LOW] Código morto (AP-14)
File: src/utils.js:2, 3, 5, 9-10, 14, 25; src/AppManager.js:2
Principle: Clean Code
Description: 5 símbolos sem uso: `config.dbUser` (2), `config.dbPass` (3), `config.smtpUser` (5) nunca lidos; `totalRevenue` (10) exportado e importado em AppManager.js:2 sem uso; `globalCache` (9) exportado e nunca lido fora de `logAndCache` (é só escrito em 14).
Evidence:
```js
const { config, logAndCache, badCrypto, totalRevenue } = require('./utils');   // totalRevenue nunca usado
```
Impact: falsa impressão de que existe banco remoto, SMTP e cache em uso.
Recommendation: remover (PT-14).
Contract change: NO

### F-15 [LOW] Logging inadequado (AP-14)
File: src/app.js:13; src/utils.js:13
Principle: Clean Code
Description: 2 `console.log` usados como log de aplicação, sem nível nem possibilidade de silenciar (o terceiro, AppManager.js:45, está em F-03).
Evidence:
```js
console.log(`[LOG] Salvando no cache: ${key}`);
```
Impact: ruído em produção, sem distinguir info de erro.
Recommendation: logger mínimo em `utils/logger.js` (níveis `info`/`error`, `console.error` para erros) (PT-14).
Contract change: NO

## Deprecated APIs
Nenhuma API deprecated identificada estaticamente para as versões em uso (Node 22.17.0, Express 4.22.1, sqlite3 5.1.7). Não há `new Buffer`, `url.parse`, `substr`, `req.param`, `app.del`, `body-parser` ou `res.send(status)`; `express.json()` já é usado. A API de callbacks do `sqlite3` é estilo antigo, mas não deprecated (tratada em F-08). A confirmação dinâmica (`node --trace-deprecation`) será feita no baseline da Fase 3.

## Positive Points
- As 10 queries que recebem valores externos usam placeholders `?`: nenhuma SQL Injection (AP-01 ausente). A refatoração deve manter isso.
- `express.json()` nativo em vez de `body-parser`.
- CommonJS consistente e `npm start` → `node src/app.js` simples; serão mantidos.

## Refactoring Plan (Phase 3 preview)
Strategy: A) decomposição completa: classificação monolítica; `AppManager.js` e `utils.js` são desmontados por camada e domínio e removidos.
Target structure (§4 Node.js/Express, tudo em `src/`, CommonJS, `npm start` inalterado):
```
src/
├── app.js                        # composition root: config → db → schema → models → controllers → routes → errorHandler → listen
├── config/index.js               # PORT, PAYMENT_GATEWAY_KEY, ADMIN_TOKEN lidos de process.env
├── database/
│   ├── connection.js             # abre o SQLite (:memory:), helpers run/get/all promisificados + transaction()
│   └── schema.js                 # CREATE TABLE + seed (senha do seed com hash scrypt)
├── models/                       # acesso a dados + regras de domínio, um arquivo por entidade
│   ├── userModel.js
│   ├── courseModel.js
│   ├── enrollmentModel.js
│   ├── paymentModel.js
│   └── auditLogModel.js
├── controllers/                  # factories ({ db, models, services }) => handlers; orquestram e validam a borda
│   ├── checkoutController.js
│   ├── reportController.js
│   └── userController.js
├── routes/index.js               # View: Router que só mapeia URL → controller (+ requireAdmin nas rotas protegidas)
├── services/paymentService.js    # "gateway" de pagamento (regra do prefixo, cartão mascarado, sem logar a chave)
├── middlewares/
│   ├── errorHandler.js           # AppError + middleware (err, req, res, next) + asyncHandler
│   └── auth.js                   # requireAdmin (Bearer ADMIN_TOKEN, fail-closed)
└── utils/
    ├── constants.js              # PAYMENT_STATUS, APPROVED_CARD_PREFIX
    ├── password.js               # hashPassword/verifyPassword com crypto.scrypt + salt
    └── logger.js
```
Rotas ficam em `routes/` (View) e handlers em `controllers/`, camadas separadas. Removidos: `src/AppManager.js`, `src/utils.js`. Criados: `.env.example`; README atualizado com as variáveis.
Contract changes requiring approval:
- F-04: `GET /api/admin/financial-report` e `DELETE /api/users/:id` passam a exigir `Authorization: Bearer <ADMIN_TOKEN>`; 401 sem credencial ou com token inválido.
- F-08: `DELETE /api/users/:id` apaga também matrículas e pagamentos do usuário; a resposta muda de `Usuário deletado, mas as matrículas e pagamentos ficaram sujos no banco.` para `Usuário deletado`; id inexistente → 404 `Usuário não encontrado` (hoje 200).
- F-11: entradas malformadas hoje não validadas (ex.: `card` não-string, `c_id` não inteiro) passam a 400 `Bad Request` em vez de 500/404. `pwd` continua opcional no contrato, mas sem senha default conhecida (é gerada aleatoriamente e só o hash é gravado).
Out of scope: o checkout com e-mail já cadastrado não verifica a senha (qualquer pessoa matricula outra conta pelo e-mail). Corrigir exigiria autenticação do comprador e mudaria o contrato do checkout (401 para senha errada); fica registrado como recomendação, não incluído sem aprovação explícita.

================================
Total: 15 findings
================================
