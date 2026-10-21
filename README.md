

Readme · MD
# Edge Store Demo
 
A small demo of an offline-first retail system. Several "stores" each run their own copy of a till app with their own stock. They keep selling even when the connection to head office (the "cloud") is lost, and they sync their sales when it comes back.
 
I built it to learn Linux, Bash and Docker hands-on, and to understand the idea behind edge computing: put the compute next to where the work happens, and treat the cloud as something that is allowed to disappear.
 
## What it does
 
- Three store containers (Bath, Bristol and London) run the same image, each with its own stock and its own web page.
- Clicking Buy reduces that store's stock straight away and queues a sale to send to the cloud.
- A background thread in each store checks the cloud every 3 seconds. If it is reachable, queued sales are sent; if not, they stay queued as pending.
- The cloud stores every sale in a SQLite database on a Docker volume, so the data survives container restarts.
- Each store also asks the cloud for sales statistics every 3 seconds (each store's share of total sales, and each book's share) and shows them on its main page.

 
## Run it
 
You need Docker with the Compose plugin.
 
```bash
git clone <this repo's URL>
cd edge-store-demo
docker compose up --build
```
 
Then open the stores and the cloud in the web browser:
 
| Bath store | http://localhost:5000 |
| Cloud | http://localhost:5001 |
| Bristol store | http://localhost:5002 |
| London store | http://localhost:5003 |
 
Stop with `Ctrl+C`, or `docker compose down` from another terminal. `docker compose down` keeps the cloud's data; `docker compose down -v` also deletes the volume for a clean start.
 
## Try the outage demo
 
1. Buy a few books in different stores. Each sale shows as pending briefly, then sent, and appears on the cloud page.
2. In a second terminal, take the cloud away:
```bash
   docker compose stop cloud
```
3. The stores' pages change to "unreachable". Keep buying. Stock still drops and sales pile up as pending, because a store doesn't need the cloud to work.
4. Bring the cloud back:
```bash
   docker compose start cloud
```
5. Within a few seconds the queues drain. Check everything arrived:
```bash
   curl localhost:5001/sales
   curl localhost:5001/stats
```
 
## How it works
 
**Stores** (`store/storeapp.py`) are Flask apps. Each reads its identity from environment variables, so one image serves every store:

| `STORE_NAME` | Name added to every sale | `store-01` |
| `CLOUD_URL` | Where to find the cloud | `http://cloud:5001` |
 
Inside the Compose network, containers reach each other by service name, which is why the URL is `http://cloud:5001`.
 
**Cloud** (`cloud/cloudapp.py`) is a Flask app with a SQLite database at `/data/cloud.db`, on the `cloud-data` Docker volume.
 
`GET /health`: Liveness check, used by the stores
`POST /sales`: Receive a sale as JSON (`store`, `id`, `item`, `time`)
`GET /sales`: List sales, optionally `?store=bath-01`
`GET /stats`: Each store's and each book's share of total sales
`GET /`: Simple page listing sales received
 
**Avoiding duplicates.** Every sale has an `id` that is unique within its store. The cloud's table has `PRIMARY KEY (store, sale_id)` and uses `INSERT OR IGNORE`, so a sale that is sent twice (for example, if a reply is lost during an outage) is only stored once. The store name is part of the key because every store numbers its sales from 1.
 
**Stats query.** A single query using a window function calculates each group's share:
 
```sql
SELECT store, COUNT(*) AS sales,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS percent
FROM sales
GROUP BY store;
```
 
## Project layout
 
```
edge-store-demo/
├── docker-compose.yml     # three stores + cloud, and the cloud-data volume
├── store/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── storeapp.py
│   └── templates/index.html
└── cloud/
    ├── Dockerfile
    ├── requirements.txt
    ├── cloudapp.py
    └── templates/index.html
```
 
## Known limitations and next steps
 
- **Store data is in memory.** The cloud persists to SQLite, but each store's stock and pending queue are Python variables, so restarting a store container resets them. Next step: give each store its own SQLite file on its own volume, with a `stock` table and a `pending_sales` table.
- **No authentication** between stores and cloud. A real system would authenticate each store.
- **Polling, not push.** Stores poll every 3 seconds. Fine for a demo; a real system would back off while the cloud is down.
- **Flask's development server** is used. A production setup would run behind a proper WSGI server such as gunicorn.
- **Stats count units, not money**, because items have no prices.
## What I used to learn the tools
 
I had little Linux or Docker experience before this, so I learned them alongside the build:
 
- **Linux:** installed Ubuntu in a VirtualBox VM and used it as my main environment. I worked through the early levels of [OverTheWire: Bandit](https://overthewire.org/wargames/bandit/), which taught me `ssh`, `find`, `grep` with regular expressions, `sort | uniq`, `file`, `strings` and file permissions with `chmod`. I also practised reading service status with `systemctl` and logs with `journalctl`.
- **Bash:** wrote small scripts covering variables, arguments, command substitution (`$(...)`) and checking disk space with `df`.
- **Docker:** started with `hello-world` and nginx, then wrote my own Dockerfile for a small Flask app (`FROM`, `WORKDIR`, `COPY`, `RUN`, `CMD`), learned images vs containers, port mapping and volumes, and then used Docker Compose to run several services on one network.
## Things that went wrong, and what they taught me
 
- A typo in `if __name__ == "__main__"` made a container exit immediately with empty logs. The lesson: when a container exits quietly, run `docker logs` and read the app's own code path.
- Flask's `render_template` couldn't find the page because the Dockerfile never copied the `templates/` folder into the image. The lesson: the container only contains what the Dockerfile puts in it.
- A misspelled `global` statement meant a background thread updated a local variable instead of the shared one, so the stats never appeared. Python raised no error, so I had to trace the data from the cloud's `curl` output through to the page.
- Dockerfile case matters on Linux: `DockerFile` is not `Dockerfile`.
 
Claude finished the response
