from flask import Flask
from chatbot import test

app = Flask(__name__)

@app.route("/")
def hello_world():
    return test()