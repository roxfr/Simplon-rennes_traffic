import pandas as pd
import requests


class GetData(object):
    def __init__(self, url) -> None:

        self.url = url
        # Récupère les données depuis l'URL et les convertit en JSON
        response = requests.get(self.url)
        self.data = response.json()

    def processing_one_point(self, data_dict: dict) -> pd.DataFrame:

        # Création d'un DataFrame temporaire à partir du dictionnaire de données
        # Correction de 'trafficstatus' en 'trafficstatus' (voir fichier en entrée : etat-du-trafic-en-temps-reel.json)
        temp = pd.DataFrame({
            key: [data_dict[key]] for key in ['datetime', 'trafficstatus', 'geo_point_2d', 'averagevehiclespeed', 'traveltime', 'trafficstatus']
        })
        # Renomme la colonne 'trafficstatus' en 'traffic'
        temp = temp.rename(columns={'trafficstatus': 'traffic'})
        # Extrait les coordonnées de latitude et longitude du champ 'geo_point_2d'
        temp['lat'] = temp.geo_point_2d.map(lambda x: x['lat']) # Correction de 'latitude' en 'lat'
        temp['lon'] = temp.geo_point_2d.map(lambda x: x['lon']) # Correction de 'longitude' en 'lon'
        # Supprime la colonne 'geo_point_2d' maintenant que les coordonnées sont extraites
        del temp['geo_point_2d']

        return temp

    def __call__(self) -> pd.DataFrame:

        # Initialise un DataFrame vide
        res_df = pd.DataFrame()

        # Traite chaque dictionnaire de données et concatène les DataFrames
        for data_dict in self.data:
            # Résolution du problème d'indentation
            temp_df = self.processing_one_point(data_dict)
            res_df = pd.concat([res_df, temp_df], ignore_index=True)

        # Filtre les données pour exclure les entrées où le statut de trafic est 'unknown'
        res_df = res_df[res_df.traffic != 'unknown'] # Manque le crochet fermé ']'

        return res_df
