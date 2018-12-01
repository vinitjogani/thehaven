from monkeylearn import MonkeyLearn

PROFANITY = 'cl_KFXhoTdt'
SENTIMENT = 'cl_pi3C7JiL'


ml = MonkeyLearn('33af7af2df4a052507240b6b6e8727be2a3ddba5')


def predict(model, tweet):
    r = ml.classifiers.classify(model, [tweet]).body[0]
    return (r['classifications'][0]['tag_name'], r['classifications'][0]['confidence'])


tweet = input()
data = [tweet]


print(predict(PROFANITY, tweet))
print(predict(SENTIMENT, tweet))

# if profane and negative:
#     print("You're blocked!")
# else:
#     print("Thank you for being nice!")
