import speech_recognition as sr
import json
import wave
import os
import pickle
import numpy as np

profane = open("profane.txt").readlines()


def is_profane(word):
    for w in profane:
        if w.strip().lower() == word.lower():
            return True
    return False


def censor_audio(FILENAME):
    API_FILE = 'api-key.json'
    points = 5

    API_KEY = open(API_FILE).read()
    r = sr.Recognizer()
    with sr.AudioFile(f'{FILENAME}.wav') as source:
        re = wave.open(f'{FILENAME}.wav', 'r')
        wr = wave.open(f'{FILENAME}_clean.wav', 'w')
        wr.setnchannels(re.getnchannels())
        wr.setsampwidth(re.getsampwidth())
        fr = re.getframerate()
        wr.setframerate(fr)

        last = 0

        for i in range(1 + re.getnframes() // (fr * 59)):
            print("[+] Transcribing file...")
            if os.path.exists(f'{FILENAME}.pickle'):
                data = pickle.load(open(f'{FILENAME}.pickle', 'rb'))
            else:
                data = r.recognize_google_cloud(
                    audio_data=r.record(source, duration=59, offset=i*59),
                    credentials_json=API_KEY,
                    show_all=True)
                pickle.dump(data, open(f'{FILENAME}.pickle', 'wb'))
            if len(data.keys()) == 0:
                wr.writeframes(re.readframes(re.getnframes()))
                exit()

            print("[+] Looping through results...")
            for result in data['results']:
                for word in result['alternatives'][0]['words']:
                    start = float(word['startTime'][:-1])
                    end = float(word['endTime'][:-1])
                    nframes = int(fr * (end - start))

                    if start > last:
                        wr.writeframes(re.readframes(int(fr * (start - last))))

                    frames = re.readframes(nframes)
                    if not is_profane(word['word']):
                        wr.writeframes(frames)
                    else:
                        print("[+] Censoring...")
                        points -= 1
                        omega = np.pi * 2 * 440 / fr
                        xaxis = np.arange(nframes, dtype=np.float) * omega
                        ydata = 16000 * np.sin(xaxis)

                        ssignal = b''
                        for i in range(len(ydata)):
                            ssignal += wave.struct.pack('h', int(ydata[i]))

                        wr.writeframes(ssignal)

                    last = end

        if re.getnframes() > wr.getnframes():
            wr.writeframes(re.readframes(re.getnframes()))

        print("[+] All done! Closing files...")
        wr.close()
        re.close()

    return points
