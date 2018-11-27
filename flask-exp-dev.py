# -*- coding: utf-8 -*-
"""
Created on Sat Oct 14 22:45:10 2017

@author: miha
"""

from flask import Flask, render_template, request, flash, url_for, session, redirect, g, Response
from flask_uploads import UploadSet, configure_uploads, UploadNotAllowed
import base64
import pandas as pd
import pandas_profiling
import io
from flask_caching import Cache
from io import StringIO
###############################################################################

# prepare flask 
app = Flask(__name__)   
app.secret_key = 'secret'

app.config.from_object(__name__)
#app.config.from_envvar('PHOTOLOG_SETTINGS', silent=True)

###############################################################################
# initialize data uploads settings
###############################################################################

## -----------------------------------------------------------
# upload settings
UPLOADS_DEFAULT_DEST = 'static/uploadedData/'
UPLOADS_DEFAULT_URL = 'http://localhost:5000/static/uploadedData/'

app.config['UPLOADS_DEFAULT_DEST'] = UPLOADS_DEFAULT_DEST
app.config['UPLOADS_DEFAULT_URL'] = UPLOADS_DEFAULT_URL

documents = UploadSet('documents', ('xls', 'xlsx', 'csv'))

configure_uploads(app, documents)

## -----------------------------------------------------------

cache = Cache(app, config={
    'CACHE_TYPE': 'redis',
    # Note that filesystem cache doesn't work on systems with ephemeral
    # filesystems like Heroku.
    'CACHE_TYPE': 'filesystem',
    'CACHE_DIR': 'cache-directory',

    # should be equal to maximum number of users on the app at a single time
    # higher numbers will store more data in the filesystem / redis cache
    'CACHE_THRESHOLD': 200
})

## -----------------------------------------------------------

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if not session.get('logged_in'):
        flash("Najprej se moraš prijaviti!")
        return render_template('login2.html')
    else:
        if request.method == 'POST' and 'document' in request.files:
            try:
                filename = documents.save(request.files['document'])

                flash("Datoteka naložena -> " + filename)

                #cache.set('last-session-filename', filename)
                session['laste-session-filename'] = filename
                get_dataframe(session['key'], filename)

            except UploadNotAllowed:
                flash("Napačen format datoteke. Datoteka mora biti .xls ali .xlsx.")

        return redirect(url_for('root'))

# saving/loading data from server-side cache
def get_dataframe(session_id, filename):

    @cache.memoize()
    def preprocess_data(session_id, filename):
        # expensive or user/session-unique data processing step goes here
        filename_full =UPLOADS_DEFAULT_DEST + 'documents/' + filename

        try:
            if 'csv' in filename:
                # Assume that the user uploaded a CSV file
                df = pd.read_csv(filename_full)
            elif 'xls' in filename:
                # Assume that the user uploaded an excel file
                df = pd.read_excel(filename_full)
        except Exception as e:
            print(e)
        flash("datoteka je bila prebrana in shranjena v cache")
        return df.to_json()

    #if not df_data.empty:
    #    cache.delete_memoized(preprocess_data, filename)

    return pd.read_json(preprocess_data(session_id, filename))

###############################################################################
# initialize login settings
###############################################################################

#login settings
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = '1234'

app.config['ADMIN_USERNAME'] = ADMIN_USERNAME
app.config['ADMIN_PASSWORD'] = ADMIN_PASSWORD

## -----------------------------------------------------------

@app.before_request
def before_request():
    if 'logged_in' not in session and request.endpoint != 'login':
        return redirect(url_for('login'))

@app.before_request
def login_handle():
    g.logged_in = bool(session.get('logged_in'))


@app.after_request
def add_header(r):
    """
    Add headers to both force latest IE rendering engine or Chrome Frame,
    and also to cache the rendered page for 10 minutes.
    """
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "0"
    r.headers['Cache-Control'] = 'public, max-age=0'
    return r


@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('logged_in'):
        flash("Si že logiran")
        return redirect(url_for('root'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if (username == app.config['ADMIN_USERNAME'] and
                password == app.config['ADMIN_PASSWORD']):
            session['logged_in'] = True

            session['key'] = username
            flash("Prijava je bila uspešna")

            return redirect(url_for('root'))
        else:
            flash("Napačno uporabniško ime ali geslo.")
    return render_template('login2.html')


@app.route('/logout')
def logout():
    if session.get('logged_in'):
        session['logged_in'] = False
        flash("Uspešno ste se odjavil.")
    else:
        flash("Nisi bil logrian.")
    return redirect(url_for('root'))

###############################################################################
## -----------------------------------------------------------
## main pages
## -----------------------------------------------------------
###############################################################################

@app.route('/')
def root():
    return render_template("blank.html")

@app.route("/load_data")
def load_data_page():
    if not session.get('logged_in'):
        flash("Najprej se moraš prijaviti!")
        return render_template('login2.html')
    else:
        return render_template('load_data.html',title = 'Naloži podatke (xlsx)')

@app.route("/data_profile")
def load_data_profile_page():
    df = get_dataframe(session['key'], session['laste-session-filename'])

    report = pandas_profiling.ProfileReport(df)
    report_filename =UPLOADS_DEFAULT_DEST + 'profiles/' + session['laste-session-filename'] + ".html"
    report.to_file(outputfile=report_filename)
    #return Response(report.html, mimetype="text/html")
    return render_template('blank.html', url_html=report_filename)

###############################################################################

if __name__ == '__main__':
	#print jdata
  app.run(debug=True)
  div_html = ''
  