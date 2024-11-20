import os
from pathlib import Path
import shutil

from flask import Flask, request, flash, redirect, url_for, send_from_directory, render_template, make_response
from werkzeug.utils import secure_filename

from decks import AnkiDeck

UPLOAD_FOLDER = "./media/uploads"
DOWNLOAD_FOLDER = "./media/downloads"
ALLOWED_EXTENSIONS = {"csv", "xls", "xlsx", "png", "tif", "jpg"}
DEBUG = True
PORT = os.getenv("PORT")

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
    
    language = request.form.get("language")
    filename = secure_filename(file.filename)

    print(app.config["UPLOAD_FOLDER"], filename)
    fpath = Path.joinpath(Path(app.config["UPLOAD_FOLDER"]), filename)
    file.save(fpath)

    print(fpath)
    download = Path.joinpath(Path(app.config["DOWNLOAD_FOLDER"]), fpath.with_suffix(".xlsx").name)

    output =  app.config["decks"].process_image(fpath, language)

    output.to_excel(download)
    return redirect(url_for("download_file", name=Path(download).name))


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
    
    language = request.form.get("language")
    blank_backside = request.form.get("blank_backside") == "on"
    
    filename = secure_filename(file.filename)
    fpath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(fpath)
    
    output = app.config["decks"].process_excel(fpath, language, blank_backside)
    
    download = Path(app.config["DOWNLOAD_FOLDER"]).joinpath(Path(output).name)
    shutil.move(output, download)
    
    return redirect(url_for("download_file", name=Path(download).name))

@app.route("/api/v1/download")
def list_downloads():
    return ""

@app.route("/api/v1/download/<name>")
def download_file(name):
    return send_from_directory(app.config["DOWNLOAD_FOLDER"], name)


@app.route("/")
def upload():
    return render_template("upload.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=app.config["PORT"], debug=app.config["DEBUG"])
