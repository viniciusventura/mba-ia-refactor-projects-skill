# ecommerce-api-legacy

LMS API (com fluxo de checkout) em Node.js/Express usada como entrada do desafio `refactor-arch`.

## Como rodar

```bash
npm install
ADMIN_TOKEN=um-token-forte npm start
```

A aplicação sobe em `http://localhost:3000`. O banco SQLite é em memória por padrão e carrega os seeds automaticamente no boot.

## Variáveis de ambiente

Veja `.env.example`. As variáveis são lidas de `process.env`; o projeto não carrega `.env` sozinho.

| Variável | Default | Uso |
|---|---|---|
| `PORT` | `3000` | Porta HTTP |
| `DATABASE_FILE` | `:memory:` | Arquivo SQLite (`:memory:` recria o banco a cada boot) |
| `PAYMENT_GATEWAY_KEY` | (vazio) | Chave do gateway de pagamento |
| `ADMIN_TOKEN` | (vazio) | Token das rotas administrativas. Sem ele, essas rotas respondem 401 |

## Rotas

| Método | Rota | Auth |
|---|---|---|
| POST | `/api/checkout` | pública |
| GET | `/api/admin/financial-report` | `Authorization: Bearer <ADMIN_TOKEN>` |
| DELETE | `/api/users/:id` | `Authorization: Bearer <ADMIN_TOKEN>` (soft delete: matrículas e pagamentos são preservados) |

Exemplos de requisições estão em `api.http`.

## Estrutura

```
src/
├── app.js            # composition root
├── config/           # configuração via ambiente
├── database/         # conexão (helpers async + transação) e schema/seed
├── models/           # acesso a dados e regras de domínio, por entidade
├── controllers/      # fluxo de cada caso de uso
├── routes/           # view: URL → controller
├── services/         # integrações externas (pagamento)
├── middlewares/      # erro centralizado e autenticação de admin
└── utils/            # hash de senha
```
