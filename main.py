"""
Módulo principal da API FastAPI para o sistema de gestão de eventos.

Este módulo define os endpoints da API, os modelos de dados Pydantic para validação
e a lógica de negócio para interagir com o banco de dados PostgreSQL.
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, model_validator
import psycopg2
from database import get_db_connection
from utils import load_sql_query
from typing import Optional, List
from fastapi.middleware.cors import CORSMiddleware
from datetime import date, datetime
import re

# --- Inicialização da Aplicação FastAPI ---
app = FastAPI(
    title="API de Gestão de Eventos",
    description="API para gerenciar cadastros e pedidos de eventos, utilizando PostgreSQL e Psycopg2.",
    version="1.0.0"
)

# --- Middleware ---
# Habilita o Cross-Origin Resource Sharing (CORS) para permitir que o frontend
# (executando em uma origem diferente, ex: http://localhost:5173) faça requisições para esta API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],  # Permite todos os métodos HTTP (GET, POST, etc.).
    allow_headers=["*"],  # Permite todos os cabeçalhos.
)

# --- Modelos de Dados (Pydantic) ---
# Os modelos Pydantic são usados para definir a estrutura dos dados das requisições (JSON bodies),
# garantindo a tipagem e a validação automática dos dados de entrada.

class PedidoCreate(BaseModel):
    """Modelo para a criação de um novo pedido, recebido do frontend."""
    nomeeventoproposto: Optional[str] = None
    localproposto: Optional[str] = None
    datainicioproposto: Optional[date] = None
    datafimproposto: Optional[date] = None
    descricao: Optional[str] = None
    usuario: str

    @model_validator(mode='after')
    def check_dates(self):
        """Validador Pydantic para garantir a consistência das datas do pedido."""
        if self.datainicioproposto and self.datainicioproposto < date.today():
            raise ValueError('A data de início não pode ser no passado.')
        if self.datainicioproposto and self.datafimproposto and self.datafimproposto < self.datainicioproposto:
            raise ValueError('A data de fim deve ser após a data de início.')
        return self

class UsuarioCreate(BaseModel):
    """Modelo para a criação de um novo usuário, com validações complexas."""
    ndoc: str
    tipodoc: str
    email: EmailStr  # Utiliza o tipo EmailStr do Pydantic para validação automática de formato de e-mail.
    nome: Optional[str] = None
    datanasc: Optional[date] = None
    rg: Optional[str] = None
    razaosocial: Optional[str] = None

    @model_validator(mode='after')
    def check_fields(self):
        """
        Validador Pydantic que executa após a validação dos campos individuais.
        Ideal para regras de negócio que dependem de múltiplos campos.
        """
        tipodoc = self.tipodoc
        ndoc = self.ndoc
        nome = self.nome
        razaosocial = self.razaosocial
        rg = self.rg

        # 1. Validação do tipo de documento.
        if tipodoc not in ['CPF', 'CNPJ']:
            raise ValueError('Tipo de documento deve ser CPF ou CNPJ.')

        # 2. Validação do formato do documento e campos condicionais.
        digits_only_ndoc = re.sub(r'\D', '', ndoc)
        if tipodoc == 'CPF':
            if len(digits_only_ndoc) != 11:
                raise ValueError('CPF deve conter 11 dígitos.')
            if not nome:
                raise ValueError('Nome é obrigatório para CPF.')

            # Validação do RG (apenas para CPF).
            if rg:
                digits_only_rg = re.sub(r'\D', '', rg)
                if not (7 <= len(digits_only_rg) <= 9):
                    raise ValueError('RG deve conter entre 7 e 9 dígitos.')

        elif tipodoc == 'CNPJ':
            if len(digits_only_ndoc) != 14:
                raise ValueError('CNPJ deve conter 14 dígitos.')
            if not razaosocial:
                raise ValueError('Razão Social é obrigatória para CNPJ.')

        # 3. Validação da idade (mínimo de 18 anos).
        if self.datanasc:
            today = date.today()
            # Calcula a idade de forma precisa, considerando o dia e mês de aniversário.
            age = today.year - self.datanasc.year - ((today.month, today.day) < (self.datanasc.month, self.datanasc.day))
            if age < 18:
                raise ValueError('Usuário deve ter pelo menos 18 anos.')

        return self

class ItemCreate(BaseModel):
    """Modelo para a criação de um novo item de patrimônio."""
    nropatrimonio: str
    statusitem: Optional[str] = "Disponível"
    qualidade: Optional[str] = None
    tamanho: float
    tiporecursofisico: str
    armazem: Optional[str] = None

class RequisitoItem(BaseModel):
    id: str
    qtd: int

class RequisitosCreate(BaseModel):
    tipos_recurso: List[RequisitoItem] = []
    recursos_humanos: List[RequisitoItem] = []

class ItemFilter(BaseModel):
    """Modelo para os parâmetros de filtro da consulta de itens."""
    search: Optional[str] = None
    tiporecursofisico: Optional[str] = None
    statusitem: Optional[str] = None
    qualidade: Optional[str] = None
    armazem: Optional[str] = None

class EventoCreate(BaseModel):
    nome: str
    data_inicio: date
    data_fim: date
    local: str
    status: str = "Confirmado"
    id_pedido: str

class AlocacaoCreate(BaseModel):
    evento_nome: str
    evento_data: date
    item_id: str
    dia_entrada: date
    dia_saida: date

class PedidoStatusUpdate(BaseModel):
    status: str
    analista: str
    gerente: str

# --- Endpoints da API ---

# GET Endpoints (Leitura de Dados)
@app.get("/users", summary="Lista todos os usuários")
async def get_users():
    """Endpoint para obter uma lista de todos os usuários cadastrados."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        query = load_sql_query("get_all_users")
        cur.execute(query)
        users = cur.fetchall()
        cur.close()
        conn.close()
        # Formata a saída para um JSON mais legível.
        return [{"ndoc": user[0], "nome": user[1], "email": user[2]} for user in users]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch users: {e}")

@app.get("/analysts", summary="Lista todos os analistas")
async def get_analysts():
    """Endpoint para obter uma lista de todos os analistas."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        query = load_sql_query("get_all_analysts")
        cur.execute(query)
        analysts = cur.fetchall()
        cur.close()
        conn.close()
        return [{"cpf": analyst[0], "nome": analyst[1]} for analyst in analysts]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch analysts: {e}")

@app.get("/managers", summary="Lista todos os gerentes")
async def get_managers():
    """Endpoint para obter uma lista de todos os gerentes."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        query = load_sql_query("get_all_managers")
        cur.execute(query)
        managers = cur.fetchall()
        cur.close()
        return [{"cpf": manager[0], "nome": manager[1]} for manager in managers]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch managers: {e}")

# POST Endpoints (Criação de Dados)
@app.post("/pedidos", summary="Cria um novo pedido de evento")
async def create_pedido(pedido: PedidoCreate):
    """
    Cria um novo pedido, aplicando validações e gerando dados no servidor.
    - Valida a existência do usuário.
    - Atribui automaticamente um analista e um gerente com base na carga de trabalho.
    - Gera um ID único para o pedido no formato PED-{ANO}-{NNN}.
    - Define a data de submissão e o status inicial no backend.
    - Utiliza controle transacional (commit/rollback).
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # 1. Validação da existência do usuário.
        cur.execute("SELECT ndoc FROM USUARIO WHERE ndoc = %s", (pedido.usuario,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail=f"Usuário com documento '{pedido.usuario}' não encontrado.")

        # 2. Atribuição automática de Analista e Gerente.
        # Busca o analista com menos pedidos.
        query_analista = load_sql_query("get_analyst_min_orders")
        cur.execute(query_analista)
        analista_row = cur.fetchone()
        if not analista_row:
             raise HTTPException(status_code=500, detail="Não há analistas cadastrados para atribuir ao pedido.")
        analista_cpf = analista_row[0]

        # Busca o gerente com menos pedidos.
        query_gerente = load_sql_query("get_manager_min_orders")
        cur.execute(query_gerente)
        gerente_row = cur.fetchone()
        if not gerente_row:
             raise HTTPException(status_code=500, detail="Não há gerentes cadastrados para atribuir ao pedido.")
        gerente_cpf = gerente_row[0]

        # 3. Geração de dados pelo servidor.
        # Lógica para criar um ID sequencial por ano.
        current_year = datetime.now().year
        cur.execute(
            "SELECT IDPEDIDO FROM PEDIDO WHERE IDPEDIDO LIKE %s ORDER BY IDPEDIDO DESC LIMIT 1",
            (f"PED-{current_year}-%",)
        )
        last_id = cur.fetchone()

        if last_id:
            last_number = int(last_id[0].split('-')[-1])
            new_number = last_number + 1
        else:
            new_number = 1

        idpedido = f"PED-{current_year}-{new_number:03d}"
        datasubmissao = date.today()
        status = "Em Análise"

        # 4. Inserção no banco de dados.
        query = load_sql_query("insert_pedido")

        # Execução da query parametrizada para prevenir SQL Injection.
        cur.execute(query, (
            idpedido,
            pedido.nomeeventoproposto,
            status,
            pedido.localproposto,
            pedido.datainicioproposto,
            pedido.datafimproposto,
            datasubmissao,
            pedido.descricao,
            pedido.usuario,
            analista_cpf,
            gerente_cpf
        ))
        conn.commit()  # Confirma a transação.

        return {"message": "Pedido criado com sucesso!", "idpedido": idpedido}
    except (HTTPException, ValueError) as e:
        if conn:
            conn.rollback()  # Desfaz a transação em caso de erro de validação ou HTTP.
        if isinstance(e, ValueError):
            raise HTTPException(status_code=400, detail=str(e))
        raise e
    except Exception as e:
        if conn:
            conn.rollback()  # Desfaz a transação para qualquer outro erro.
        raise HTTPException(status_code=500, detail=f"Ocorreu um erro interno: {e}")
    finally:
        if conn:
            cur.close()
            conn.close()

@app.post("/usuarios", summary="Cria um novo usuário")
async def create_usuario(usuario: UsuarioCreate):
    """
    Cria um novo usuário, aplicando validações de dados e de unicidade.
    - As validações de formato (CPF, CNPJ, e-mail, idade) são feitas pelo Pydantic.
    - A validação de unicidade (documento e e-mail) é feita com consulta ao banco.
    - Utiliza controle transacional (commit/rollback).
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # 1. Validação de unicidade (conflito de dados).
        cur.execute("SELECT ndoc FROM USUARIO WHERE ndoc = %s", (usuario.ndoc,))
        if cur.fetchone():
            raise HTTPException(status_code=409, detail=f"Documento '{usuario.ndoc}' já cadastrado.")

        cur.execute("SELECT email FROM USUARIO WHERE email = %s", (str(usuario.email),))
        if cur.fetchone():
            raise HTTPException(status_code=409, detail=f"E-mail '{usuario.email}' já cadastrado.")

        # 2. Inserção no banco de dados.
        query = load_sql_query("insert_usuario")
        # 2. Inserção no banco de dados.
        query = load_sql_query("insert_usuario")

        cur.execute(query, (
            usuario.ndoc,
            usuario.tipodoc,
            str(usuario.email),
            usuario.nome,
            usuario.datanasc,
            usuario.rg,
            usuario.razaosocial
        ))
        conn.commit()

        return {"message": "Usuário cadastrado com sucesso!", "ndoc": usuario.ndoc}
    except HTTPException as e:
        if conn:
            conn.rollback()
        raise e
    except Exception as e:
        if conn:
            conn.rollback()
        # Captura erros de validação do Pydantic e outros erros inesperados.
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        if conn:
            cur.close()
            conn.close()

@app.post("/items", summary="Cadastra um novo item de patrimônio")
async def create_item(item: ItemCreate):
    """
    Cadastra um novo item físico no sistema.
    - Valida a existência do Tipo de Recurso e do Armazém.
    - Verifica a unicidade do Número de Patrimônio.
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # 1. Validação de chaves estrangeiras.
        cur.execute("SELECT IDTIPORECURSO FROM TIPORECURSOFISICO WHERE IDTIPORECURSO = %s", (item.tiporecursofisico,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail=f"Tipo de Recurso '{item.tiporecursofisico}' não encontrado.")

        if item.armazem:
            cur.execute("SELECT IDARMAZEM FROM ARMAZEM WHERE IDARMAZEM = %s", (item.armazem,))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail=f"Armazém '{item.armazem}' não encontrado.")

        # 2. Validação de unicidade.
        cur.execute("SELECT NROPATRIMONIO FROM ITEM WHERE NROPATRIMONIO = %s", (item.nropatrimonio,))
        if cur.fetchone():
            raise HTTPException(status_code=409, detail=f"Patrimônio '{item.nropatrimonio}' já cadastrado.")

        # 3. Inserção.
        query = load_sql_query("insert_item")
        cur.execute(query, (
            item.nropatrimonio,
            item.statusitem,
            item.qualidade,
            item.tamanho,
            item.tiporecursofisico,
            item.armazem
        ))
        conn.commit()

        return {"message": "Item cadastrado com sucesso!", "nropatrimonio": item.nropatrimonio}
    except HTTPException as e:
        if conn:
            conn.rollback()
        raise e
        raise HTTPException(status_code=500, detail=f"Erro ao cadastrar item: {e}")
    finally:
        if conn:
            cur.close()
            conn.close()

class ItemUpdate(BaseModel):
    statusitem: Optional[str] = None
    qualidade: Optional[str] = None
    tamanho: Optional[float] = None
    tiporecursofisico: Optional[str] = None
    armazem: Optional[str] = None

@app.put("/items/{nropatrimonio}", summary="Atualiza um item de patrimônio")
async def update_item(nropatrimonio: str, item: ItemUpdate):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Verifica se o item existe
        cur.execute("SELECT NROPATRIMONIO FROM ITEM WHERE NROPATRIMONIO = %s", (nropatrimonio,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Item não encontrado.")

        # Validações opcionais de FK se forem passadas
        if item.tiporecursofisico:
            cur.execute("SELECT IDTIPORECURSO FROM TIPORECURSOFISICO WHERE IDTIPORECURSO = %s", (item.tiporecursofisico,))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail=f"Tipo de Recurso '{item.tiporecursofisico}' não encontrado.")

        if item.armazem:
            cur.execute("SELECT IDARMAZEM FROM ARMAZEM WHERE IDARMAZEM = %s", (item.armazem,))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail=f"Armazém '{item.armazem}' não encontrado.")

        query = load_sql_query("update_item")
        cur.execute(query, (
            item.statusitem,
            item.qualidade,
            item.tamanho,
            item.tiporecursofisico,
            item.armazem,
            nropatrimonio
        ))
        conn.commit()
        return {"message": "Item atualizado com sucesso!"}
    except HTTPException as e:
        if conn: conn.rollback()
        raise e
    except Exception as e:
        if conn: conn.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao atualizar item: {e}")
    finally:
        if conn:
            cur.close()
            conn.close()

@app.delete("/items/{nropatrimonio}", summary="Remove um item de patrimônio")
async def delete_item(nropatrimonio: str):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Verifica se o item existe
        cur.execute("SELECT NROPATRIMONIO FROM ITEM WHERE NROPATRIMONIO = %s", (nropatrimonio,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Item não encontrado.")

        # Verifica se está alocado (opcional, mas recomendável para integridade referencial se não houver CASCADE)
        # Por simplicidade, assumimos que o banco retornará erro de integridade se estiver em uso.

        query = load_sql_query("delete_item")
        cur.execute(query, (nropatrimonio,))
        conn.commit()
        return {"message": "Item removido com sucesso!"}
    except psycopg2.IntegrityError:
        if conn: conn.rollback()
        raise HTTPException(status_code=409, detail="Não é possível excluir este item pois ele está vinculado a outros registros (ex: Alocações).")
    except HTTPException as e:
        if conn: conn.rollback()
        raise e
    except Exception as e:
        if conn: conn.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao excluir item: {e}")
    finally:
        if conn:
            cur.close()
            conn.close()

@app.get("/items", summary="Lista e filtra os itens do patrimônio")
async def get_items(
    search: Optional[str] = None,
    tiporecursofisico: Optional[str] = None,
    statusitem: Optional[str] = None,
    qualidade: Optional[str] = None,
    tamanho: Optional[str] = None,
    armazem: Optional[str] = None
):
    """
    Endpoint para consulta de itens com filtros dinâmicos.
    A query SQL é construída dinamicamente no backend com base nos parâmetros
    fornecidos pelo usuário, utilizando uma query base do arquivo `filter_items.sql`.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        base_query = load_sql_query("filter_items")

        params = []
        where_clauses = []

        # Adiciona cláusulas WHERE e parâmetros conforme os filtros são aplicados.
        if tiporecursofisico and tiporecursofisico != "all":
            where_clauses.append("trf.IDTIPORECURSO = %s")
            params.append(tiporecursofisico)
        if statusitem and statusitem != "all":
            where_clauses.append("i.STATUSITEM = %s")
            params.append(statusitem)
        if qualidade and qualidade != "all":
            where_clauses.append("i.QUALIDADE = %s")
            params.append(qualidade)
        if armazem and armazem != "all":
            where_clauses.append("a.IDARMAZEM = %s")
            params.append(armazem)
        if search:
            where_clauses.append("i.NROPATRIMONIO ILIKE %s")
            params.append(f"%{search}%")

        # Constrói a query final.
        if where_clauses:
            final_query = base_query + " WHERE " + " AND ".join(where_clauses)
        else:
            final_query = base_query

        cur.execute(final_query, tuple(params))
        items = cur.fetchall()
        cur.close()
        conn.close()

        # Mapeia o resultado da tupla para um dicionário JSON.
        result = []
        for item in items:
            result.append({
                "nropatrimonio": item[0],
                "statusitem": item[1],
                "qualidade": item[2],
                "tamanho": item[3],
                "tiporecursofisico": {"nome": item[4]},
                "armazem": {"idarmazem": item[5], "endereco": item[6]} if item[5] else None,
            })
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch items: {e}")

@app.get("/tipos-recurso", summary="Lista os tipos de recurso físico")
async def get_tipos_recurso():
    """Endpoint para obter os tipos de recursos físicos disponíveis para os filtros."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        query = load_sql_query("get_all_tiporecursofisico")
        cur.execute(query)
        tipos = cur.fetchall()
        cur.close()
        conn.close()
        return [{"idtiporecurso": tipo[0], "nome": tipo[1]} for tipo in tipos]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch resource types: {e}")

class TipoRecursoCreate(BaseModel):
    idtiporecurso: str
    nome: str

@app.post("/tipos-recurso", summary="Cria um novo tipo de recurso físico")
async def create_tipo_recurso(tipo: TipoRecursoCreate):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Check if exists
        cur.execute("SELECT IDTIPORECURSO FROM TIPORECURSOFISICO WHERE IDTIPORECURSO = %s", (tipo.idtiporecurso,))
        if cur.fetchone():
             raise HTTPException(status_code=409, detail=f"Tipo de recurso '{tipo.idtiporecurso}' já existe.")

        query = load_sql_query("insert_tiporecurso")
        cur.execute(query, (tipo.idtiporecurso, tipo.nome))
        conn.commit()
        return {"message": "Tipo de recurso criado com sucesso!"}
    except HTTPException as e:
        if conn: conn.rollback()
        raise e
    except Exception as e:
        if conn: conn.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao criar tipo de recurso: {e}")
    finally:
        if conn:
            cur.close()
            conn.close()

@app.delete("/tipos-recurso/{id}", summary="Remove um tipo de recurso físico")
async def delete_tipo_recurso(id: str):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Check if exists
        cur.execute("SELECT IDTIPORECURSO FROM TIPORECURSOFISICO WHERE IDTIPORECURSO = %s", (id,))
        if not cur.fetchone():
             raise HTTPException(status_code=404, detail="Tipo de recurso não encontrado.")

        query = load_sql_query("delete_tiporecurso")
        cur.execute(query, (id,))
        conn.commit()
        return {"message": "Tipo de recurso removido com sucesso!"}
    except psycopg2.IntegrityError:
        if conn: conn.rollback()
        raise HTTPException(status_code=409, detail="Não é possível excluir este tipo pois está em uso.")
    except HTTPException as e:
        if conn: conn.rollback()
        raise e
    except Exception as e:
        if conn: conn.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao excluir tipo de recurso: {e}")
    finally:
        if conn:
            cur.close()
            conn.close()

@app.get("/armazens", summary="Lista os armazéns")
async def get_armazens():
    """Endpoint para obter os armazéns disponíveis para os filtros."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        query = load_sql_query("get_all_armazem")
        cur.execute(query)
        armazens = cur.fetchall()
        cur.close()
        conn.close()
        return [{"idarmazem": armazem[0], "endereco": armazem[1]} for armazem in armazens]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch warehouses: {e}")

@app.post("/pedidos/{id_pedido}/requisitos", summary="Adiciona requisitos a um pedido")
async def add_requisitos(id_pedido: str, requisitos: RequisitosCreate):
    """
    Adiciona requisitos de recursos físicos e humanos a um pedido.
    - Cria automaticamente o Documento de Requisito se não existir.
    - Insere os itens nas tabelas DOC_TIPORECURSO e DOC_RH.
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # 1. Verifica se o pedido existe.
        cur.execute("SELECT IDPEDIDO FROM PEDIDO WHERE IDPEDIDO = %s", (id_pedido,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Pedido não encontrado.")

        # 2. Garante que o Documento de Requisito existe.
        query_doc = load_sql_query("insert_documento_requisito")
        cur.execute(query_doc, (id_pedido,))

        # O ID do documento é o próprio ID do pedido (relação 1:1 na PK)
        id_documento = id_pedido

        # 3. Insere Requisitos Físicos.
        query_tr = load_sql_query("insert_doc_tiporecurso")
        for item in requisitos.tipos_recurso:
            # Valida se o tipo existe
            cur.execute("SELECT IDTIPORECURSO FROM TIPORECURSOFISICO WHERE IDTIPORECURSO = %s", (item.id,))
            if not cur.fetchone():
                 raise HTTPException(status_code=404, detail=f"Tipo de Recurso '{item.id}' não encontrado.")

            try:
                cur.execute(query_tr, (id_documento, item.id, item.qtd))
            except psycopg2.IntegrityError:
                conn.rollback()
                raise HTTPException(status_code=409, detail=f"Requisito físico '{item.id}' já existe para este pedido.")

        # 4. Insere Requisitos Humanos.
        query_rh = load_sql_query("insert_doc_rh")
        for item in requisitos.recursos_humanos:
             # Valida se o RH existe
            cur.execute("SELECT NOMEPROFISSAO FROM RECURSOHUMANO WHERE NOMEPROFISSAO = %s", (item.id,))
            if not cur.fetchone():
                 raise HTTPException(status_code=404, detail=f"Profissão '{item.id}' não encontrada.")

            try:
                cur.execute(query_rh, (id_documento, item.id, item.qtd))
            except psycopg2.IntegrityError:
                conn.rollback()
                raise HTTPException(status_code=409, detail=f"Requisito humano '{item.id}' já existe para este pedido.")

        conn.commit()
        return {"message": "Requisitos adicionados com sucesso!"}

    except HTTPException as e:
        if conn:
            conn.rollback()
        raise e
    except Exception as e:
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao adicionar requisitos: {e}")
    finally:
        if conn:
            cur.close()
            conn.close()

@app.get("/pedidos/{id_pedido}/requisitos", summary="Lista os requisitos de um pedido")
async def get_requisitos(id_pedido: str):
    """
    Retorna a lista de requisitos físicos e humanos associados a um pedido.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Verifica se existe documento de requisito para o pedido
        cur.execute("SELECT PEDIDO FROM DOCUMENTODEREQUISITO WHERE PEDIDO = %s", (id_pedido,))
        if not cur.fetchone():
            return [] # Sem requisitos cadastrados

        # O ID do documento é o próprio ID do pedido
        id_documento = id_pedido

        query = load_sql_query("get_requisitos_por_documento")
        cur.execute(query, (id_documento, id_documento))
        rows = cur.fetchall()

        requisitos = []
        for row in rows:
            requisitos.append({
                "nome": row[0],
                "quantidade": row[1],
                "tipo": row[2]
            })

        return requisitos

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar requisitos: {e}")
    finally:
        if 'conn' in locals() and conn:
            cur.close()
            conn.close()

@app.delete("/pedidos/{id_pedido}/requisitos/fisico/{id_recurso}", summary="Remove um requisito físico de um pedido")
async def delete_requisito_fisico(id_pedido: str, id_recurso: str):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # O ID do documento é o próprio ID do pedido
        id_documento = id_pedido

        query = load_sql_query("delete_doc_tiporecurso")
        cur.execute(query, (id_documento, id_recurso))

        if cur.rowcount == 0:
             raise HTTPException(status_code=404, detail="Requisito não encontrado.")

        conn.commit()
        return {"message": "Requisito removido com sucesso!"}
    except HTTPException as e:
        if conn: conn.rollback()
        raise e
    except Exception as e:
        if conn: conn.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao remover requisito: {e}")
    finally:
        if conn:
            cur.close()
            conn.close()

@app.delete("/pedidos/{id_pedido}/requisitos/humano/{id_recurso}", summary="Remove um requisito humano de um pedido")
async def delete_requisito_humano(id_pedido: str, id_recurso: str):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # O ID do documento é o próprio ID do pedido
        id_documento = id_pedido

        query = load_sql_query("delete_doc_rh")
        cur.execute(query, (id_documento, id_recurso))

        if cur.rowcount == 0:
             raise HTTPException(status_code=404, detail="Requisito não encontrado.")

        conn.commit()
        return {"message": "Requisito removido com sucesso!"}
    except HTTPException as e:
        if conn: conn.rollback()
        raise e
    except Exception as e:
        if conn: conn.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao remover requisito: {e}")
    finally:
        if conn:
            cur.close()
            conn.close()

@app.get("/pedidos", summary="Lista pedidos com filtros")
async def get_pedidos(status: Optional[str] = None, usuario: Optional[str] = None):
    """
    Lista pedidos, opcionalmente filtrando por status ou usuário.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        base_query = load_sql_query("get_pedidos")

        params = []
        where_clauses = []

        if status:
            where_clauses.append("p.STATUS = %s")
            params.append(status)
        if usuario:
            where_clauses.append("p.USUARIO = %s")
            params.append(usuario)

        if where_clauses:
            final_query = base_query + " WHERE " + " AND ".join(where_clauses)
        else:
            final_query = base_query

        cur.execute(final_query, tuple(params))
        pedidos = cur.fetchall()

        result = []
        for p in pedidos:
            result.append({
                "idpedido": p[0],
                "nomeeventoproposto": p[1],
                "status": p[2],
                "localproposto": p[3],
                "datainicioproposto": p[4],
                "datafimproposto": p[5],
                "datasubmissao": p[6],
                "usuario_nome": p[7],
                "analista_nome": p[8],
                "gerente_nome": p[9],
                "descricao": p[10]
            })

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao listar pedidos: {e}")
    finally:
        if 'conn' in locals() and conn:
            cur.close()
            conn.close()

@app.patch("/pedidos/{id_pedido}/status", summary="Atualiza status do pedido")
async def update_pedido_status(id_pedido: str, status_update: PedidoStatusUpdate):
    """
    Atualiza o status de um pedido (ex: Aprovado, Recusado) e atribui os responsáveis.
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Valida existência dos responsáveis
        cur.execute("SELECT CPF FROM ANALISTA WHERE CPF = %s", (status_update.analista,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Analista não encontrado.")

        cur.execute("SELECT CPF FROM GERENTE WHERE CPF = %s", (status_update.gerente,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Gerente não encontrado.")

        query = load_sql_query("update_pedido_status")
        cur.execute(query, (status_update.status, status_update.analista, status_update.gerente, id_pedido))

        if cur.rowcount == 0:
             raise HTTPException(status_code=404, detail="Pedido não encontrado.")

        conn.commit()
        return {"message": "Status atualizado com sucesso!"}
    except HTTPException as e:
        if conn: conn.rollback()
        raise e
    except Exception as e:
        if conn: conn.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao atualizar status: {e}")
    finally:
        if conn:
            cur.close()
            conn.close()

@app.post("/eventos", summary="Cria um novo evento")
async def create_evento(evento: EventoCreate):
    """
    Cria um evento efetivo a partir de um pedido aprovado.
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Valida Pedido
        cur.execute("SELECT IDPEDIDO FROM PEDIDO WHERE IDPEDIDO = %s", (evento.id_pedido,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Pedido não encontrado.")

        query = load_sql_query("insert_evento")
        cur.execute(query, (
            evento.nome,
            evento.data_inicio,
            evento.data_fim,
            evento.status,
            evento.local,
            evento.id_pedido
        ))
        conn.commit()
        return {"message": "Evento criado com sucesso!"}
    except psycopg2.IntegrityError as e:
        if conn: conn.rollback()
        raise HTTPException(status_code=409, detail=f"Erro de integridade (Evento já existe?): {e}")
    except Exception as e:
        if conn: conn.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao criar evento: {e}")
    finally:
        if conn:
            cur.close()
            conn.close()

@app.post("/alocacoes", summary="Aloca um item a um evento")
async def create_alocacao(alocacao: AlocacaoCreate):
    """
    Aloca um item físico a um evento.
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Valida Evento
        cur.execute("SELECT NOMEEVENTOEFETIVO FROM EVENTO WHERE NOMEEVENTOEFETIVO = %s AND DATAINICIOEFETIVO = %s",
                    (alocacao.evento_nome, alocacao.evento_data))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Evento não encontrado.")

        # Valida Item
        cur.execute("SELECT NROPATRIMONIO FROM ITEM WHERE NROPATRIMONIO = %s", (alocacao.item_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Item não encontrado.")

        query = load_sql_query("insert_alocacao")
        cur.execute(query, (
            alocacao.evento_nome,
            alocacao.evento_data,
            alocacao.item_id,
            alocacao.dia_entrada,
            alocacao.dia_saida
        ))
        conn.commit()
        return {"message": "Item alocado com sucesso!"}
    except psycopg2.IntegrityError as e:
        if conn: conn.rollback()
        raise HTTPException(status_code=409, detail=f"Erro de alocação (Item já alocado?): {e}")
    except Exception as e:
        if conn: conn.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao alocar item: {e}")
    finally:
        if conn:
            cur.close()
            conn.close()
