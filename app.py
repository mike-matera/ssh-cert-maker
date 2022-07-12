"""

    MAKE THIS CREATE ACCOUNTS LIKE JUPYTERHUB DOES


"""

import logging
import os
import pathlib
import re
import subprocess
import tempfile
import requests
import yaml
import flask 

import google.oauth2.credentials
import google_auth_oauthlib.flow
from googleapiclient.discovery import build

from canvasapi import Canvas

logging.basicConfig(level=logging.DEBUG)

canvas_cfg_file = pathlib.Path(pathlib.Path(os.environ['HOME']) / '.canvasapi')
canvas_cfg = None
canvas = None
logging.info(f"Loading canvas config file: {canvas_cfg_file}")
with open(canvas_cfg_file) as fh:
    canvas_cfg = yaml.load(fh, Loader=yaml.Loader)
canvas = Canvas(canvas_cfg['API_URL'], canvas_cfg['API_KEY'])

# This variable specifies the name of a file that contains the OAuth 2.0
# information for this application, including its client_id and client_secret.
CLIENT_SECRETS_FILE = "secrets/client_secret.json"

# This OAuth 2.0 access scope allows for full read/write access to the
# authenticated user's account and requires requests to use an SSL connection.
SCOPES = ['openid', 'https://www.googleapis.com/auth/userinfo.email', 'https://www.googleapis.com/auth/userinfo.profile']
API_VERSION = 'v2'

app = flask.Flask(__name__)
# Note: A secret key is included in the sample so that it works.
# If you use this code in your application, replace this with a truly secret
# key. See https://flask.palletsprojects.com/quickstart/#sessions.
app.secret_key = 'XXX REPLACE ME - this value is here as a placeholder.'


@app.route('/')
def index():
  if 'credentials' in flask.session:
      return flask.redirect(flask.url_for('make_key'))

  return flask.render_template('index.html')


@app.route('/authorize')
def authorize():
  # Create flow instance to manage the OAuth 2.0 Authorization Grant Flow steps.
  flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
      CLIENT_SECRETS_FILE, scopes=SCOPES)

  # The URI created here must exactly match one of the authorized redirect URIs
  # for the OAuth 2.0 client, which you configured in the API Console. If this
  # value doesn't match an authorized URI, you will get a 'redirect_uri_mismatch'
  # error.
  flow.redirect_uri = flask.url_for('oauth2callback', _external=True)

  authorization_url, state = flow.authorization_url(
      # Enable offline access so that you can refresh an access token without
      # re-prompting the user for permission. Recommended for web server apps.
      access_type='offline',
      # Enable incremental authorization. Recommended as a best practice.
      include_granted_scopes='false')

  # Store the state so the callback can verify the auth server response.
  flask.session['state'] = state

  return flask.redirect(authorization_url)


@app.route('/oauth2callback')
def oauth2callback():
  # Specify the state when creating the flow in the callback so that it can
  # verified in the authorization server response.
  state = flask.session['state']

  flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
      CLIENT_SECRETS_FILE, scopes=SCOPES, state=state)
  flow.redirect_uri = flask.url_for('oauth2callback', _external=True)

  # Use the authorization server's response to fetch the OAuth 2.0 tokens.
  authorization_response = flask.request.url
  flow.fetch_token(authorization_response=authorization_response)

  # Store credentials in the session.
  # ACTION ITEM: In a production app, you likely want to save these
  #              credentials in a persistent database instead.
  credentials = flow.credentials
  flask.session['credentials'] = credentials_to_dict(credentials)

  return flask.redirect(flask.url_for('make_key'))


@app.route('/revoke')
def revoke():
  if 'credentials' not in flask.session:
    return "Not authorized", 404 

  credentials = google.oauth2.credentials.Credentials(
    **flask.session['credentials'])
  del flask.session['credentials']

  revoke = requests.post('https://oauth2.googleapis.com/revoke',
      params={'token': credentials.token},
      headers = {'content-type': 'application/x-www-form-urlencoded'})

  status_code = getattr(revoke, 'status_code')
  if status_code == 200:
    return flask.render_template('index.html', message='Credentials successfully revoked.')
  else:
    return flask.render_template('index.html', message='An error occurred.')
   


@app.route('/clear')
def clear_credentials():
  if 'credentials' in flask.session:
    del flask.session['credentials']
  return flask.render_template('index.html', message='Credentials have been cleared.')


def credentials_to_dict(credentials):
  return {'token': credentials.token,
          'refresh_token': credentials.refresh_token,
          'token_uri': credentials.token_uri,
          'client_id': credentials.client_id,
          'client_secret': credentials.client_secret,
          'scopes': credentials.scopes}


@app.route('/key', methods=['GET', 'POST'])
def make_key():

    if 'credentials' not in flask.session:
        return flask.redirect('authorize')

    credentials = google.oauth2.credentials.Credentials(
        **flask.session['credentials'])

    service = build("oauth2", "v2", credentials=credentials)
    user_info = service.userinfo().get().execute()

    __blake = '0359051'
    __me = '0137431'
    id, domain = user_info['email'].split('@')
    if domain == 'cabrillo.edu':
        id = __me

    logging.debug(f"Google: {user_info}")

    courses = canvas.get_courses(enrollment_type='teacher', enrollment_state='active', include=['term'])
    for course in courses:
        m = re.search('^CIS-(\d+)', course.name)
        if m is not None:
            course_id = m.group(1)
            for student in course.get_users(include=['first_name', 'last_name', 'sis_user_id', 'email']):
                print("Test:", student)

    canvas_user = canvas.get_user(id, 'sis_login_id')
    logging.debug(canvas_user)

    if flask.request.method == "GET":
        return flask.render_template('keygen.html', usernames=user_info['email'])

    elif flask.request.method == 'POST':

        pubkey = flask.request.form.get("pubkey", None)

        with tempfile.TemporaryDirectory() as temp:
            temppath = pathlib.Path(temp)

            with open(temppath / 'id_rsa.pub', 'w') as fh:
                fh.write(pubkey)

            kg = subprocess.run(f"""ssh-keygen -s ./secrets/ca_key -n {user_info['email']} -I "{user_info['email']}" {temppath / "id_rsa.pub"}""", shell=True)
            if (kg.returncode != 0):
                return flask.render_template('keygen.html', usernames=user_info['email'], cert="Invalid public key!")

            with open(temppath / 'id_rsa-cert.pub') as fh:
                cert = fh.read()

        return flask.render_template('keygen.html', usernames=user_info['email'], cert=cert)

if __name__ == '__main__':
  # When running locally, disable OAuthlib's HTTPs verification.
  # ACTION ITEM for developers:
  #     When running in production *do not* leave this option enabled.
  os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

  # Specify a hostname and port that are set as a valid redirect URI
  # for your API project in the Google API Console.
  app.run('localhost', 9000, debug=True)


