-- Insere um novo registro na tabela PEDIDO.
-- Os valores são substituídos por parâmetros no backend para segurança.
INSERT INTO PEDIDO (IDPEDIDO, NOMEEVENTOPROPOSTO, STATUS, LOCALPROPOSTO, DATAINICIOPROPOSTO, DATAFIMPROPOSTO, DATASUBMISSAO, DESCRICAO, USUARIO, ANALISTA, GERENTE)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
