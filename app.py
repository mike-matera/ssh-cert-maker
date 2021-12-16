import tempfile 
import subprocess
import pathlib
import zipfile 

from flask import Flask, render_template, request, send_file
from werkzeug.utils import redirect

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == "GET":
        return render_template('index.html')

    elif request.method == 'POST':

        username = request.form.get("username", None)
        realname = request.form.get("realname", None)
        if username is None or realname is None:
            return render_template('index.html', error="Invalid Form")

        username = username.strip()
        realname = realname.strip()
        if username == "" or realname == "":
            return render_template('index.html', error="User name and real name cannot be blank.")

        with tempfile.TemporaryDirectory() as temp:
            temppath = pathlib.Path(temp)

            subprocess.run(f"""ssh-keygen -t rsa -b 4096 -f {temppath / "id_rsa"} -N ''""", shell=True)
            subprocess.run(f"""ssh-keygen -s ./secrets/ca_key -n {username} -I "{realname}" {temppath / "id_rsa.pub"}""", shell=True)

            with zipfile.ZipFile(temppath / "keys.zip", 'w') as zip:
                zip.write(temppath / "id_rsa", arcname="id_rsa")
                zip.write(temppath / "id_rsa.pub", arcname="id_rsa.pub")
                zip.write(temppath / "id_rsa-cert.pub", arcname="id_rsa-cert.pub")

            return send_file(f"""{temppath / "keys.zip"}""")
