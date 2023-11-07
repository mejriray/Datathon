import logging
import sys
import yaml

import pandas as pd
from sqlalchemy import create_engine
import openai

from llama_index import (
    load_index_from_storage,
    ServiceContext,
    StorageContext,
)
from llama_index.node_parser.simple import SimpleNodeParser
from llama_index.text_splitter import TokenTextSplitter
from llama_index.llms import OpenAI

# Set logging
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logging.getLogger().addHandler(logging.StreamHandler(stream=sys.stdout))


def parse_credentials():
    with open("credentials.yml","r") as f:
        credentials = yaml.load(f)
    openai_api_key = credentials.get("open_api_key")
    return openai_api_key

# Set API KEY
OPENAI_API_KEY = parse_credentials()
openai.api_key = OPENAI_API_KEY

def init_server():
    # define node parser and LLM
    chunk_size = 540
    llm = OpenAI(temperature=0, model="gpt-3.5-turbo", streaming=True)
    service_context = ServiceContext.from_defaults(chunk_size=chunk_size, llm=llm)
    text_splitter = TokenTextSplitter(chunk_size=chunk_size)
    node_parser = SimpleNodeParser.from_defaults(text_splitter=text_splitter)
    
    # Rebuild storage context
    storage_context = StorageContext.from_defaults(persist_dir="renov_index")

    # Load index from the storage context
    index = load_index_from_storage(storage_context)

    # Use index to build query engine
    query_engine = index.as_query_engine()

    # Load database as pandas
    df = pd.read_parquet("data/database_dpe.parquet").head(10)

    return query_engine, df

def get_bot_response(query_engine, request):
    response = query_engine.query(request)
    return str(response)
