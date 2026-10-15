API_VERSION = "1.0.0"

PAPEL_ADMIN = "admin"
PAPEL_CLIENTE = "cliente"

CATEGORIAS_VALIDAS = ["informatica", "moveis", "vestuario", "geral", "eletronicos", "livros"]
CATEGORIA_PADRAO = "geral"
NOME_PRODUTO_MIN = 2
NOME_PRODUTO_MAX = 200

STATUS_PENDENTE = "pendente"
STATUS_APROVADO = "aprovado"
STATUS_ENVIADO = "enviado"
STATUS_ENTREGUE = "entregue"
STATUS_CANCELADO = "cancelado"
STATUS_PEDIDO = [STATUS_PENDENTE, STATUS_APROVADO, STATUS_ENVIADO, STATUS_ENTREGUE, STATUS_CANCELADO]

# (faturamento acima de, percentual de desconto), da maior faixa para a menor
FAIXAS_DESCONTO = [(10000, 0.10), (5000, 0.05), (1000, 0.02)]
