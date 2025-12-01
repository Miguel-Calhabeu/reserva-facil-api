-- Cria um Documento de Requisito para um Pedido, se não existir.
INSERT INTO DOCUMENTODEREQUISITO (PEDIDO, STATUS)
VALUES (%s, 'Pendente')
ON CONFLICT (PEDIDO) DO NOTHING;
