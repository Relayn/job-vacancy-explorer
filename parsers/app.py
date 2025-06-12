from flask import Flask, render_template
import sqlite3

app = Flask(__name__)

@app.route("/")
def show_vacancies():
    conn = sqlite3.connect("vacancies.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM vacancies ORDER BY published_at DESC LIMIT 50")
    vacancies = cur.fetchall()
    conn.close()
    return render_template("vacancies.html", vacancies=vacancies)

if __name__ == "__main__":
    app.run(debug=True)