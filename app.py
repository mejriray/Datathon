from flask import Flask, render_template, session, redirect, url_for, jsonify
from flask_socketio import SocketIO, emit
import threading
from fct import fcts

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key' # For session management
socketio = SocketIO(app)

QUERY_ENGINE = fcts.init_server() # Init server bot backend

# In-memory task completion flag and message - in production, use a database or cache
task_status = {}
task_message = {}


def query_reno_bot(session_key):
        request = (
            "Identifier les économies d'énergie et comment passer de la classe_dpe D à C"
            + " avec économie d'énergie pour mon appartement de 50 mètres carrés"
            + " dans le département 76. Elaborer une réponse avec les options d'aides financières disponibles."
        )

        generated_response_string = fcts.get_bot_response(QUERY_ENGINE, request)
        task_status[session_key] = True
        task_message[session_key] = generated_response_string


@app.route('/')
def index():
    return render_template("index.html")


@app.route("/init_chat", methods=['POST'])
def init_chat():
    session_key = 'task_done'  # Unique session key for task status
    session[session_key] = False
    task_status[session_key] = False
    task_message[session_key] = ""
    # Start long-running task in a separate thread
    threading.Thread(target=query_reno_bot, args=(session_key,)).start()
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


@socketio.on('user_message')
def handle_user_message(message):
    # Logic to handle user message goes here...
    print('received message: ' + message)
    # Simulate response from ChatGPT-like bot
    bot_response = "This is a response from the bot."
    emit('bot_message', bot_response)


@socketio.on('my event')
def handle_my_custom_event(json):
    print('received json: ' + str(json))

if __name__ == '__main__':
    # Use the development server if running in debug mode
    if app.debug:
        socketio.run(app)
    else:
        # Use an ASGI server such as eventlet or gevent in production
        socketio.run(app, host='0.0.0.0', port=5000)
