import plotly.express as px
import numpy as np


def create_figure(data):

    fig_map = px.scatter_mapbox(
        data,
        title="Traffic en temps réel",
        color="traffic",  # Colonne pour la couleur des points
        lat="lat",        # Colonne pour la latitude des points
        lon="lon",        # Colonne pour la longitude des points
        color_discrete_map={'freeFlow': 'green', 'heavy': 'orange', 'congested': 'red'},  # Mappe les états de trafic aux couleurs
        zoom=10,          # Niveau de zoom de la carte + Rajout d'une virgule
        height=500,       # Hauteur de la figure
        mapbox_style="carto-positron"  # Style de la carte
    )
    
    return fig_map

def prediction_from_model(model, hour_to_predict):

    try:
        # Conversion de l'heure en entier
        hour_to_predict = int(hour_to_predict)
    except ValueError:
        raise ValueError("hour_to_predict doit être un entier valide entre 0 et 23")

    # Crée un tableau d'entrée avec 24 éléments, tous initialisés à 0
    input_pred = np.zeros(24)
    input_pred[hour_to_predict] = 1

    # Effectue la prédiction avec le modèle et trouve la catégorie avec la valeur maximale
    cat_predict = np.argmax(model.predict(np.array([input_pred])))

    return cat_predict
