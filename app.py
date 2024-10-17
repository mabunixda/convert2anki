from flask import Flask, request, flash, redirect, url_for, send_from_directory, render_template
import os
from pathlib import Path

from werkzeug.utils import secure_filename

from decks import AnkiDeck

UPLOAD_FOLDER = "./media/uploads"
ALLOWED_EXTENSIONS = {"csv", "xls", "xlsx", "png", "tif", "jpg"}
DEBUG = True

app = Flask(__name__, static_folder="./templates/statics/")
app.config.from_object(__name__)

app.add_url_rule("/api/v1/download/<name>", endpoint="download_file", build_only=True)


@app.before_request
def init_request():
    app.config["decks"] = AnkiDeck()


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/api/v1/scan", methods=["POST"])
def scan_picture():
    if "file" not in request.files:
        flash("No file part")
        return redirect(request.url)
    file = request.files["file"]
    if file.filename == "":
        flash("No selected file")
        return redirect(request.url)
    if not allowed_file(file.filename):
        return None
    
    filename = secure_filename(file.filename)
    fpath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(fpath)
    output =  app.config["decks"].process_image(fpath)
    return render_template("image_converted.html", output=output)

@app.route("/api/v1/convert", methods=["POST"])
def convert_deckset():
    if "file" not in request.files:
        flash("No file part")
        return redirect(request.url)
    file = request.files["file"]
    if file.filename == "":
        flash("No selected file")
        return redirect(request.url)
    if not allowed_file(file.filename):
        return None
    
    filename = secure_filename(file.filename)
    fpath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(fpath)
    output = app.config["decks"].processExcel(fpath)
    return redirect(url_for("download_file", name=Path(output).name))

    


@app.route("/api/v1/download")
def list_downloads():
    return ""

@app.route("/api/v1/download/<name>")
def download_file(name):
    return send_from_directory(app.config["UPLOAD_FOLDER"], name)


@app.route("/")
def upload():
    return render_template("upload.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5005, debug=app.config["DEBUG"])
