from flask import Flask, render_template, session, redirect, url_for, jsonify, request
from flask_socketio import SocketIO, emit
import threading
import pandas as pd
import plotly.express as px
from fct import fcts

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key' # For session management
socketio = SocketIO(app)

# Init server bot backend:
# Llama-index query engine to prompt queries to a specialized ChatGPT
# Database is a pandas dataframe containing average energy consumtions for housing in Normandie
QUERY_ENGINE, DATABASE = fcts.init_server() 

# In-memory task completion flag and message - in production, use a database or cache
task_status = {}
task_message = {}
task_data = {}

# TODO: move this to the right place
# Convert the Plotly figure to HTML
#fig_surface = px.histogram(DATABASE, x='surface_habitable_logement', nbins=50, title='Distribution de la surface habitable')
#plot_div = fig_surface.to_html(full_html=False)
df = pd.read_parquet("dfs/database_dpe.parquet")

def get_info():
    surface = int(request.form['surface'])
    dpe = request.form['dpe']
    department = request.form['department']
    property_type = request.form['property_type']
    energy_type = request.form['energy_type']
    build_year = request.form['build_year']
    glazing_type = request.form['glazing_type']
    data = {
        "type_batiment_dpe": property_type,
        "surface_habitable_logement": surface,
        "annee_construction_dpe": build_year,
        "type_vitrage": glazing_type,
        "type_energie_chauffage": energy_type,
        "code_departement_insee": department,
        "classe_dpe": dpe,
    }
    return data

def query_reno_bot(session_key, data):
    user_request = (
        """Tu es un conseiller expert en rénovation de logements.
        Je possède un bien possédant les caractéristiques suivantes:
        - type d'habitation: {}
        - surface habitable: {} m²
        - date de construction: {}
        - vitrage: {}
        - énergie chauffage: {}
        - département: {}
        - classe énergétique: {}
        N'hésite pas à demander des complément d'informations si besoin.
        Je souhaites que tu m'accompagnes dans le choix des meilleurs rénovations à effectuer pour réduire ma facture énergétique.
        Dresse une liste des rénovations possibles suivant les premières informations que je t'ai fournit.
        Dans un second temps liste les aides des financement disponibles et les conditions requises pour y avoir droit.
        Enfin suggère moi de te demander des détails sur un type de rénovation.
        """.format(
            data.get("type_batiment_dpe"),
            str(data.get("surface_habitable_logement")),
            str(data.get("annee_construction_dpe")),
            data.get("type_vitrage"),
            data.get("type_energie_chauffage"),
            data.get("code_departement_insee"),
            data.get("classe_dpe")
        )
    )
    
    print("User request:")
    print(user_request)

    # generated_response_string = fcts.get_bot_response(QUERY_ENGINE, user_request)
    generated_response_string = "tmp"
    print("generated_response_string:")
    print(generated_response_string)

    task_status[session_key] = True
    task_message[session_key] = generated_response_string
    task_data[session_key] = data


@app.route('/')
def index():
    return render_template("index.html")


@app.route("/init_chat", methods=['POST'])
def init_chat():
    data = get_info()
    print(data)
    session_key = 'task_done'  # Unique session key for task status
    session[session_key] = False
    task_status[session_key] = False
    task_message[session_key] = ""
    task_data[session_key] = {}
    # Start long-running task in a separate thread
    threading.Thread(target=query_reno_bot, args=(session_key, data)).start()
    return redirect(url_for('loading'))


@app.route('/loading')
def loading():
    # Render loading page
    return render_template('loading.html')


@app.route('/check_status')
def check_status():
    session_key = 'task_done'
    # Check if the task is complete and return the status
    is_done = task_status.get(session_key, False)
    return jsonify({'task_done': is_done})


@app.route('/renovaide_chat')
def renovaide_chat():
    session_key = 'task_done'
    initial_message = task_message.get(session_key, "")
    data = task_data.get(session_key, "")
    initial_message = initial_message.strip().replace("\n", "<br>")
    print("INITIAL MESSAGE:\n", initial_message)
    print("data1")
    print(data)
    plot_div = fcts.plot_bilan(df, data)
    return render_template('chat.html', initial_message=initial_message, plot_div=plot_div)


@socketio.on('user_input')
def handle_user_message(message):
    # Call chat gpt with user message and retrieve response
    bot_response = fcts.get_bot_response(QUERY_ENGINE, message)
    emit('bot_message', bot_response)


@socketio.on('user_connection')
def handle_user_connection(json):
    print('received user connection json: ' + str(json))


if __name__ == '__main__':
    print("Initialize server")
    # Use the development server if running in debug mode
    if app.debug:
        print("Debug mode start")
        socketio.run(app)
    else:
        # Use an ASGI server such as eventlet or gevent in production
        print("Prod mode start")
        socketio.run(app, host='0.0.0.0', port=5000)
