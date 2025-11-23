from minitel import Minitel
from minitel.ImageMinitel import ImageMinitel
from pydantic_settings import BaseSettings, SettingsConfigDict


from datetime import datetime, timedelta
from fastapi import FastAPI
from PIL import Image
import requests
import logging


logger = logging.getLogger()


class Settings(BaseSettings):
    app_title: str = "Spotify"
    spotify_client_id: str = "<missing spotify client id>"
    spotify_client_secret: str = "<missing spotify client secret>"

    model_config = SettingsConfigDict(env_file=".env")


spotify_token = None
current_track_id = None
current_album_id = None


settings = Settings()
app = FastAPI()


def get_spotify_headers(force=False):
    global spotify_token
    if force or not spotify_token or spotify_token["expire_at"] < datetime.now():
        request_body = {
            "grant_type": "client_credentials",
            "client_id": settings.spotify_client_id,
            "client_secret": settings.spotify_client_secret,
        }
        res = requests.post("https://accounts.spotify.com/api/token", data=request_body)

        if not res.ok:
            print(f"Spotify authorization error: {res.text}")
            res.raise_for_status()

        res_json = res.json()
        spotify_token = {
            "token": res_json["access_token"],
            "expire_at": datetime.now() + timedelta(seconds=res_json["expires_in"]),
        }
    return {"Authorization": f"Bearer {spotify_token['token']}"}


def remove_artwork():
    for i in range(2, 14):
        minitel.position(21, i)
        minitel.efface("finligne")


def change_artwork(album):
    global current_album_id
    smallest_image = None
    for image in album["images"]:
        if not smallest_image or smallest_image["width"] > image["width"]:
            smallest_image = image
    if not smallest_image:
        current_album_id = None
        return
    r = requests.get(smallest_image["url"], stream=True)
    r.raw.decode_content = True
    image = Image.open(r.raw)
    image = image.resize((36, 36), Image.Resampling.LANCZOS)

    image_minitel = ImageMinitel(minitel)
    try:
        image_minitel.importer(image)
    except Exception:
        logger.exception("Impossible d'importer l'image dans le minitel")
    image_minitel.envoyer(21, 2)
    current_album_id = album["id"]


def init_header():
    minitel.position(2, 3)
    minitel.taille(2, 2)
    minitel.envoyer("3615")
    minitel.position(2, 5)
    minitel.taille(2, 2)
    minitel.envoyer(settings.app_title)


def get_track_data(track_id):
    headers = get_spotify_headers()
    url = f"https://api.spotify.com/v1/tracks/{track_id}"
    res = requests.get(url, headers=headers)
    if res.status_code == 401:
        headers = get_spotify_headers(force=True)
        res = requests.get(url, headers=headers)
    res.raise_for_status()
    return res.json()


def change_track(track_id):
    global current_album_id
    global current_track_id
    if current_track_id == track_id:
        return
    track = get_track_data(track_id)
    if current_album_id != track["album"]["id"]:
        remove_artwork()
    remove_track_info()
    if current_album_id != track["album"]["id"]:
        change_artwork(track["album"])
    show_track_info(track)
    current_track_id = track["id"]


def remove_track_info():
    debut = 15
    for i in range(debut, debut + 10):
        minitel.position(2, i)
        minitel.efface("ligne")


def show_track_info(track):
    debut = 15
    lignes = [
        track["name"][i * 37 : (i + 1) * 37]
        for i in range(0, min(2, 1 + len(track["name"]) // 37))
    ]
    lignes.append(None)
    artistes_text = ", ".join(artist["name"] for artist in track["artists"])
    lignes.extend([artistes_text[i * 37 : (i + 1) * 37] for i in range(0, 2)])
    position = debut
    for ligne in lignes:
        if ligne is None:
            position += 1
        else:
            position += 2
            minitel.position(2, position)
            minitel.taille(1, 2)
            minitel.envoyer(ligne)


def show_play_pause():
    minitel.position(35, 19)
    minitel.efface("ligne")
    minitel.position(35, 20)
    minitel.efface("ligne")
    minitel.taille(2, 2)
    minitel.envoyer("▶")


def reset_minitel():
    global current_track_id
    minitel.deviner_vitesse()
    minitel.identifier()
    minitel.definir_vitesse(1200)
    minitel.definir_mode("VIDEOTEX")
    minitel.configurer_clavier(etendu=True, curseur=False, minuscule=True)
    minitel.echo(False)
    minitel.curseur(False)
    minitel.efface()

    init_header()

    if current_track_id:
        change_track(current_track_id)


minitel = Minitel.Minitel()

reset_minitel()


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.post("/reset_minitel")
def reset_minitel_api():
    reset_minitel()


@app.patch("/current_track/{track_id}")
def change_current_track(track_id: str):
    change_track(track_id)
