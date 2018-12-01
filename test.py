from monkeylearn import MonkeyLearn
from flask import Flask, request
from flask_cors import CORS
from sentiment_score import SentimentScore
from textblob import TextBlob
from profanity import profanity


app = Flask(__name__)
CORS(app)

ml = MonkeyLearn('33af7af2df4a052507240b6b6e8727be2a3ddba5')
PROFANITY = 'cl_KFXhoTdt'
SENTIMENT = 'cl_pi3C7JiL'

for line in open('rap.txt').readlines():
    blob = TextBlob(line)
    for sentence in blob.sentences:
        print(sentence.sentiment.polarity)
    print(profanity.contains_profanity(line))
    # x = SentimentScore(line).to_dict()
    print(line)


def predict_s(model, tweet):
    r = ml.classifiers.classify(model, [tweet]).body[0]
    return (r['classifications'][0]['tag_name'], r['classifications'][0]['confidence'])


@app.route('/', methods=['POST'])
def predict():
    tweet = request.form['tweet']

    x = SentimentScore(tweet).to_dict()

    # l1, c1 = predict_s(PROFANITY, tweet)
    # l2, c2 = predict_s(SENTIMENT, tweet)

    if x['neg'] > 0.6:  # l1 == 'profanity' or l2 == 'Negative':
        return '<span class="highlight">' + tweet + '</span>'
    else:
        return tweet

    return "Hello"
