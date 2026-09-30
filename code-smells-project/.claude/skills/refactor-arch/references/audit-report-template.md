# Template do Relatório de Auditoria (Fase 2)

Formato **obrigatório** da saída da Fase 2. O mesmo conteúdo é impresso no terminal e salvo em `reports/audit-report.md`, dentro do projeto auditado. Os títulos dos blocos seguem o padrão em inglês do enunciado. Descrições, impacto e recomendações são escritos no idioma do usuário (português por padrão).

---

## Regras de preenchimento

1. **Ordenação:** findings em ordem de severidade **CRITICAL → HIGH → MEDIUM → LOW**. Dentro da mesma severidade, pela ordem do catálogo (AP-01, AP-02...).
2. **Numeração:** `F-01`, `F-02`... na ordem final. O ID é usado para referência na Fase 3.
3. **Um finding por anti-pattern por escopo:** ocorrências do mesmo AP no mesmo contexto viram **um** finding com todas as linhas e a contagem (ex.: "19 queries"). Separe em findings distintos só quando o impacto for diferente.
4. **Localização exata:** `arquivo:linha`, `arquivo:inicio-fim` ou lista `arquivo:l1, l2, l3`. Caminhos relativos à raiz do projeto. Nunca "vários lugares".
5. **Evidência:** inclua o trecho de código relevante (1-5 linhas) e, quando a auditoria executou algo para provar (warning emitido, contagem de queries, resposta de endpoint), o resultado observado.
6. **Mudança de contrato:** marque `Contract change: YES` quando a correção alterar URL, status, corpo de resposta ou exigir credencial. Esses itens precisam de aprovação explícita.
7. **Contagens consistentes:** o Summary, o total final e a lista de findings precisam bater.
8. **Sem findings inventados:** se o projeto tiver menos problemas numa severidade, reporte o número real. Não "complete" categorias.

---

## Template

````markdown
================================
ARCHITECTURE AUDIT REPORT
================================
Project:  <nome da pasta do projeto>
Stack:    <linguagem + framework + versão>
Files:    <N> analyzed | ~<L> lines of code
Date:     <AAAA-MM-DD>
Architecture: <classificação A/B/C da Fase 1>

## Summary
CRITICAL: <n> | HIGH: <n> | MEDIUM: <n> | LOW: <n>

| ID | Severity | Anti-pattern | Location |
|----|----------|--------------|----------|
| F-01 | CRITICAL | <nome> (AP-xx) | <arquivo:linhas> |
| ...  | ...      | ...          | ...      |

## Findings

### F-01 [CRITICAL] <Nome do anti-pattern> (AP-xx)
File: <arquivo:linhas>
Principle: <princípio violado, do catálogo>
Description: <o que está errado, com contagem de ocorrências quando houver>
Evidence:
```<linguagem>
<trecho de 1-5 linhas>
```
<resultado observado, se houve prova em execução>
Impact: <consequência concreta: segurança, manutenção, performance, integridade>
Recommendation: <correção, citando o padrão do playbook (PT-xx)>
Contract change: <NO | YES: descreva a mudança visível ao cliente>

### F-02 [HIGH] ...

## Deprecated APIs
| API em uso | Ocorrências | Local | Equivalente moderno |
|------------|-------------|-------|---------------------|
| <api>      | <n>         | <arquivo:linhas> | <substituto> |
(ou: "Nenhuma API deprecated identificada para as versões em uso.")

## Positive Points
- <boas práticas já presentes que a refatoração deve preservar; ex.: "queries usam placeholders">
(opcional; omita a seção se não houver)

## Refactoring Plan (Phase 3 preview)
Strategy: <A) decomposição completa | B) evolução incremental | C) apenas correções de código>
Target structure: <resumo das pastas/camadas que serão criadas ou mantidas>
Contract changes requiring approval:
- <F-xx: mudança> (ou "Nenhuma")
Out of scope: <findings que não serão corrigidos e por quê, se houver>

================================
Total: <N> findings
================================
````

---

## Exemplo preenchido (trecho)

````markdown
================================
ARCHITECTURE AUDIT REPORT
================================
Project:  code-smells-project
Stack:    Python + Flask 3.1.1
Files:    4 analyzed | ~780 lines of code
Date:     2026-09-30
Architecture: A) Monolítica: 4 arquivos, sem separação real de camadas

## Summary
CRITICAL: 4 | HIGH: 2 | MEDIUM: 2 | LOW: 2

| ID | Severity | Anti-pattern | Location |
|----|----------|--------------|----------|
| F-01 | CRITICAL | SQL Injection (AP-01) | models.py:28, 48, 58, ... 291-297 |
| F-02 | CRITICAL | Credenciais hardcoded (AP-02) | app.py:7, controllers.py:289 |

## Findings

### F-01 [CRITICAL] SQL Injection (AP-01)
File: models.py:28, 48, 58, 68, 92, 110, 127, 140, 149, 155, 158, 164, 174, 188, 192, 220, 224, 280, 291-297
Principle: OWASP A03 Injection
Description: 19 queries montadas por concatenação de strings com valores vindos da requisição.
Evidence:
```python
cursor.execute("SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'")
```
Impact: permite contornar o login e ler ou alterar qualquer tabela.
Recommendation: parametrizar todas as queries (PT-01).
Contract change: NO

### F-04 [CRITICAL] Endpoint sensível sem autenticação (AP-05)
File: app.py:47-57, 59-78
Principle: OWASP A01 Broken Access Control
Description: /admin/reset-db apaga o banco e /admin/query executa SQL arbitrário, ambos sem autenticação.
Evidence:
```python
cursor.execute(query)   # query = dados.get("sql")
```
Impact: qualquer cliente lê as senhas ou destrói todos os dados.
Recommendation: remover /admin/query; proteger /admin/reset-db com require_auth(role="admin") (PT-05).
Contract change: YES: /admin/query deixa de existir; /admin/reset-db passa a exigir token (401 sem credencial).

...

================================
Total: 10 findings
================================
````

---

## Encerramento da Fase 2 (pergunta obrigatória)

Depois do relatório, imprima **exatamente** a pergunta abaixo e **pare**. Nenhum arquivo do projeto pode ser alterado antes de uma resposta afirmativa.

```
Phase 2 complete. Report saved to reports/audit-report.md.
Proceed with refactoring (Phase 3)? [y/n]
```

- `y` / `sim` / `yes`: segue para a Fase 3, aplicando as mudanças de contrato listadas.
- `n` / `não`: encerra sem modificar nada.
- Qualquer outra resposta (ex.: "sim, mas mantenha o /admin/query"): ajuste o plano conforme pedido, confirme o novo plano em uma frase e siga.
