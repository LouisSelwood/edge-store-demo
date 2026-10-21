import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)
DB = "/data/cloud.db"


def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sales (
                store TEXT,
                sale_id INTEGER,
                item TEXT,
                time TEXT,
                received_at TEXT,
                PRIMARY KEY (store, sale_id)
            )
        """)


@app.route("/")
def home():
    with db() as conn:
        rows = conn.execute("SELECT * FROM sales ORDER BY rowid DESC").fetchall()
    return render_template("index.html", sales=[dict(r) for r in rows])


@app.route("/health")
def health():
    return {"status": "ok"}

def share_by(column):
    # column is chosen by our own code, never by user input
    assert column in ("store", "item")
    with db() as conn:
        rows = conn.execute(f"""
            SELECT {column} AS name,
                   COUNT(*) AS sales,
                   ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS percent
            FROM sales
            GROUP BY {column}
            ORDER BY percent DESC
        """).fetchall()
    return [dict(r) for r in rows]


@app.route("/stats")
def stats():
    return jsonify({
        "by_store": share_by("store"),
        "by_book": share_by("item"),
    })
@app.route("/sales", methods=["POST"])
def receive_sale():
    sale = request.get_json(silent=True)
    if not sale or "item" not in sale or "store" not in sale or "id" not in sale:
        return {"error": "expected JSON with an id, an item and a store"}, 400
    received = datetime.now().strftime("%H:%M:%S")
    with db() as conn:
        cur = conn.execute(
            "INSERT OR IGNORE INTO sales (store, sale_id, item, time, received_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (sale["store"], sale["id"], sale["item"], sale.get("time"), received),
        )
        total = conn.execute("SELECT COUNT(*) FROM sales").fetchone()[0]
    if cur.rowcount == 0:
        return {"status": "duplicate ignored"}, 200
    return {"status": "ok", "total": total}, 201


@app.route("/sales")
def list_sales():
    store = request.args.get("store")
    with db() as conn:
        if store:
            rows = conn.execute("SELECT * FROM sales WHERE store = ?", (store,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM sales").fetchall()
    return jsonify([dict(r) for r in rows])


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
