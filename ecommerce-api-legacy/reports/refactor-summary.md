================================
PHASE 3: REFACTORING COMPLETE
================================
## Strategy
A) Decomposição completa: a God Class `AppManager` e o `utils.js` foram desmontados nas camadas da §4 (Node/Express). `src/app.js` virou composition root, e os dois arquivos antigos foram removidos.

## New Project Structure
```
ecommerce-api-legacy/
├── package.json                      # "start": "node src/app.js" (inalterado)
├── .env.example                      # PORT, DATABASE_FILE, PAYMENT_GATEWAY_KEY, ADMIN_TOKEN
├── api.http                          # + header Authorization nas rotas protegidas
├── README.md                         # variáveis, rotas e estrutura atualizadas
└── src/
    ├── app.js                        # Entry point / composition root (createApp + listen só se executado direto)
    ├── config/index.js               # Config: tudo via process.env
    ├── database/
    │   ├── connection.js             # Database: helpers Promise + transaction() serializada
    │   └── schema.js                 # Database: CREATE TABLE IF NOT EXISTS, migração idempotente (deleted/deleted_at), seed
    ├── models/                       # Model: SQL parametrizado + regras de domínio
    │   ├── userModel.js              #   findActiveByEmail, create, softDelete
    │   ├── courseModel.js            #   findActiveById
    │   ├── enrollmentModel.js        #   create
    │   ├── paymentModel.js           #   PAYMENT_STATUS, create, countsAsRevenue
    │   ├── auditLogModel.js          #   create
    │   └── reportModel.js            #   financialRows (1 query com LEFT JOIN)
    ├── controllers/                  # Controller: fluxo do caso de uso
    │   ├── checkoutController.js     #   validação de borda + cobrança + transação
    │   ├── reportController.js       #   agrupa linhas por curso
    │   └── userController.js         #   soft delete
    ├── routes/index.js               # View: URL + método → controller (+ requireAdmin)
    ├── services/paymentService.js    # Service: gateway simulado, cartão mascarado no log
    ├── middlewares/
    │   ├── errorHandler.js           # Middleware: AppError, asyncHandler, handler central (texto puro)
    │   └── auth.js                   # Middleware: requireAdmin (Bearer, comparação em tempo constante)
    └── utils/password.js             # Utils: scrypt + salt, senha aleatória
```

## Findings Resolved
| ID | Severity | Anti-pattern | Status | How (PT-xx) |
|----|----------|--------------|--------|-------------|
| F-01 | CRITICAL | Credenciais hardcoded (AP-02) | RESOLVED | PT-02: `config/index.js` lê o ambiente; `dbUser`/`dbPass`/`smtpUser` removidos; `.env.example` |
| F-02 | CRITICAL | Senha insegura (AP-03) | RESOLVED | PT-03: `crypto.scrypt` com salt; sem `pwd`, a senha é aleatória (`randomBytes`) e só o hash é gravado; seed com hash |
| F-03 | CRITICAL | Exposição de dados sensíveis (AP-04) | RESOLVED | PT-04: log só com `**** 4444`, sem a chave do gateway |
| F-04 | CRITICAL | Endpoint sem autenticação (AP-05) | RESOLVED | PT-05: `requireAdmin` nas 2 rotas sensíveis |
| F-05 | CRITICAL | God Class (AP-06) | RESOLVED | PT-06: 18 módulos em camadas; `AppManager.js`/`utils.js` removidos |
| F-06 | HIGH | Regra na camada errada (AP-07) | RESOLVED | PT-07: aprovação no `paymentService`, faturamento em `paymentModel.countsAsRevenue`, fluxo no controller |
| F-07 | HIGH | Estado global / sem DI (AP-08) | RESOLVED | PT-08: cache write-only removido; conexão criada no composition root e injetada |
| F-08 | HIGH | Checkout sem transação (AP-09) | RESOLVED | PT-09: `db.transaction()`; verificado: falha no INSERT de pagamento → rollback (matrículas 2→2, usuário não criado) |
| F-09 | HIGH | Exclusão física (AP-09) | RESOLVED | PT-09 soft delete: `users.deleted` + `deleted_at`; matrículas/pagamentos intactos |
| F-10 | MEDIUM | Query N+1 (AP-10) | RESOLVED | PT-10: relatório com 1 query (antes 1 + C + 2E) |
| F-11 | MEDIUM | Código duplicado (AP-11) | RESOLVED | PT-11: contadores manuais eliminados por async/await + agrupamento único |
| F-12 | MEDIUM | Erro engolido / validação (AP-12) | PARTIAL | PT-12: handler central, `asyncHandler`, nenhum `err` ignorado, validação de tipos (o crash por `card` numérico virou 400). **Não feito:** validação do formato do e-mail, porque não estava entre as mudanças de contrato aprovadas |
| F-13 | LOW | Magic numbers (AP-14) | RESOLVED | PT-14: `APPROVED_CARD_PREFIX`, `PAYMENT_STATUS`, `UNKNOWN_STUDENT`, porta via config; hash caseiro removido |
| F-14 | LOW | Nomes ruins (AP-14) | RESOLVED | PT-14: `usr/eml/pwd/c_id/card` → `name/email/password/courseId/cardNumber` internamente (contrato mantido) |
| F-15 | LOW | Código morto (AP-14) | RESOLVED | PT-14: `totalRevenue`, `globalCache`, `logAndCache`, configs sem uso removidos |
| F-16 | LOW | Logging inadequado (AP-14) | RESOLVED | PT-14: log do cache removido; logs com prefixo/nível (`console.info/warn/error`); sem lib de logger (nenhuma dependência nova) |

## Contract Changes Applied
- F-04: `GET /api/admin/financial-report` e `DELETE /api/users/:id` exigem `Authorization: Bearer <ADMIN_TOKEN>` → 401 "Não autorizado" sem credencial ou com token inválido. Sem `ADMIN_TOKEN` configurado, as rotas ficam fechadas (401).
- F-09: o DELETE responde "Usuário removido." (200 mantido, inclusive para id inexistente ou já removido, como antes). O relatório mostra o nome do aluno removido em vez de `"Unknown"`.
- F-12: `card` não-string, `c_id` não inteiro, ou `usr`/`eml`/`pwd` com tipo errado → 400 "Bad Request" (antes derrubava o processo). Erros inesperados → 500 "Erro interno".
- **Ajuste pedido pelo usuário:** `pwd` continua opcional (a mudança F-02 do plano original, 400 sem `pwd`, **não** foi aplicada); sem `pwd`, é gerada uma senha aleatória e só o hash é gravado.

Mudanças internas, sem efeito na resposta:
- Pagamento recusado não cria mais o usuário: a cobrança é decidida antes da transação.
- Ordem dos alunos no relatório: agora é a ordem do id da matrícula. Antes dependia da chegada dos callbacks (no curso Docker, `[Leonan, Guilherme]` virou `[Guilherme, Leonan]`). Chaves e valores são os mesmos.
- Unicidade: um e-mail de usuário removido pode ser usado de novo no checkout e gera um novo usuário. O comportamento anterior era o mesmo, porque não há `UNIQUE` em `email`.
- Desvios do plano: `PAYMENT_STATUS` ficou em `models/paymentModel.js` (enum do domínio de pagamentos) e o `paymentService` devolve só aprovado/recusado. Foi adicionada a variável opcional `DATABASE_FILE` (default `:memory:`, igual ao original).

## Validation
  ✓ Application boots without errors (`npm start` e `node --trace-deprecation src/app.js`)
  ✓ All endpoints respond as baseline (13/13 chamadas: mesmo status e mesmas chaves, ou mudança aprovada)
  ✓ Approved contract changes verified (401 sem token e com token inválido; 200 com token; soft delete persistido no banco)
  ✓ No deprecation warnings from project code (nenhum, nem no baseline nem depois)
  ✓ No CRITICAL/HIGH anti-patterns remaining (sinais de AP-02/03/04/05/06/07/08/09 reexecutados: 0 ocorrências)
  ✓ MVC structure checklist complete (§7: os 9 itens atendidos)

Soft delete (banco SQLite descartável, `DATABASE_FILE` no scratchpad): após o `DELETE /api/users/1`, a linha existe com `deleted = 1` e `deleted_at` preenchido; 1 matrícula e 1 pagamento preservados; o checkout com o mesmo e-mail não encontra o removido e cria um novo usuário; o relatório continua mostrando "Leonan". A API não tem GET de usuário por id, então o critério "GET por id → 404" não se aplica.

## Endpoint Comparison
| Método | Rota | Caso | Baseline | Depois | OK |
|--------|------|------|----------|--------|----|
| POST | /api/checkout | sucesso (novo usuário) | 200 `{enrollment_id, msg}` | 200 `{enrollment_id, msg}` | ✓ |
| POST | /api/checkout | pagamento recusado | 400 "Pagamento recusado" | 400 "Pagamento recusado" | ✓ |
| POST | /api/checkout | campos faltando | 400 "Bad Request" | 400 "Bad Request" | ✓ |
| POST | /api/checkout | curso inexistente | 404 "Curso não encontrado" | 404 "Curso não encontrado" | ✓ |
| POST | /api/checkout | usuário existente sem pwd | 200 `{enrollment_id, msg}` | 200 `{enrollment_id, msg}` | ✓ |
| POST | /api/checkout | e-mail novo sem pwd | 200 `{enrollment_id, msg}` | 200 `{enrollment_id, msg}` | ✓ |
| POST | /api/checkout | e-mail de usuário removido | 200 `{enrollment_id, msg}` | 200 `{enrollment_id, msg}` | ✓ |
| POST | /api/checkout | `card` numérico | sem resposta (processo caiu, ECONNRESET) | 400 "Bad Request" | ✓ (aprovada) |
| GET | /api/admin/financial-report | com token | 200 `[{course, revenue, students}]` ×2 | 200 `[{course, revenue, students}]` ×2, mesmos valores | ✓ |
| GET | /api/admin/financial-report | sem token / token inválido | 200 | 401 "Não autorizado" | ✓ (aprovada) |
| GET | /api/admin/financial-report | após delete | 200, aluno "Unknown" | 200, aluno "Leonan" | ✓ (aprovada) |
| DELETE | /api/users/1 | com token | 200 "Usuário deletado, mas…" | 200 "Usuário removido." | ✓ (aprovada) |
| DELETE | /api/users/1 | sem token | 200 | 401 "Não autorizado" | ✓ (aprovada) |
| DELETE | /api/users/999 | id inexistente | 200 | 200 "Usuário removido." | ✓ |

## How to run
```bash
npm install
ADMIN_TOKEN=um-token-forte PAYMENT_GATEWAY_KEY=<chave> npm start     # porta 3000 (PORT para mudar)
```
Em PowerShell: `$env:ADMIN_TOKEN='um-token-forte'; npm start`.
Variáveis (ver `.env.example`): `PORT` (3000), `DATABASE_FILE` (`:memory:`), `PAYMENT_GATEWAY_KEY`, `ADMIN_TOKEN` (sem ele, as rotas admin respondem 401).
Rotas admin: header `Authorization: Bearer <ADMIN_TOKEN>` (já configurado no `api.http` via `@adminToken`).
================================
