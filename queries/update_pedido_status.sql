-- Atualiza o status de um pedido e define os responsáveis.
UPDATE PEDIDO
SET STATUS = %s, ANALISTA = %s, GERENTE = %s
WHERE IDPEDIDO = %s;
