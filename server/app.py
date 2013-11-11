# coding=utf-8

"""
    Linked Tag Workld Server
    ------------------------

    A little LTW configuring server written in Flask.

    :copyright: (c) 2013 by Jon Lazaro.
"""

from flask import Flask, request, redirect, url_for, render_template

import os

# Flask app initialization
app = Flask(__name__)


# Controllers
@app.route("/")
def index():
    return redirect(url_for('configure'))

@app.route("/configure/")
def configure():
    return render_template('step0.html')

@app.route("/configure/rdfsource/", methods=['GET', 'POST'])
def rdfsource():
    if request.method == 'POST':
        app.logger.debug(request.form)
        return render_template('rdf_step1.html')
    else:
        return render_template('rdf_step1.html')

@app.route("/configure/nonrdfsource/", methods=['GET', 'POST'])
def nonrdfsource():
    if request.method == 'POST':
        return render_template('nonrdf_step1.html')
    else:
        return render_template('nonrdf_step1.html')


# Server launch
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)