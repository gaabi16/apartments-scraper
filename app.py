from flask import Flask, render_template
from routes import routes

app = Flask(__name__)
app.register_blueprint(routes)


@app.route("/")
def index():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True)
