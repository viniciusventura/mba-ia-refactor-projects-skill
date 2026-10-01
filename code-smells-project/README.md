# code-smells-project

API de E-commerce em Python/Flask usada como entrada do desafio `refactor-arch`.

## Como rodar

```bash
pip install -r requirements.txt
python app.py
```

A aplicação sobe em `http://localhost:5000`. O banco SQLite (`loja.db`) é criado automaticamente no primeiro boot, já com produtos e usuários de exemplo (senhas gravadas com hash). Bancos antigos são migrados no boot: ganham a coluna de soft delete de produtos, e as senhas em texto puro são convertidas para hash.

## Configuração

As variáveis de ambiente estão em `.env.example`. Todas têm default de desenvolvimento. Sem `SECRET_KEY`, uma chave aleatória é gerada a cada boot, e os tokens emitidos deixam de valer quando o servidor reinicia.

## Autenticação

`POST /login` devolve `dados.token`. As rotas administrativas exigem o header `Authorization: Bearer <token>` de um usuário `admin` (401 sem token e 403 para quem não é admin):

- `POST /admin/reset-db`
- `DELETE /produtos/<id>`: soft delete; o produto continua no histórico dos pedidos
- `GET /relatorios/vendas`

```bash
curl -X POST localhost:5000/login -H "Content-Type: application/json" -d '{"email":"admin@loja.com","senha":"admin123"}'
curl localhost:5000/relatorios/vendas -H "Authorization: Bearer <token>"
```

## Estrutura

| Pasta | Camada |
|---|---|
| `app.py` | Entry point (`create_app`) |
| `config/` | Configuração lida do ambiente |
| `database.py` | Conexão por requisição, schema, migrações e seed |
| `models/` | Acesso a dados e regras de domínio, um arquivo por domínio |
| `controllers/` | Fluxo de cada caso de uso e validação de entrada |
| `views/` | Rotas (Blueprints), só delegam aos controllers |
| `services/` | Notificações (e-mail, SMS e push, simulados por log) |
| `middlewares/` | Tratamento de erro centralizado e autenticação |
| `utils/` | Constantes de domínio |
