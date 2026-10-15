def resetar_banco(db):
    """Ferramenta administrativa: esvazia todas as tabelas numa transação única."""
    with db:
        db.execute("DELETE FROM itens_pedido")
        db.execute("DELETE FROM pedidos")
        db.execute("DELETE FROM produtos")
        db.execute("DELETE FROM usuarios")
