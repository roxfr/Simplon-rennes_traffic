# Ajout d'import
import os
from flask import Flask, render_template, request, abort, g
import plotly.graph_objs as go
import plotly.express as px
import numpy as np
import tensorflow as tf
from keras.models import load_model
from src.get_data import GetData
from src.utils import create_figure, prediction_from_model 
 # Importation de l'extension Flask Monitoring Dashboard
import flask_monitoringdashboard as dashboard
# Importation du module logging pour la gestion des logs dans l'application
import logging
from logging.handlers import RotatingFileHandler
import warnings
from time import sleep, time
from functools import wraps


# Suppression des messages de dépréciation
warnings.filterwarnings("ignore", category=DeprecationWarning, module='keras')
# Réduire les messages de log de TensorFlow
tf.get_logger().setLevel('ERROR')

# Définition des seuils d'alerte
ALERT_THRESHOLD_RESPONSE_TIME = 2  # secondes
ALERT_THRESHOLD_ERROR_RATE = 0.05  # 5%

# Création d'un fichier log uniquement s'il n'existe pas encore
log_file_path = os.path.join(os.getcwd(), 'app.log')
if not os.path.isfile(log_file_path):
    open(log_file_path, 'w', encoding='utf-8').close()

# Configuration du logger
handler = RotatingFileHandler(log_file_path, maxBytes=10000, backupCount=1, encoding='utf-8')
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)


# Création de l'application Flask
app = Flask(__name__)

# Configuration du logger pour l'application
app.logger.setLevel(logging.INFO)
app.logger.addHandler(handler)

# Configuration du logger de Werkzeug pour ne pas émettre des logs à la console
logging.getLogger('werkzeug').setLevel(logging.ERROR)

# Configuration de l'application Flask pour utiliser le tableau de bord de surveillance
app.config['FLASK_MONITORINGDASHBOARD'] = {
    'ENABLE': True, # Activer le tableau de bord de surveillance
    'LOGGING': True, # Activer la journalisation des performances pour le tableau de bord
}
# Liaison du tableau de bord à l'application Flask
dashboard.bind(app)
# Accéder au tableau de bord => http://localhost:5000/dashboard

# Décorateur pour mesurer le temps de réponse des requêtes
def monitor_performance(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time()
        try:
            response = func(*args, **kwargs)
        finally:
            elapsed_time = time() - start_time
            if elapsed_time > ALERT_THRESHOLD_RESPONSE_TIME:
                app.logger.warning(f"Temps de réponse élevé : {elapsed_time:.2f} secondes, le seuil de {ALERT_THRESHOLD_RESPONSE_TIME} secondes est dépassé")
        return response
    return wrapper

# Middleware pour surveiller les erreurs
@app.before_request
def before_request():
    if not hasattr(g, 'error_count'):
        g.error_count = 0
    if not hasattr(g, 'total_requests'):
        g.total_requests = 0

@app.after_request
def after_request(response):
    g.total_requests += 1
    if response.status_code >= 500:
        g.error_count += 1
    
    # Calculer le taux d'erreurs
    if g.total_requests > 0:
        error_rate = g.error_count / g.total_requests
        if error_rate > ALERT_THRESHOLD_ERROR_RATE:
            app.logger.warning(f"Taux d'erreurs élevé : {error_rate:.2%}, seuil dépassé : {ALERT_THRESHOLD_ERROR_RATE:.2%}")
    
    return response

# Récupération des données avec gestion des erreurs
try:
    data_retriever = GetData(url="https://data.rennesmetropole.fr/api/explore/v2.1/catalog/datasets/etat-du-trafic-en-temps-reel/exports/json?lang=fr&timezone=Europe%2FBerlin&use_labels=true&delimiter=%3B")
    data = data_retriever()
    app.logger.info('Données récupérées avec succès')
except Exception as e:
    app.logger.error(f"Erreur lors de la récupération des données : {e}")

# Chargement du modèle avec gestion des erreurs
try:
    model = load_model('models/model.h5')
    app.logger.info('Modèle chargé avec succés')
except Exception as e:
    app.logger.error(f"Erreur lors du chargement du modèle : {e}")



# Route de test pour vérifier les logs
@app.route('/test_log')
def test_log():
    app.logger.info('Accés à la route /test_log')
    return 'Test de log réussi'

# Route pour simuler un ralentissement
@app.route('/slow')
@monitor_performance
def slow_route():
    sleep(3)  # Simule un délai de 3 secondes
    return "Cette route est trop lente !"

# Route pour tester une erreur serveur
@app.route('/error')
def error_route():
    # Simule une erreur serveur
    abort(500)

# Route principale
@app.route('/', methods=['GET', 'POST'])
def index():
    # Tentative de création de la figure et de conversion en JSON
    try:
        fig_map = create_figure(data)
        graph_json = fig_map.to_json()
        # Initialisation des variables de retour pour le template
        text_pred = None
        color_pred = None
        
        # POST
        if request.method == 'POST':
            app.logger.info('Requête POST reçue')
            # Récupération de l'heure sélectionnée dans le formulaire et ajout du .get
            selected_hour = request.form.get('hour')
            app.logger.info(f"Heure sélectionnée par l'utilisateur : {selected_hour}")
            
            # Prédiction à partir du modèle
            try:
                # Rajout de l'heure sélectionnée en paramètre du model
                cat_predict = prediction_from_model(model, selected_hour)
                # Dictionnaire de mappage pour la prédiction et la couleur
                # Rajout de l'heure sélectionnée par l'utilisateur
                color_pred_map = {
                    0: [f"Prédiction : Libre pour {selected_hour} h", "green"],
                    1: [f"Prédiction : Dense pour {selected_hour} h", "orange"],
                    2: [f"Prédiction : Bloqué pour {selected_hour} h", "red"]
                }
                # Mise à jour des variables de retour avec la prédiction
                text_pred, color_pred = color_pred_map.get(cat_predict, ["Prédiction inconnue", "gray"])
                app.logger.info(f"Résultat de la prédiction : {text_pred}")

            except Exception as e:
                # Enregistrer l'erreur dans les journaux
                app.logger.error(f"Erreur lors de la prédiction : {e}")
                text_pred, color_pred = "Erreur de prédiction", "gray"

            # Retourner le modèle avec les données de la figure et, le cas échéant, la prédiction
            # Remplacement de 'home.html' par 'index.htlm'
            return render_template('index.html',
                                   graph_json=graph_json,
                                   text_pred=text_pred,
                                   color_pred=color_pred)
        # GET
        else:
            app.logger.info('Requête GET reçue')
            return render_template('index.html', graph_json=graph_json)

    except Exception as e:
        # Enregistrer l'erreur dans les journaux
        app.logger.error(f"Une erreur s'est produite : {e}")
        # Afficher un message d'erreur générique à l'utilisateur
        return "Une erreur s'est produite lors du traitement de la demande. Veuillez réessayer plus tard.", 500


if __name__ == '__main__':
    app.run(debug=False)
