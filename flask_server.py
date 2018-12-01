from flask import Flask, request, redirect, session
from flask_session import Session
from textblob import TextBlob
import pyrebase
import os
from censor_sound import censor_audio
from werkzeug.utils import secure_filename
from pydub import AudioSegment

app = Flask(__name__, static_url_path='', static_folder='html')
app.secret_key = 'topsecreteminemkey'
app.config['UPLOAD_FOLDER'] = 'uploads'

config = {
    "apiKey": "AIzaSyCr65SnH0QQsZZmMMaLWm4R_QObEC-5zwQ",
    "authDomain": "haven-80079.firebaseapp.com",
    "databaseURL": "https://haven-80079.firebaseio.com",
    "storageBucket": "haven-80079.appspot.com"
}
firebase = pyrebase.initialize_app(config)
auth = firebase.auth()
db = firebase.database()
storage = firebase.storage()

from clarifai.rest import ClarifaiApp
clarifai = ClarifaiApp(api_key='b7992789f9364353b08f6889a378ee74')
model = clarifai.models.get("general-v1.3")
moderate = clarifai.models.get("moderation")


def get_image_points(base64):
    result = model.predict_by_base64(base64)
    tags = ['outputs'][0]['data']['concepts']
    tags = [tag['name'] for tag in tags]
    positive = 'nature' in tags or 'animal' in tags
    result = moderate.predict_by_base64(base64)
    points = ['outputs'][0]['data']['concepts']
    points = [point['value'] for point in points if point['name'] == 'safe']
    points = int(points[0] * 4) + int(positive)
    return points, (tags[0], tags[1])


def get_text_points(text):
    blob = TextBlob(text)
    n = len(blob.sentences)
    points = 0
    for sentence in blob.sentences:
        points += sentence.sentiment.polarity
    return (points + n) / n


def get_audio_points(tmp_audio_file):
    return censor_audio(tmp_audio_file)


@app.route('/auth/register/', methods=['POST'])
def signup():
    email, password = request.form['email'], request.form['password']
    result = firebase.auth().create_user_with_email_and_password(email, password)
    print(result)
    return redirect('/')


@app.route('/auth/register/', methods=['GET'])
def register():
    if 'key' not in session:
        return app.send_static_file('register.html')
    else:
        return redirect('/')


@app.route('/auth/login/', methods=['POST'])
def signin():
    email, password = request.form['email'], request.form['password']
    result = firebase.auth().sign_in_with_email_and_password(email, password)
    session['key'] = result['idToken']
    session['email'] = email.replace("@", ".")
    return redirect('/')


@app.route('/auth/login/', methods=['GET'])
def login():
    if 'key' not in session:
        return app.send_static_file('login.html')
    else:
        return redirect('/')


@app.route('/auth/logout/', methods=['GET'])
def logout():
    if 'key' in session:
        del session['key']
    if 'email' in session:
        del session['email']
    return redirect('/')


@app.route('/', methods=['GET'])
def home():
    if 'key' not in session:
        return redirect("/auth/login")
    else:
        return app.send_static_file('index.html')


@app.route('/curr', methods=['GET'])
def curr():
    if 'key' in session:
        return session['key']
    else:
        return redirect('/auth/login')


@app.route('/postImage', methods=['POST'])
def postImage():
    request.form['image']


@app.route('/postAudio', methods=['POST'])
def postAudio():
    file = request.files['audio']
    path = os.path.join('uploads/', secure_filename(file.filename))
    file.save(path)

    sound = AudioSegment.from_file(path)
    sound.export(path + ".wav", format="wav")
    points = get_audio_points(path)
    sound = AudioSegment.from_file(path + "_clean.wav")
    path = path.replace(".wav", ".mp3")
    sound.export(path, format="mp3")

    folder = session['email'] + "." + path
    url = storage.child(folder).put(path, token=session['key'])
    os.remove(path)

    points = max(0, points)
    points += get_text_points(request.form['text'])

    if points > 2:
        db.child("posts").push({
            'email': session['email'],
            'audio': url,
            'text': request.form['text'],
            'points': points
        })
    else:
        return "Too negative!"


@app.route('/postText', methods=['POST'])
def postText():
    request.form['text']
