API_VERSAO = "1.0.0"

CATEGORIAS_VALIDAS = ["informatica", "moveis", "vestuario", "geral", "eletronicos", "livros"]
CATEGORIA_PADRAO = "geral"
NOME_PRODUTO_MIN = 2
NOME_PRODUTO_MAX = 200

STATUS_PEDIDO = ["pendente", "aprovado", "enviado", "entregue", "cancelado"]
STATUS_PEDIDO_INICIAL = "pendente"

# Faixas de desconto do relatório de vendas: (faturamento acima de, taxa)
FAIXAS_DESCONTO = [(10000, 0.10), (5000, 0.05), (1000, 0.02)]

TIPO_USUARIO_PADRAO = "cliente"
TIPO_ADMIN = "admin"
