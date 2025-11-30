-- Query base para a consulta de itens.
-- O backend adiciona cláusulas WHERE dinamicamente a esta query
-- com base nos filtros aplicados pelo usuário.
SELECT
    i.NROPATRIMONIO,
    i.STATUSITEM,
    i.QUALIDADE,
    i.TAMANHO,
    trf.NOME AS TIPORECURSOFISICO_NOME,
    a.IDARMAZEM AS ARMAZEM_ID,
    a.ENDERECO AS ARMAZEM_ENDERECO
FROM ITEM i
JOIN TIPORECURSOFISICO trf ON i.TIPORECURSOFISICO = trf.IDTIPORECURSO
LEFT JOIN ARMAZEM a ON i.ARMAZEM = a.IDARMAZEM