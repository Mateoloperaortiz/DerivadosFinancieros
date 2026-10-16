"""Actualiza los datos crudos (TRM y series FRED) en data/raw.

Uso: uv run python scripts/fetch_data.py
Advertencia: al actualizar, la fecha de corte del informe cambia; revise la narrativa.
"""

from derivados.data import download_all

if __name__ == "__main__":
    download_all()
    print("Datos actualizados en data/raw")
