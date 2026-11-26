"""
Roda as consultas SQL e gera 2 graficos a partir do banco criado por etl.py.

Como rodar (depois do etl.py):
    python src/analise.py
"""

import sqlite3
from contextlib import closing
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # permite gerar figuras sem abrir janela
import matplotlib.pyplot as plt
import pandas as pd

BANCO = Path("data/simcosta.db")
SQL = Path("sql/consultas.sql")
SAIDA = Path("resultados")


def rodar_consultas(con):
    """Executa cada consulta do arquivo .sql e mostra o resultado."""
    consultas = [c.strip() for c in SQL.read_text(encoding="utf-8").split(";") if "SELECT" in c]
    for i, consulta in enumerate(consultas, start=1):
        print(f"\n--- Consulta {i} ---")
        print(pd.read_sql_query(consulta, con).to_string(index=False))


def grafico_serie_diaria(con):
    """Altura significativa media e maxima por dia."""
    d = pd.read_sql_query("SELECT * FROM resumo_diario", con, parse_dates=["dia"])
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(d["dia"], d["hsig_max_m"], label="Máxima do dia", color="tab:red", linewidth=0.8)
    ax.plot(d["dia"], d["hsig_media_m"], label="Média do dia", color="tab:blue", linewidth=1.2)
    ax.set_title("Altura significativa de onda por dia - SiMCosta RS-4 (Rio Grande, RS)")
    ax.set_ylabel("Hsig (m)")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(SAIDA / "hsig_diaria.png", dpi=150)
    plt.close(fig)


def grafico_histograma(con):
    """Distribuicao da altura significativa."""
    o = pd.read_sql_query("SELECT hsig_m FROM ondas", con)
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.hist(o["hsig_m"], bins=30, color="tab:blue", edgecolor="white")
    ax.set_title("Distribuição da altura significativa (Hsig)")
    ax.set_xlabel("Hsig (m)")
    ax.set_ylabel("Número de medições")
    fig.tight_layout()
    fig.savefig(SAIDA / "hsig_histograma.png", dpi=150)
    plt.close(fig)


def main():
    SAIDA.mkdir(exist_ok=True)
    with closing(sqlite3.connect(BANCO)) as con:
        rodar_consultas(con)
        grafico_serie_diaria(con)
        grafico_histograma(con)
        pd.read_sql_query("SELECT * FROM resumo_diario", con).to_csv(
            SAIDA / "resumo_diario.csv", index=False
        )
    print(f"\nGráficos e resumo salvos em {SAIDA}/")


if __name__ == "__main__":
    main()
