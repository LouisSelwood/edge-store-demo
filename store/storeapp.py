import os
import threading
import time
from datetime import datetime

import requests
from flask import Flask, render_template, redirect

app = Flask(__name__)

STORE_NAME = os.environ.get("STORE_NAME", "store-01")
CLOUD_URL = os.environ.get("CLOUD_URL",  "http://cloud:5001")

items = [
	{"name": "The Satanic Verses", "author": "Salmon Rushdie", "qty": 12},
	{"name": "Small Gods", "author": "Terry Pratchett", "qty": 12},
	{"name": "Men At Arms", "author": "Terry Pratchett", "qty": 12},
	{"name": "Reaper Man", "author": "Terry Pratchett", "qty": 12},
	{"name": "Moving Pictures", "author": "Terry Pratchett", "qty": 12},
	{"name": "Hard Times", "author": "Charles Dickens", "qty": 12},
	{"name": "Great Expectations", "author": "Charles Dickens", "qty": 12},
	{"name": "The Tale of Two Cities", "author": "Charles Dickens", "qty": 12},
	{"name": "Little Women", "author": "Louisa Alcott", "qty": 12},
	{"name": "Cannery Row", "author": "John Steinbeck", "qty": 12},
	{"name": "East of Eden", "author": "John Steinbeck", "qty": 12},
	{"name": "Winter of Our Discontent", "author": "John Steinbeck", "qty": 12},
	{"name": "A Short Stay In Hell", "author": "Stephen L Peck", "qty": 12},
]
lock = threading.Lock()
sales = []
stats = {"by_store": [], "by_book": []}
next_id = 1
cloud_up = False

def sync_loop():
	"""Every three seconds check the cloud then send any pending sales"""
	global cloud_up, stats
	while True:
		try: 
			requests.get(f"{CLOUD_URL}/health", timeout=2).raise_for_status()
			cloud_up = True
		except requests.RequestException:
			cloud_up = False
		
		if cloud_up:
			with lock:
				pending = [s for s in sales if not s["sent"]]
			for sale in pending:
				payload = {"store": sale["store"], "id": sale["id"],
						"item": sale["item"], "time": sale["time"]}
				try:
					requests.post(f"{CLOUD_URL}/sales", json=payload, timeout=2).raise_for_status()
					sale["sent"] = True
				except requests.RequestException:
					break
		try:
			stats = requests.get(f"{CLOUD_URL}/stats", timeout=2).json()
		except requests.RequestException as e:
			print("stats failed:", e, flush=True)
		time.sleep(3)

@app.route("/")
def home():
	with lock:
		pending = len([s for s in sales if not s["sent"]])
		recent = list(reversed(sales))[:10]
	return render_template("index.html", items=items, cloud_up=cloud_up, pending=pending, 
							recent=recent, store=STORE_NAME, stats=stats)

@app.route("/buy/<name>", methods=["POST"])
def buy(name):
	global next_id
	for item in items:
		if item["name"] == name and item["qty"] > 0:
			item["qty"] -= 1
			with lock:
				sales.append({"id":next_id, "store": STORE_NAME, "item": name, 
					"time": datetime.now().strftime("%H:%M:%S"), "sent": False})
				next_id += 1
			break
	return redirect("/")


@app.route("/health")
def health():
	return {"status": "ok"}


if __name__ == "__main__":
	threading.Thread(target=sync_loop, daemon=True).start()
	app.run(host="0.0.0.0", port=5000)



