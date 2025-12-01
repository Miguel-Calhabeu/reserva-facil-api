-- Insere uma nova alocação de item para evento.
INSERT INTO ALOCA (EVENTONOME, EVENTODATA, ITEM, DIAENTRADA, DIASAIDA)
VALUES (%s, %s, %s, %s, %s);
