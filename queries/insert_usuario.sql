-- Insere um novo registro na tabela USUARIO.
-- Os valores são substituídos por parâmetros no backend para segurança.
INSERT INTO USUARIO (NDOC, TIPODOC, EMAIL, NOME, DATANASC, RG, RAZAOSOCIAL)
VALUES ('{ndoc}', '{tipodoc}', '{email}', {nome}, {datanasc}, {rg}, {razaosocial});
