================================
ARCHITECTURE AUDIT REPORT
================================
Project:  ecommerce-api-legacy
Stack:    JavaScript (Node.js v22.17.0, CommonJS) + Express ^4.18.2 (instalado 4.22.1) + sqlite3 ^5.1.6 (instalado 5.1.7)
Files:    3 analyzed | ~180 lines of code
Date:     2026-10-01
Architecture: A) Monolítica / God Class: `src/AppManager.js` concentra conexão, schema, seed, SQL, regra de pagamento, validação e as 3 rotas; `src/utils.js` mistura config com segredos, cache global e "hash" de senha

## Summary
CRITICAL: 5 | HIGH: 4 | MEDIUM: 3 | LOW: 4

| ID | Severity | Anti-pattern | Location |
|----|----------|--------------|----------|
| F-01 | CRITICAL | Credenciais hardcoded (AP-02) | src/utils.js:2-6 |
| F-02 | CRITICAL | Armazenamento inseguro de senha (AP-03) | src/utils.js:17-23, src/AppManager.js:18, 68-69 |
| F-03 | CRITICAL | Exposição de dados sensíveis (AP-04) | src/AppManager.js:45 |
| F-04 | CRITICAL | Endpoint sensível sem autenticação (AP-05) | src/AppManager.js:80, 131 |
| F-05 | CRITICAL | God Class / God File (AP-06) | src/AppManager.js:1-141, src/utils.js:1-25 |
| F-06 | HIGH | Regra de negócio na camada errada (AP-07) | src/AppManager.js:43-75, 46, 66-75, 89-127, 108-110 |
| F-07 | HIGH | Estado global mutável / acoplamento sem DI (AP-08) | src/utils.js:9, 14, 25; src/AppManager.js:7, 26 |
| F-08 | HIGH | Operação multi-etapa sem transação: checkout (AP-09) | src/AppManager.js:50-63, 69-71 |
| F-09 | HIGH | Exclusão física de usuário com histórico (AP-09) | src/AppManager.js:131-137 |
| F-10 | MEDIUM | Query N+1 (AP-10) | src/AppManager.js:83, 92, 104, 106 |
| F-11 | MEDIUM | Código duplicado (AP-11) | src/AppManager.js:95-99, 118-122 |
| F-12 | MEDIUM | Erro engolido / sem handler central / validação ausente (AP-12) | src/AppManager.js:35, 38, 46, 57, 68, 92-93, 104, 106, 133-135; src/app.js:1-14 |
| F-13 | LOW | Magic numbers/strings (AP-14) | src/AppManager.js:21, 46, 108; src/utils.js:6, 19-22 |
| F-14 | LOW | Nomes ruins (AP-14) | src/AppManager.js:29-33, 26 |
| F-15 | LOW | Código morto (AP-14) | src/utils.js:2-3, 5, 10, 25; src/AppManager.js:2 |
| F-16 | LOW | Logging inadequado (AP-14) | src/app.js:13, src/utils.js:13 |

## Findings

### F-01 [CRITICAL] Credenciais hardcoded (AP-02)
File: src/utils.js:2-6
Principle: OWASP A07 / 12-Factor App (Config)
Description: 2 segredos literais sem nenhuma leitura de ambiente (`dbPass` na linha 3, `paymentGatewayKey` com prefixo `pk_live_` na linha 4), além de configuração fixa (`dbUser` linha 2, `smtpUser` linha 5, `port` linha 6). Não há `process.env` em nenhum arquivo do projeto. A chave do gateway também vaza em log (ver F-03).
Evidence:
```js
dbPass: "senha_super_secreta_prod_123",
paymentGatewayKey: "pk_live_1234567890abcdef",
```
Impact: qualquer pessoa com acesso ao repositório tem a chave de produção do gateway e a senha do banco; trocar segredos exige deploy de código.
Recommendation: extrair para `src/config/index.js` lendo `process.env` (PAYMENT_GATEWAY_KEY, PORT, ADMIN_TOKEN), com `.env.example` sem valores reais; remover `dbUser`/`dbPass`/`smtpUser`, que nunca são usados (PT-02).
Contract change: NO

### F-02 [CRITICAL] Armazenamento inseguro de senha (AP-03)
File: src/utils.js:17-23, src/AppManager.js:18, 68-69
Principle: OWASP A02 Cryptographic Failures
Description: o "hash" `badCrypto` repete os 2 primeiros caracteres do base64 da senha; o resultado depende só dos ~12 primeiros bits da senha. Senha ausente vira o default `"123456"` (linha 68). O usuário do seed é gravado em texto puro (`'123'`, linha 18). Não há bcrypt/scrypt/argon2/pbkdf2 no projeto.
Evidence:
```js
hash += Buffer.from(pwd).toString('base64').substring(0, 2);
let hash = badCrypto(p || "123456");
```
Executado: `senhaforte`, `senha` e `se123` geram o mesmo valor `c2c2c2c2c2`; `123` e `1234567` geram `MTMTMTMTMT`.
Impact: colisões triviais e reversão imediata; um vazamento do banco expõe todas as senhas.
Recommendation: `crypto.scrypt` nativo do Node com salt aleatório por senha (sem dependência nova); seed também com hash; senha obrigatória ao criar usuário (PT-03).
Contract change: YES: `POST /api/checkout` sem `pwd` para um e-mail **novo** passa a responder 400 "Bad Request" (hoje cria o usuário com senha "123456"). E-mail já existente continua não exigindo `pwd`.

### F-03 [CRITICAL] Exposição de dados sensíveis (AP-04)
File: src/AppManager.js:45
Principle: OWASP A01/A09
Description: o número completo do cartão e a chave de produção do gateway são escritos em log a cada checkout (1 ocorrência).
Evidence:
```js
console.log(`Processando cartão ${cc} na chave ${config.paymentGatewayKey}`);
```
Impact: PAN e chave do gateway em logs (violação PCI-DSS); qualquer pessoa com acesso aos logs pode usá-los.
Recommendation: remover o log; se necessário, registrar só os 4 últimos dígitos, sem a chave (PT-04 + PT-02).
Contract change: NO

### F-04 [CRITICAL] Endpoint sensível sem autenticação (AP-05)
File: src/AppManager.js:80, 131
Principle: OWASP A01 Broken Access Control
Description: 2 rotas sensíveis sem nenhuma autenticação, e o projeto não tem mecanismo de auth algum (nenhum `auth`/`jwt`/middleware antes das rotas): `GET /api/admin/financial-report` expõe faturamento e nomes de alunos; `DELETE /api/users/:id` apaga qualquer usuário.
Evidence:
```js
app.get('/api/admin/financial-report', (req, res) => {
app.delete('/api/users/:id', (req, res) => {
```
Impact: qualquer cliente anônimo lê dados financeiros e pessoais ou apaga usuários (explorável sem autenticação).
Recommendation: middleware `requireAdmin` em `src/middlewares/auth.js` exigindo `Authorization: Bearer <ADMIN_TOKEN>` (token vindo do ambiente, comparação em tempo constante; sem token configurado, a rota fica fechada) (PT-05).
Contract change: YES: as duas rotas passam a responder 401 sem credencial válida; com credencial, o status original.

### F-05 [CRITICAL] God Class / God File (AP-06)
File: src/AppManager.js:1-141, src/utils.js:1-25
Principle: SRP (SOLID) + MVC
Description: `AppManager` acumula 7 responsabilidades de camadas diferentes: conexão (7), DDL (12-16), seed (18-21), rotas/HTTP (28, 80, 131), validação de entrada (35), regra de pagamento / integração com gateway (45-46), acesso a dados (37, 40, 50, 54, 57, 69, 83, 92, 104, 106, 133) e agregação do relatório (89-127). `utils.js` mistura config (1-7), cache (9-15) e criptografia (17-23).
Evidence:
```js
class AppManager {
    constructor() { this.db = new sqlite3.Database(':memory:'); }
    initDb() { ... CREATE TABLE ... INSERT ... }
    setupRoutes(app) { app.post('/api/checkout', ...) ... }
```
Impact: qualquer mudança toca o mesmo arquivo; impossível testar regra sem HTTP e banco; 4 níveis de callbacks aninhados.
Recommendation: decomposição completa em `config/`, `database/`, `models/`, `controllers/`, `routes/`, `services/`, `middlewares/` (PT-06).
Contract change: NO

### F-06 [HIGH] Regra de negócio na camada errada (AP-07)
File: src/AppManager.js:43-75, 46, 66-75, 89-127, 108-110
Principle: SRP (SOLID) + MVC
Description: 3 regras de domínio dentro de handlers HTTP: aprovação de pagamento (`cc.startsWith("4")`, linha 46), fluxo "cria usuário se não existe → matricula → paga → audita" (43-75) e cálculo de faturamento por curso, somando só pagamentos `PAID` (108-110).
Evidence:
```js
let status = cc.startsWith("4") ? "PAID" : "DENIED";
if (payment && payment.status === 'PAID') { courseData.revenue += payment.amount; }
```
Impact: a regra não pode ser reutilizada (CLI, fila) nem testada sem HTTP; a integração com o gateway fica misturada com o handler.
Recommendation: aprovação do pagamento em `services/paymentService.js`; orquestração do checkout em `controllers/checkoutController.js`; montagem do relatório no controller com dados vindos do model (PT-07).
Contract change: NO

### F-07 [HIGH] Estado global mutável / acoplamento sem DI (AP-08)
File: src/utils.js:9, 14, 25; src/AppManager.js:7, 26
Principle: DIP (SOLID)
Description: `globalCache` é um objeto de módulo exportado e mutado a cada checkout (linha 14), sem limite de tamanho, e nunca lido. A conexão é criada dentro do construtor (`new sqlite3.Database(':memory:')`), sem injeção, e as rotas dependem de `this`/`self` capturados por closure.
Evidence:
```js
let globalCache = {};
function logAndCache(key, data) { globalCache[key] = data; }
```
Impact: crescimento de memória sem limite (uma chave por usuário); estado compartilhado entre requisições; impossível trocar o banco em teste.
Recommendation: remover o cache (é escrito e nunca lido); conexão criada em `database/connection.js` e injetada nos models/controllers pelo composition root `app.js` (PT-08).
Contract change: NO

### F-08 [HIGH] Operação multi-etapa sem transação: checkout (AP-09)
File: src/AppManager.js:50-63, 69-71
Principle: Integridade (ACID)
Description: o checkout grava em até 4 tabelas (`users` 69, `enrollments` 50, `payments` 54, `audit_logs` 57) em callbacks aninhados, sem `BEGIN/COMMIT/ROLLBACK`.
Evidence:
```js
this.db.run("INSERT INTO enrollments ...", [userId, cid], function(err) {
    self.db.run("INSERT INTO payments ...", [enrId, course.price, status], function(err) {
```
Impact: se o INSERT de pagamento falhar, a matrícula fica gravada sem pagamento (acesso ao curso sem pagar); um pagamento recusado já deixou o usuário criado.
Recommendation: helpers promisificados + `transaction()` em `database/connection.js`, envolvendo criação de usuário, matrícula, pagamento e auditoria numa única transação com async/await (PT-09).
Contract change: NO

### F-09 [HIGH] Exclusão física de usuário com histórico (AP-09)
File: src/AppManager.js:131-137
Principle: Integridade (ACID)
Description: `DELETE FROM users` apaga o aluno e deixa `enrollments` e `payments` órfãos (a própria resposta admite). O relatório financeiro passa a mostrar `'Unknown'` no lugar do aluno.
Evidence:
```js
this.db.run("DELETE FROM users WHERE id = ?", [id], (err) => {
    res.send("Usuário deletado, mas as matrículas e pagamentos ficaram sujos no banco.");
```
Impact: perda de histórico de negócio (quem pagou o quê); dados órfãos.
Recommendation: soft delete (PT-09): coluna nova `users.deleted INTEGER NOT NULL DEFAULT 0` (+ `deleted_at DATETIME`); o DELETE vira `UPDATE`; leituras de negócio (busca de usuário por e-mail no checkout) filtram `deleted = 0`; o relatório financeiro continua mostrando o aluno. Sem cascata: matrículas e pagamentos são histórico e permanecem.
Contract change: YES: o texto da resposta passa de "Usuário deletado, mas as matrículas e pagamentos ficaram sujos no banco." para "Usuário removido." (status 200 mantido); no relatório, o aluno removido aparece pelo nome em vez de `'Unknown'`.

### F-10 [MEDIUM] Query N+1 (AP-10)
File: src/AppManager.js:83, 92, 104, 106
Principle: Performance
Description: o relatório executa 1 query de cursos + 1 query de matrículas por curso (92, dentro do `forEach` de 89) + 2 queries por matrícula (104 e 106, dentro do `forEach` de 102): 1 + C + 2E queries. Com o seed: 1 + 2 + 2 = 5; com 100 cursos e 10 mil matrículas, 20.101.
Evidence:
```js
courses.forEach(c => {
    this.db.all("SELECT * FROM enrollments WHERE course_id = ?", [c.id], ...
        enrollments.forEach(enr => { this.db.get("SELECT name, email FROM users WHERE id = ?", ...
```
Impact: tempo de resposta cresce linearmente com o número de matrículas.
Recommendation: uma única query com `LEFT JOIN` courses → enrollments → users → payments, agrupada no controller (PT-10).
Contract change: NO (a ordem dos alunos dentro de cada curso hoje depende da ordem de chegada dos callbacks; passa a ser a ordem por id da matrícula).

### F-11 [MEDIUM] Código duplicado (AP-11)
File: src/AppManager.js:95-99, 118-122
Principle: DRY
Description: o bloco de "fechamento de curso" (push no relatório, decremento do contador, resposta quando chega a zero) aparece 2 vezes com o mesmo comportamento.
Evidence:
```js
report.push(courseData);
coursesPending--;
if (coursesPending === 0) res.json(report);
```
Impact: contador manual duplicado; uma correção em um ramo e não no outro faz a resposta nunca ser enviada (requisição pendurada).
Recommendation: eliminado ao trocar os contadores por async/await e agrupamento único (PT-11 + PT-10).
Contract change: NO

### F-12 [MEDIUM] Erro engolido / sem handler central / validação ausente (AP-12)
File: src/AppManager.js:35, 38, 46, 57, 68, 92-93, 104, 106, 133-135; src/app.js:1-14
Principle: Robustez / Fail-fast
Description: 5 callbacks em que `err` nunca é testado (57, 92, 104, 106, 133); na linha 93, se a query falhar, `enrollments.length` lança TypeError dentro do callback e derruba o processo. Erro de banco na linha 38 vira 404 "Curso não encontrado". Não há middleware de erro `(err, req, res, next)`. Validação: só presença de campos (35); `card` não numérico em string (ex.: número JSON) faz `cc.startsWith` (46) lançar TypeError dentro de callback do sqlite e **derrubar o servidor**; `c_id`, formato de e-mail e `pwd` (68) não são validados. O DELETE responde sucesso mesmo com erro (133-135).
Evidence:
```js
this.db.all("SELECT * FROM enrollments WHERE course_id = ?", [c.id], (err, enrollments) => {
    let enrPending = enrollments.length;
let status = cc.startsWith("4") ? "PAID" : "DENIED";   // card: 4111... (number) → TypeError
```
Impact: uma única requisição malformada derruba a API para todos (DoS); falhas de banco ficam invisíveis.
Recommendation: `middlewares/errorHandler.js` + `asyncHandler`; validação na borda do checkout (tipos de `card`, `c_id`, e-mail) (PT-12).
Contract change: YES: `POST /api/checkout` com `card` não-string ou `c_id` não inteiro passa a responder 400 "Bad Request" (hoje derruba o processo / responde 404). Erros inesperados passam a responder 500 em texto pelo handler central.

### F-13 [LOW] Magic numbers/strings (AP-14)
File: src/AppManager.js:21, 46, 108; src/utils.js:6, 19-22
Principle: Clean Code
Description: 5 literais de domínio sem nome: prefixo de aprovação `"4"` (46), status `'PAID'`/`'DENIED'` repetidos como string (21, 46, 108), porta `3000` (utils 6), `10000` e `10` no hash (19, 22).
Evidence:
```js
let status = cc.startsWith("4") ? "PAID" : "DENIED";
```
Impact: regra escondida; risco de erro de digitação nos status.
Recommendation: constantes `PAYMENT_STATUS` e `APPROVED_CARD_PREFIX` em `services/paymentService.js`; porta via config (PT-14).
Contract change: NO

### F-14 [LOW] Nomes ruins (AP-14)
File: src/AppManager.js:29-33, 26
Principle: Clean Code
Description: 5 variáveis de 1-3 letras (`u`, `e`, `p`, `cid`, `cc`) e o alias `self` (26). Os campos do contrato (`usr`, `eml`, `pwd`, `c_id`, `card`) também são abreviados, mas fazem parte da API e serão mantidos.
Evidence:
```js
let u = req.body.usr; let e = req.body.eml; let p = req.body.pwd; let cid = req.body.c_id; let cc = req.body.card;
```
Impact: leitura mais lenta.
Recommendation: mapear o body para nomes claros (`name`, `email`, `password`, `courseId`, `cardNumber`) na borda (PT-14).
Contract change: NO

### F-15 [LOW] Código morto (AP-14)
File: src/utils.js:2-3, 5, 10, 25; src/AppManager.js:2
Principle: Clean Code
Description: 5 símbolos sem uso: `totalRevenue` (declarado em 10, importado em AppManager.js:2 e nunca usado), `globalCache` exportado e nunca importado (25), `config.dbUser`, `config.dbPass`, `config.smtpUser` (2, 3, 5) nunca lidos.
Evidence:
```js
let totalRevenue = 0;
const { config, logAndCache, badCrypto, totalRevenue } = require('./utils');
```
Impact: ruído e falsa impressão de que existe integração com SMTP/banco remoto.
Recommendation: remover (PT-14).
Contract change: NO

### F-16 [LOW] Logging inadequado (AP-14)
File: src/app.js:13, src/utils.js:13
Principle: Clean Code
Description: `console.log` usado como log da aplicação em 2 pontos (o terceiro, AppManager.js:45, já está em F-03), incluindo o log de cada escrita no cache.
Evidence:
```js
console.log(`[LOG] Salvando no cache: ${key}`);
```
Impact: log sem nível nem estrutura; ruído por requisição.
Recommendation: remover o log do cache (junto com o cache); manter só o log de boot com mensagem neutra (PT-14).
Contract change: NO

## Deprecated APIs
Nenhuma API deprecated identificada para as versões em uso (Node 22, Express 4.22.1, sqlite3 5.1.7). `Buffer.from` já é a forma moderna; a API de callbacks do sqlite3 é estilo antigo, mas não deprecated (tratada em F-08/F-11). A confirmação em execução (`node --trace-deprecation`) será feita no baseline da Fase 3.

## Positive Points
- Todas as queries com entrada externa usam placeholders `?` (nenhum SQL injection).
- `express.json()` nativo em vez de `body-parser`.
- Projeto pequeno, CommonJS, sem dependências desnecessárias.

## Refactoring Plan (Phase 3 preview)
Strategy: A) decomposição completa (monolito: 3 arquivos, God Class `AppManager`).
Target structure (mvc-guidelines §4, Node/Express; `package.json` "start" inalterado):
```
src/
├── app.js                          # composition root: config → db → schema → models → controllers → routes → errorHandler → listen
├── config/index.js                 # PORT, PAYMENT_GATEWAY_KEY, ADMIN_TOKEN via process.env
├── database/
│   ├── connection.js               # abre ':memory:' + run/get/all promisificados + transaction()
│   └── schema.js                   # CREATE TABLE (users.deleted / deleted_at) + seed com senha em hash
├── models/
│   ├── userModel.js                # findActiveByEmail, create, softDelete
│   ├── courseModel.js              # findActiveById
│   ├── enrollmentModel.js          # create
│   ├── paymentModel.js             # create
│   ├── auditLogModel.js            # create
│   └── reportModel.js              # financialRows (LEFT JOIN único)
├── controllers/
│   ├── checkoutController.js       # checkout (validação de borda + transação)
│   ├── reportController.js         # financialReport (agrupa linhas por curso)
│   └── userController.js           # deleteUser (soft delete)
├── routes/index.js                 # View: Router com as 3 rotas (URLs inalteradas) + requireAdmin
├── services/paymentService.js      # aprovação do cartão, PAYMENT_STATUS
├── middlewares/
│   ├── errorHandler.js             # HttpError, asyncHandler, handler central (respostas em texto, como hoje)
│   └── auth.js                     # requireAdmin (Bearer ADMIN_TOKEN)
└── utils/password.js               # hashPassword com crypto.scrypt + salt
```
`src/AppManager.js` e `src/utils.js` são removidos. Criar `.env.example` e atualizar o README (variáveis e uso do token).
Soft delete: `DELETE /api/users/:id` → `UPDATE users SET deleted = 1, deleted_at = datetime('now') WHERE id = ? AND deleted = 0`. Migração: colunas `deleted INTEGER NOT NULL DEFAULT 0` e `deleted_at DATETIME` no `CREATE TABLE users` de `database/schema.js` (o banco é em memória e recriado a cada boot; não há dados persistidos a migrar). Sem cascata: matrículas, pagamentos e auditoria são histórico e ficam intactos; o relatório financeiro continua listando o aluno. O checkout busca usuário só entre os ativos (`deleted = 0`).
Contract changes requiring approval:
- F-04: `GET /api/admin/financial-report` e `DELETE /api/users/:id` exigem `Authorization: Bearer <ADMIN_TOKEN>`; 401 sem credencial válida.
- F-09: resposta do DELETE passa a ser "Usuário removido." (200 mantido); relatório mostra o nome do aluno removido em vez de `'Unknown'`.
- F-02: checkout de e-mail novo sem `pwd` → 400 "Bad Request" (fim da senha default "123456").
- F-12: checkout com `card` não-string ou `c_id` não inteiro → 400 "Bad Request" (hoje derruba o processo ou responde 404).
Out of scope: não há endpoint de login, então não existe verificação de senha a corrigir; não será adicionada constraint `UNIQUE` em `users.email` nem `FOREIGN KEY` (mudaria comportamento sem pedido). `DELETE /api/users/:id` com id inexistente continua respondendo 200, como hoje.

================================
Total: 16 findings
================================
