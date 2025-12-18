from flask import Flask, render_template, redirect, url_for, session

app = Flask(__name__)

@app.route("/games")
def games():
    return render_template("games.html")