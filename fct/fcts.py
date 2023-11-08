import logging
import sys
import yaml

import pandas as pd
from sqlalchemy import create_engine
import openai
import plotly.express as px

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
    #with open("credentials.yml","r") as f:
      #  credentials = yaml.load(f)
    #openai_api_key = credentials.get("open_api_key")
    return "openai_api_key"

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


def plot_bilan(df, data):
    surface = round(data.get("surface_habitable_logement")/10)*10
    filtered_df = df[
                    (df['code_departement_insee'] == data.get("code_departement_insee").lower()) 
                     & (df['type_batiment_dpe'] == data.get("type_batiment_dpe").lower()) 
                     & (df['annee_construction_dpe'] == int(data.get("annee_construction_dpe")))  
                     & (df['surface_habitable_logement'] == surface) 
                     & (df['type_energie_chauffage'] == data.get("type_energie_chauffage").lower()) 
                     & (df['type_vitrage'] == data.get("type_vitrage").lower())
                     ]
    if filtered_df.shape[0] < 5:
        filtered_df = df[
            (df['type_batiment_dpe'] == data.get("type_batiment_dpe").lower()) 
            & (df['annee_construction_dpe'] == int(data.get("annee_construction_dpe")))  
            & (df['surface_habitable_logement'] == surface) 
            & (df['type_energie_chauffage'] == data.get("type_energie_chauffage").lower()) 
            & (df['type_vitrage'] == data.get("type_vitrage").lower())
        ]
    df_grp = filtered_df.groupby(['classe_dpe'], as_index=False)['conso_energies_primaires_m2'].agg('mean')
    fig = px.bar(df_grp, x="conso_energies_primaires_m2", y="classe_dpe", title = "TITRE", orientation='h')
    fig.update_layout(
        {
            "plot_bgcolor": "rgba(0, 0, 0, 0)",
            "paper_bgcolor": "rgba(0, 0, 0, 0)",
        }
    )
    plot_div = fig.to_html(full_html=False)
    return plot_div