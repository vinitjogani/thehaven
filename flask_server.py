from flask import Flask, request, redirect, session
from flask_session import Session
from textblob import TextBlob
import pyrebase
import base64
import os
from censor_sound import censor_audio, is_profane
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


def get_image_points(image):
    result = model.predict_by_filename(image)
    tags = result['outputs'][0]['data']['concepts']
    tags = [tag['name'] for tag in tags]
    positive = 'nature' in tags or 'animal' in tags
    result = moderate.predict_by_filename(image)
    points = result['outputs'][0]['data']['concepts']
    points = [point['value'] for point in points if point['name'] == 'safe']
    points = int(points[0] * 4) + int(positive)
    return points, (tags[0], tags[1])


def get_text_points(text):
    if text.strip() == '':
        return 5

    blob = TextBlob(text)
    n = len(blob.sentences)
    points = 0
    for sentence in blob.sentences:
        points += sentence.sentiment.polarity
        for word in sentence.split(' '):
            if is_profane(word):
                points -= 1
    return round((points + n) / (2*n) * 5)


def get_audio_points(tmp_audio_file):
    return max(0, censor_audio(tmp_audio_file))


@app.route('/auth/register/', methods=['POST'])
def signup():
    if 'key' not in session:
        email, password = request.form['email'], request.form['password']
        result = auth.create_user_with_email_and_password(email, password)
        db.child('users/' + result['localId'] +
                 '/fname').set(request.form['fname'], result['idToken'])
        db.child('users/' + result['localId'] +
                 '/lname').set(request.form['lname'], result['idToken'])
        return redirect('/')
    else:
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
    session['uid'] = result['localId']
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
    if 'uid' in session:
        del session['uid']
    return redirect('/auth/login')


@app.route('/', methods=['GET'])
def home():
    if 'key' not in session:
        return redirect("/auth/login")
    else:
        return app.send_static_file('index.html')


@app.route('/admin', methods=['GET'])
def admin():
    if 'key' in session and session['key'] == 'G8BhHlNHAXX7SGtbHSDFj7crPq62':
        return app.send_static_file('admin.html')


@app.route('/profile', methods=['GET'])
def profile():
    if 'key' not in session:
        return redirect("/auth/login")
    else:
        return app.send_static_file('profile.html')


@app.route('/curr', methods=['GET'])
def curr():
    if 'key' in session:
        return session['uid']
    else:
        return redirect('/auth/login')


@app.route('/password', methods=['POST'])
def password():
    if 'key' in session:
        auth.send_password_reset_email(
            auth.get_account_info(session['key'])['users'][0]['email'])
        return redirect('/?sta=Password')
    else:
        return redirect('/auth/login')


def upload_audio(file):
    path = os.path.join('uploads/', secure_filename(file.filename))
    file.save(path)

    sound = AudioSegment.from_file(path)
    sound.export(path + ".wav", format="wav")

    points = get_audio_points(path)

    sound = AudioSegment.from_file(path + "_clean.wav")
    path = path.replace(".wav", ".mp3")
    sound.export(path, format="mp3")

    folder = session['uid'] + "/" + path
    storage.child(folder).put(path, token=session['key'])
    url = storage.child(folder).get_url(session['key'])
    os.remove(path)

    return url, points


@app.route('/post', methods=['POST'])
def post():
    text, image, audio, tags = '', '', '', ()
    points = 5

    if not ('text' in request.form or 'image' in request.files or 'audio' in request.files):
        return redirect('/')

    if 'text' in request.form:
        text = request.form['text']
        points = min(get_text_points(text), points)

    if 'image' in request.files:
        image = request.files['image']
        path = 'uploads/' + secure_filename(image.filename)
        image.save(path)

        img_points, tags = get_image_points(path)
        points = min(img_points, points)
        storage.child(
            session['uid'] + "/" +
            secure_filename(image.filename)
        ).put(path, token=session['key'])
        image = storage.child(
            session['uid'] + "/" +
            secure_filename(image.filename)
        ).get_url(session['key'])

        tag1 = db.child("users/" + session['uid'] + "/" + tags[0]).get().val()
        tag2 = db.child("users/" + session['uid'] + "/" + tags[1]).get().val()
        if tag1 is None:
            tag1 = 1
        else:
            tag1 += 1
        if tag2 is None:
            tag2 = 1
        else:
            tag2 += 1
        db.child("users/" + session['uid'] + "/" +
                 tags[0]).set(tag1, token=session['key'])
        db.child("users/" + session['uid'] + "/" +
                 tags[1]).set(tag2, token=session['key'])

    if 'audio' in request.files:
        audio, audio_points = upload_audio(request.files['audio'])
        points = min(audio_points, points)

    new_point = db.child(
        "users/" + session['uid'] + "/point_history").push(points, token=session['key'])

    user_info = db.child(
        "users/" + session['uid']).get(token=session['key']).val()
    name = user_info['fname'] + ' ' + user_info['lname']

    if points > 2:
        db.child("posts").push({
            'uid': session['uid'],
            'audio': audio,
            'text': text,
            'image': image,
            'points': max(0, points),
            'author': name
        }, token=session['key'])

        return redirect("/?sta=Success&points="+str(points))
    else:
        return redirect("/?sta=Failure&points="+str(points))


@app.route('/comment', methods=['POST'])
def comment():
    if get_text_points(request.form['text']) > 2:
        user_info = db.child(
            "users/" + session['uid']).get(token=session['key']).val()
        name = user_info['fname'] + ' ' + user_info['lname']

        db.child('posts/' + request.form['id'] + '/comments').push({
            'uid': session['uid'],
            'author': name,
            'text': request.form['text']
        }, token=session['key'])
        return "OK"
    else:
        return "BE NICE"
