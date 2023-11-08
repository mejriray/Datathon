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

list_dpe = ["A", "B", "C", "D", "E", "F", "G"]


def parse_credentials():
   # with open("credentials.yml","r") as f:
       # credentials = yaml.load(f)
   # openai_api_key = credentials.get("open_api_key")
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
    df = pd.read_parquet("data/database_dpe.parquet")
    
    return query_engine, df

def get_bot_response(query_engine, request):
    response = query_engine.query(request)
    return str(response)


def plot_bilan(df, data):
    data["surface_habitable_logement"] = round(
        data.get("surface_habitable_logement")/10)*10
    
    filter_cols = [
        "type_batiment_dpe",
        "code_departement_insee",
        "surface_habitable_logement",
        "annee_construction_dpe",
        "type_energie_chauffage",
        "type_vitrage",
    ]

    df_filtered = df.copy()
    for col in filter_cols:
        df_filtered_new = df_filtered[df_filtered[col] == data.get(col)]
        nb_class_dpe = len(df_filtered_new.classe_dpe.unique())
        if nb_class_dpe < 7:
            break
        else:
            df_filtered = df_filtered_new
    dfg = df_filtered.groupby(
        "classe_dpe").conso_energies_primaires_m2.mean().reset_index().sort_values(by='classe_dpe', ascending=False)

    fig = px.bar(dfg, x="conso_energies_primaires_m2",
                 y="classe_dpe", title="Concommations d'énergies primaires au m² par classe DPE",
                   orientation='h', template='plotly_dark')
    fig.update_layout(
        {
            "plot_bgcolor": "rgba(0, 0, 0, 0)",
            "paper_bgcolor": "rgba(0, 0, 0, 0)",
        }
    )
    plot_div = fig.to_html(full_html=False)

    #texte de bilan
    actual_dpe = data.get("classe_dpe")
    objectif_dpe = list_dpe[list_dpe.index(actual_dpe) - 1]
    surface = data["surface_habitable_logement"]
    actual_conso = dfg[dfg["classe_dpe"] == actual_dpe].conso_energies_primaires_m2.mean()
    objectif_conso = dfg[dfg["classe_dpe"] == objectif_dpe].conso_energies_primaires_m2.mean()
    price = 0.2276 #prix annuel par metre carre (énergivore)
    actual_cost = price * actual_conso * surface
    objectif_cost = price * objectif_conso * surface
    return plot_div, actual_dpe, objectif_dpe, actual_cost, objectif_cost


def plot_dpe_stats(df):
    # Convert the Plotly figure to HTML
    fig_classe_dpe = px.bar(
        df, x='classe_dpe', title='Répartition des classes DPE')

    fig_classe_dpe.update_layout(
        {
            "plot_bgcolor": "rgba(0, 0, 0, 0)",
            "paper_bgcolor": "rgba(0, 0, 0, 0)",
        }
    )
    plot_div = fig_classe_dpe.to_html(full_html=False)
    return plot_div
