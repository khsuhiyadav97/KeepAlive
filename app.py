from flask import Flask

app = Flask(__name__)
broken = False

@app.route("/health")
def health():
    if broken:
        return {"status": "broken"}, 500
    return {"status": "ok"}

@app.route("/crash")
def crash():
    global broken
    broken = True
    return {"message": "service is now broken"}, 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)