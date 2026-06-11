from flask import Flask, render_template
from flask_cors import CORS
from routes import routes
from Database.database import init_db, ensure_new_today_view
from scheduler import create_scheduler

app = Flask(__name__)
CORS(app)
app.register_blueprint(routes)


@app.route("/")
def index():
    return render_template("index.html")


if __name__ == "__main__":
    init_db()
    ensure_new_today_view()

    scheduler = create_scheduler()
    scheduler.start()
    print("[app] Scheduler pornit — scraping zilnic la 07:00 Europe/Bucharest")

    try:
        app.run(debug=False, use_reloader=False)
    finally:
        scheduler.shutdown()
