"""
Módulo com funções utilitárias para a API.
"""
import os

def load_sql_query(query_name: str) -> str:
    """
    Carrega uma query SQL de um arquivo .sql localizado no diretório 'api/queries'.

    Esta abordagem permite que as queries SQL sejam mantidas separadas da lógica
    da aplicação, em conformidade com o requisito do projeto de não usar ORMs
    e manter as declarações SQL explícitas.

    Args:
        query_name (str): O nome do arquivo da query (sem a extensão .sql).

    Returns:
        str: O conteúdo da query SQL como uma string.
    """
    query_path = os.path.join(os.path.dirname(__file__), "queries", f"{query_name}.sql")
    with open(query_path, "r") as f:
        return f.read()