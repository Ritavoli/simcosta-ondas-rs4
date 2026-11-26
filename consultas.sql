-- Consultas SQL simples sobre o banco data/simcosta.db
-- Colunas de data/hora estao em texto no formato 'AAAA-MM-DD HH:MM:SS'

-- 1) As 10 maiores alturas significativas de onda
SELECT data_hora_local, hsig_m, hmax_m, tsig_s
FROM ondas
ORDER BY hsig_m DESC
LIMIT 10;

-- 2) Media mensal da altura significativa e do periodo
SELECT substr(data_hora_local, 1, 7) AS mes,
       COUNT(*)                      AS n_medicoes,
       ROUND(AVG(hsig_m), 2)         AS hsig_media_m,
       ROUND(MAX(hsig_m), 2)         AS hsig_max_m,
       ROUND(AVG(tsig_s), 1)         AS tsig_media_s
FROM ondas
GROUP BY mes
ORDER BY mes;

-- 3) Dias com ondas significativas de 2 m ou mais
SELECT dia, hsig_max_m, hmax_m
FROM resumo_diario
WHERE hsig_max_m >= 2
ORDER BY hsig_max_m DESC
LIMIT 15;

-- 4) Ondas e corrente superficial no mesmo horario (JOIN das duas tabelas)
SELECT o.data_hora_local,
       o.hsig_m,
       ROUND(c.velocidade_ms, 2) AS corrente_ms
FROM ondas AS o
JOIN correntes_superficie AS c
  ON o.data_hora_utc = c.data_hora_utc
ORDER BY o.hsig_m DESC
LIMIT 10;
