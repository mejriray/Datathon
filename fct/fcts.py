import logging
import sys
import os

import pandas as pd
from sqlalchemy import create_engine
import openai

from llama_index import (
    load_index_from_storage,
    ServiceContext,
    StorageContext,
    SQLDatabase,
)
from llama_index.query_engine import (
    SQLAutoVectorQueryEngine,
    RetrieverQueryEngine,
)

from llama_index.tools.query_engine import QueryEngineTool
from llama_index.indices.vector_store.retrievers import (
    VectorIndexAutoRetriever,
)
from llama_index.vector_stores.types import MetadataInfo, VectorStoreInfo
from llama_index.indices.struct_store.sql_query import NLSQLTableQueryEngine
from llama_index.node_parser.simple import SimpleNodeParser
from llama_index.text_splitter import TokenTextSplitter
from llama_index.llms import OpenAI

# Set logging
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logging.getLogger().addHandler(logging.StreamHandler(stream=sys.stdout))

# Set API KEY
OPENAI_API_KEY = os.environ["OPEN_API_KEY"]
# Replace 'your-api-key' with your actual OpenAI API key
openai.api_key = OPENAI_API_KEY

def init_server():
    # define node parser and LLM
    chunk_size = 1024
    llm = OpenAI(temperature=0, model="gpt-3.5-turbo", streaming=True)
    service_context = ServiceContext.from_defaults(chunk_size=chunk_size, llm=llm)
    text_splitter = TokenTextSplitter(chunk_size=chunk_size)
    node_parser = SimpleNodeParser.from_defaults(text_splitter=text_splitter)
    
    # Rebuild storage context
    storage_context = StorageContext.from_defaults(persist_dir="renov_index")

    # Load index from the storage context
    index = load_index_from_storage(storage_context)

    # create DEP SQL table
    engine = create_engine("sqlite:///:memory:", future=True)
    table_name = "database_dpe"
    
    # Load database as pandas
    df = pd.read_parquet("data/database_dpe.parquet").head(10)
    
    # Store the dataframe into a new table called 'database_dpe' in the database
    df.to_sql(table_name, con=engine, if_exists='replace', index=False)

    # Build SQL Index
    sql_database = SQLDatabase(engine, include_tables=["database_dpe"])

    # Build SQL Query engine
    sql_query_engine = NLSQLTableQueryEngine(
        sql_database=sql_database,
        tables=["database_dpe"],
    )

    # Vector store info
    vector_store_info = VectorStoreInfo(
        content_info="articles dealing with aid for the energy renovation of housing",
        metadata_info=[
            MetadataInfo(
                name="title", type="str", description="The name of the website"
            ),
        ],
    )

    # Indicate which vector index to use
    vector_auto_retriever = VectorIndexAutoRetriever(
        index, vector_store_info=vector_store_info
    )

    retriever_query_engine = RetrieverQueryEngine.from_args(
        vector_auto_retriever, service_context=service_context
    )

    sql_tool = QueryEngineTool.from_defaults(
        query_engine=sql_query_engine,
        description=(
            "Useful for translating a natural language query into a SQL query over"
            " a table containing: database_dpe, containing the energy consumption"
            " performances of houses and appartments"
        ),
    )

    vector_tool = QueryEngineTool.from_defaults(
        query_engine=retriever_query_engine,
        description=(
            f"Useful for answering semantic questions about energy performances for housing renovation"
        ),
    )

    # Define SQLAutoVectorQueryEngine
    query_engine = SQLAutoVectorQueryEngine(
        sql_tool, vector_tool, service_context=service_context
    )

    return query_engine

def get_bot_response(query_engine, request):
    response = query_engine.query(request)
    return str(response)

