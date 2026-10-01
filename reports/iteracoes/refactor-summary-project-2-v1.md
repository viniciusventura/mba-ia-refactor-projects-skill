================================
PHASE 3: REFACTORING COMPLETE
================================
## Strategy
A) Decomposição completa: `AppManager.js` (God Class) e `utils.js` foram desmontados por camada e domínio na estrutura Express da §4 e removidos; `npm start` → `node src/app.js` foi mantido.

## New Project Structure
```
ecommerce-api-legacy/
├── package.json                    # inalterado ("start": "node src/app.js")
├── .env.example                    # NOVO: PORT, DATABASE_PATH, ADMIN_TOKEN, PAYMENT_GATEWAY_KEY
├── api.http                        # atualizado: Authorization: Bearer {{adminToken}} nas rotas protegidas
├── README.md                       # atualizado: variáveis de ambiente e estrutura
└── src/
    ├── app.js                      # Entry point / composition root (createApp + listen)
    ├── config/index.js             # Config: lida de process.env, sem segredos
    ├── database/
    │   ├── connection.js           # Database: helpers async + transaction() serializada
    │   └── schema.js               # Database: CREATE TABLE + seed (senha com scrypt)
    ├── models/                     # Model: SQL parametrizado + regras de domínio
    │   ├── userModel.js
    │   ├── courseModel.js          # inclui o relatório financeiro (1 JOIN + agregação)
    │   ├── enrollmentModel.js
    │   ├── paymentModel.js
    │   └── auditLogModel.js
    ├── controllers/                # Controller: validação da borda + orquestração
    │   ├── checkoutController.js
    │   ├── reportController.js
    │   └── userController.js
    ├── routes/index.js             # View: URL → controller (+ requireAdmin)
    ├── services/paymentService.js  # Service: gateway de pagamento simulado (cartão mascarado)
    ├── middlewares/
    │   ├── errorHandler.js         # AppError + asyncHandler + middleware central
    │   └── auth.js                 # requireAdmin (Bearer, timing-safe, fail-closed)
    └── utils/
        ├── constants.js            # PAYMENT_STATUS, APPROVED_CARD_PREFIX, UNKNOWN_STUDENT
        ├── password.js             # hashPassword/verifyPassword (crypto.scrypt + salt)
        └── logger.js               # logger com níveis
```
Removidos: `src/AppManager.js`, `src/utils.js`. Nenhuma dependência nova (`crypto` é nativo).

## Findings Resolved
| ID | Severity | Anti-pattern | Status | How (PT-xx) |
|----|----------|--------------|--------|-------------|
| F-01 | CRITICAL | Credenciais hardcoded (AP-02) | RESOLVED | PT-02: `config/index.js` lê o ambiente; `dbUser`/`dbPass`/`smtpUser` removidos |
| F-02 | CRITICAL | Senha insegura (AP-03) | RESOLVED | PT-03: scrypt + salt; seed hasheado; sem default `123456` (senha aleatória quando `pwd` ausente) |
| F-03 | CRITICAL | Exposição de dados sensíveis (AP-04) | RESOLVED | PT-04: log mostra `**** 4444`; a chave nunca é logada |
| F-04 | CRITICAL | Endpoint sem autenticação (AP-05) | RESOLVED | PT-05: `requireAdmin` nas 2 rotas |
| F-05 | CRITICAL | God Class (AP-06) | RESOLVED | PT-06: 19 arquivos por camada/domínio |
| F-06 | HIGH | Regra na camada errada (AP-07) | RESOLVED | PT-07: pagamento em `paymentService`, receita em `courseModel`, fluxo nos controllers |
| F-07 | HIGH | Estado global / sem DI (AP-08) | RESOLVED | PT-08: cache write-only removido; db/serviços injetados pelo `app.js` |
| F-08 | HIGH | Sem transação (AP-09) | RESOLVED | PT-09: checkout e delete em `db.transaction()`; pagamento decidido antes de qualquer escrita |
| F-09 | MEDIUM | N+1 (AP-10) | RESOLVED | PT-10: 1 query com LEFT JOIN (antes 1 + C + 2E), ordem determinística |
| F-10 | MEDIUM | Código duplicado (AP-11) | RESOLVED | PT-10/PT-11: bloco de fechamento eliminado |
| F-11 | MEDIUM | Erros / validação (AP-12) | RESOLVED | PT-12: `errorHandler` + `asyncHandler` + validação de tipos na borda |
| F-12 | LOW | Magic numbers (AP-14) | RESOLVED | PT-14: `utils/constants.js` |
| F-13 | LOW | Nomes ruins (AP-14) | RESOLVED | PT-14: `{ usr: name, eml: email, ... }`; contrato mantido |
| F-14 | LOW | Código morto (AP-14) | RESOLVED | PT-14: `totalRevenue`, `globalCache`, `dbUser`, `dbPass`, `smtpUser` removidos |
| F-15 | LOW | Logging (AP-14) | RESOLVED | PT-14: `utils/logger.js` |

## Contract Changes Applied
- F-04: `GET /api/admin/financial-report` e `DELETE /api/users/:id` exigem `Authorization: Bearer <ADMIN_TOKEN>`; sem credencial ou com token inválido → 401 `Não autorizado`. Sem `ADMIN_TOKEN` configurado → sempre 401 (fail-closed).
- F-08: `DELETE /api/users/:id` remove também matrículas e pagamentos do usuário; resposta `Usuário deletado`; id inexistente → 404 `Usuário não encontrado`.
- F-11: entradas malformadas → 400 `Bad Request` (`card` não-string, `c_id` não inteiro, JSON inválido, `:id` não numérico). Antes, `card` numérico **derrubava o processo** (comprovado no baseline).
- `api.http`: header `Authorization` adicionado nas rotas protegidas (pedido na aprovação).

Observações (não fazem parte do contrato testado):
- Falhas internas inesperadas (erro de banco) respondem 500 `Erro interno` no lugar dos textos específicos anteriores (`Erro DB`, `Erro Matrícula`...), e o detalhe vai para o log.
- Um checkout recusado não cria mais o usuário (antes, o usuário ficava gravado).
- Mensagem de boot: `[INFO] LMS API rodando na porta 3000`.

## Validation
  ✓ Application boots without errors
  ✓ All endpoints respond as baseline (6/6 chamadas sem mudança aprovada; as 3 com mudança aprovada também verificadas)
  ✓ Approved contract changes verified (401 sem credencial e com token inválido nas 2 rotas; status original com credencial; DELETE 404/texto novo)
  ✓ No deprecation warnings from project code (`--trace-deprecation`, antes e depois: nenhum)
  ✓ No CRITICAL/HIGH anti-patterns remaining (sinais AP-02/03/04/05/07/08 rodados de novo: sem ocorrência)
  ✓ MVC structure checklist complete (§7: config sem segredos; models sem HTTP; rotas só delegam; controllers sem SQL; handler central; composition root; service isolado; sem estado global mutável; `npm start` mantido)

Extra: 20 checkouts concorrentes → 20×200, contagens e receitas exatas no relatório (fila de transações).

## Endpoint Comparison
Mesma preparação nos dois casos: banco `:memory:` novo a cada boot, seed automático, mesma sequência de chamadas.

| Método | Rota | Caso | Baseline | Depois | OK |
|--------|------|------|----------|--------|----|
| POST | /api/checkout | sucesso (novo usuário) | 200 `{msg, enrollment_id}` | 200 `{msg, enrollment_id}` | ✓ |
| POST | /api/checkout | pagamento recusado | 400 `Pagamento recusado` | 400 `Pagamento recusado` | ✓ |
| POST | /api/checkout | campos ausentes | 400 `Bad Request` | 400 `Bad Request` | ✓ |
| POST | /api/checkout | curso inexistente | 404 `Curso não encontrado` | 404 `Curso não encontrado` | ✓ |
| POST | /api/checkout | usuário existente | 200 `{msg, enrollment_id}` | 200 `{msg, enrollment_id}` | ✓ |
| POST | /api/checkout | `card` numérico | processo encerrado (TypeError) | 400 `Bad Request` | ✓ (aprovado F-11) |
| GET | /api/admin/financial-report | com token | 200 `[{course, revenue, students}]` ×2 | 200, mesmos valores, ordem por id | ✓ |
| GET | /api/admin/financial-report | sem token / token inválido | 200 | 401 `Não autorizado` | ✓ (aprovado F-04) |
| DELETE | /api/users/999 | inexistente | 200 texto antigo | 404 `Usuário não encontrado` | ✓ (aprovado F-08) |
| DELETE | /api/users/1 | com token | 200 texto antigo | 200 `Usuário deletado` | ✓ (aprovado F-08) |
| DELETE | /api/users/2 | sem token / token inválido | 200 | 401 `Não autorizado` | ✓ (aprovado F-04) |
| GET | /api/admin/financial-report | após delete | 200, alunos `Unknown` órfãos | 200, sem órfãos | ✓ (aprovado F-08) |

## How to run
```bash
npm install
cp .env.example .env              # defina ADMIN_TOKEN
node --env-file=.env src/app.js   # ou: ADMIN_TOKEN=<token> npm start
```
Variáveis: `PORT` (3000), `DATABASE_PATH` (`:memory:`), `ADMIN_TOKEN` (obrigatória para as rotas admin), `PAYMENT_GATEWAY_KEY` (opcional, gateway simulado). Em `api.http`, ajuste `@adminToken`.
Nada foi commitado: `src/AppManager.js` e `src/utils.js` aparecem como removidos no `git status`.
================================
