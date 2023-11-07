from flask import Flask, render_template, session, redirect, url_for, jsonify, request
from flask_socketio import SocketIO, emit
import threading
# from fct import fcts

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key' # For session management
socketio = SocketIO(app)

# QUERY_ENGINE = fcts.init_server() # Init server bot backend
DPE = ["A", "B", "C", "D", "E", "F"]

# In-memory task completion flag and message - in production, use a database or cache
task_status = {}
task_message = {}


def query_reno_bot(session_key, data):
            
    request1 = (
        "Identifier les économies d'énergie et comment passer de la classe_dpe " 
        + data.get("dpe") + " à " + data.get("dpe_objectif") + " avec économie d'énergie pour mon bien : " 
        + data.get("property_type") + " de " +  str(data.get("surface")) + " mètres carrés dans le département " 
        + data.get("department") + ". Elaborer une réponse avec les options d'aides financières disponibles."
    )
    print(data)

    # generated_response_string = fcts.get_bot_response(QUERY_ENGINE, request1)
    generated_response_string = """ Pour identifier les économies d'énergie et passer de la classe DPE D à C pour votre appartement de 50 mètres carrés dans le département 76, vous pouvez envisager les mesures suivantes :

1. Isolation : Assurez-vous que votre appartement est bien isolé, en particulier les murs, les fenêtres et le toit. Cela permettra de réduire les pertes de chaleur et de diminuer votre consommation d'énergie.

2. Chauffage : Optez pour un système de chauffage plus efficace et économe en énergie, tel qu'une chaudière à granulés. Ce type de chauffage peut vous permettre de réaliser des économies significatives sur votre facture énergétique.

3. Régulation de la température : Installez un thermostat programmable pour contrôler la température de votre appartement de manière plus précise et éviter les gaspillages d'énergie.       

4. Éclairage : Remplacez les ampoules traditionnelles par des ampoules LED, qui consomment moins d'énergie et ont une durée de vie plus longue.

5. Appareils électroménagers : Choisissez des appareils électroménagers économes en énergie, tels que des réfrigérateurs et des lave-linge de classe énergétique A+++. Cela vous permettra de réduire votre consommation d'électrici réduire votre consommation d'électricité.

En ce qui concerne les aides financières disponibles, vous pouvez envisager les options suivantes :

1. Crédit d'impôt : Vous pourriez être éligible à un crédit d'impôt pour la transition énergétique (CITE) pour certaines dépenses liées à l'amélioration de l'efficacité énergétique de votre logement. logement.

2. Éco-prêt à taux zéro : Vous pouvez également demander un éco-prêt à taux zéro pour financer les travaux de rénovation énergétique de votre appartement.

3. Aides de l'Agence nationale de l'habitat (ANAH) : L'ANAH propose des subventions pour les travaux de rénovation énergétique, en particulier pour les ménages à revenu modeste.

4. Certificats d'économie d'énergie (CEE) : Vous pouvez bénéficier de primes ou de bons d'achat en réalisant des travaux d'économie d'énergie et en obtenant des certificats d'économie d'énergie.                                                                                                                                                                                        bles dans votre département.

Il est recommandé de contacter les autorités locales, les agences de l'énergie ou les professionnels du secteur pour obtenir des informations plus précises sur les aides financières disponibles dans votre département."""
    task_status[session_key] = True
    # TODO: replace with generated_response_string
    task_message[session_key] = request1



@app.route('/')
def index():
    return render_template("index.html")


@app.route("/init_chat", methods=['POST'])
def init_chat():
    surface = int(request.form['surface'])
    dpe = request.form['dpe']
    department = request.form['department']
    property_type = request.form['property_type']
    #energy_type = request.form['energy_type']
    dpe_objectif = DPE[DPE.index(dpe) - 1]
    data = {
        "surface": surface,
        "dpe": dpe,
        "department": department,
        "property_type": property_type,
        #"energy_type": energy_type,
        "dpe_objectif": dpe_objectif,
    }
    print(data)
    session_key = 'task_done'  # Unique session key for task status
    session[session_key] = False
    task_status[session_key] = False
    task_message[session_key] = ""
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
    initial_message = initial_message.strip().replace("\n", "<br>")
    print("INITIAL MESSAGE:\n",initial_message)
    return render_template('chat.html', initial_message=initial_message)


@socketio.on('user_input')
def handle_user_message(message):
    # Logic to handle user message goes here...
    print('received message: ' + message)
    # Simulate response from ChatGPT-like bot
    # TODO: Call bot here to get response
    bot_response = "This is a response from the bot."
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
