"""
ETL simples dos dados da boia SiMCosta RS-4 (Rio Grande, RS).

E (Extract):   le os arquivos CSV baixados do SiMCosta (ondas e correntes)
T (Transform): monta a data/hora, limpa valores faltantes e absurdos
L (Load):      grava tudo em um banco SQLite

Como rodar (na pasta do projeto):
    python src/etl.py
"""

import glob
import sqlite3
from contextlib import closing
from pathlib import Path

import pandas as pd

PASTA_DADOS = Path("data/raw")
BANCO = Path("data/simcosta.db")


# ---------------------------------------------------------------- EXTRACT
def ler_csv_simcosta(caminho):
    """Le um CSV do SiMCosta.

    As primeiras linhas do arquivo sao comentarios que comecam com '/'.
    Valores faltantes aparecem escritos como NULL.
    """
    return pd.read_csv(caminho, comment="/", na_values=["NULL"])


def achar_arquivo(padrao):
    """Procura em data/raw o arquivo que combina com o padrao (ex.: '*OCEAN*')."""
    arquivos = glob.glob(str(PASTA_DADOS / padrao))
    if not arquivos:
        raise FileNotFoundError(
            f"Nenhum arquivo '{padrao}' em {PASTA_DADOS}. "
            "Veja no README como baixar os dados."
        )
    return arquivos[0]


# -------------------------------------------------------------- TRANSFORM
def criar_data_hora(df):
    """Junta YEAR, MONTH, DAY, HOUR, MINUTE, SECOND em uma coluna de data/hora.

    Os dados originais estao em UTC. Criamos tambem a hora local (Brasilia).
    """
    partes = pd.DataFrame(
        {
            "year": df["YEAR"],
            "month": df["MONTH"],
            "day": df["DAY"],
            "hour": df["HOUR"],
            "minute": df["MINUTE"],
            "second": df["SECOND"],
        }
    )
    df = df.drop(columns=["YEAR", "MONTH", "DAY", "HOUR", "MINUTE", "SECOND"]).copy()
    df["data_hora_utc"] = pd.to_datetime(partes, utc=True)
    df["data_hora_local"] = df["data_hora_utc"].dt.tz_convert("America/Sao_Paulo")
    return df


def tratar_ondas(df):
    """Limpa os dados de ondas."""
    df = criar_data_hora(df)
    df = df.rename(
        columns={
            "Hsig": "hsig_m",  # altura significativa (m)
            "Hmax": "hmax_m",  # altura da maior onda (m)
            "Havg": "hmed_m",  # altura media (m)
            "Tsig": "tsig_s",  # periodo significativo (s)
            "Avg_Wv_Dir_N": "direcao_graus",  # direcao media, referencia norte verdadeiro
        }
    )

    # 1) remove linhas sem altura de onda (nao servem para a analise)
    df = df.dropna(subset=["hsig_m"])

    # 2) remove valores fisicamente impossiveis:
    #    altura positiva e a maior onda nao pode ser menor que a significativa
    df = df[(df["hsig_m"] > 0) & (df["hmax_m"] >= df["hsig_m"])]

    # 3) direcao deve ficar entre 0 e 360 graus
    df = df[(df["direcao_graus"] >= 0) & (df["direcao_graus"] <= 360)]

    # 4) remove linhas repetidas no mesmo horario
    df = df.drop_duplicates(subset="data_hora_utc")
    return df.sort_values("data_hora_utc").reset_index(drop=True)


def tratar_correntes(df):
    """Fica so com a camada mais proxima da superficie (celula 1, 0,71 m).

    O arquivo original tem uma coluna para cada celula do ADCP, o que
    deixaria a tabela enorme. Para este projeto basico usamos a celula 1.
    A velocidade vem em mm/s; convertemos para m/s.
    """
    df = criar_data_hora(df)
    saida = pd.DataFrame(
        {
            "data_hora_utc": df["data_hora_utc"],
            "data_hora_local": df["data_hora_local"],
            "velocidade_ms": df["Avg_Cell(001)_mag"] / 1000,
            "direcao_graus": df["Avg_Cell(001)_dir_n"],
        }
    )
    saida = saida.dropna(subset=["velocidade_ms"])
    saida = saida[saida["velocidade_ms"] >= 0]
    saida = saida.drop_duplicates(subset="data_hora_utc")
    return saida.sort_values("data_hora_utc").reset_index(drop=True)


def resumo_diario(ondas):
    """Calcula estatisticas por dia (hora local)."""
    d = ondas.copy()
    d["dia"] = d["data_hora_local"].dt.date
    resumo = d.groupby("dia").agg(
        n_medicoes=("hsig_m", "count"),
        hsig_media_m=("hsig_m", "mean"),
        hsig_max_m=("hsig_m", "max"),
        hmax_m=("hmax_m", "max"),
        tsig_media_s=("tsig_s", "mean"),
    )
    return resumo.round(2).reset_index()


# ------------------------------------------------------------------- LOAD
def preparar_para_sqlite(df):
    """SQLite nao guarda datas com fuso; gravamos como texto 'AAAA-MM-DD HH:MM:SS'."""
    df = df.copy()
    for col in ("data_hora_utc", "data_hora_local"):
        if col in df.columns:
            df[col] = df[col].dt.strftime("%Y-%m-%d %H:%M:%S")
    return df


def carregar(ondas, correntes, diario):
    BANCO.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(BANCO)) as con:
        preparar_para_sqlite(ondas).to_sql("ondas", con, if_exists="replace", index=False)
        preparar_para_sqlite(correntes).to_sql(
            "correntes_superficie", con, if_exists="replace", index=False
        )
        diario.astype({"dia": str}).to_sql("resumo_diario", con, if_exists="replace", index=False)
        con.commit()


def main():
    # Extract
    ondas_bruto = ler_csv_simcosta(achar_arquivo("*OCEAN*.csv"))
    corr_bruto = ler_csv_simcosta(achar_arquivo("*CURR*.csv"))
    print(f"Lidas {len(ondas_bruto)} linhas de ondas e {len(corr_bruto)} de correntes")

    # Transform
    ondas = tratar_ondas(ondas_bruto)
    correntes = tratar_correntes(corr_bruto)
    diario = resumo_diario(ondas)
    print(f"Depois da limpeza: {len(ondas)} linhas de ondas e {len(correntes)} de correntes")

    # Load
    carregar(ondas, correntes, diario)
    print(f"Banco gravado em {BANCO}")


if __name__ == "__main__":
    main()
