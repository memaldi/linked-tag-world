# coding=utf-8

"""
    Linked Tag Workld Server
    ------------------------

    A little LTW configuring server written in Flask.

    :copyright: (c) 2013 by Jon Lazaro.
"""

from ltwserver import app
from flask import request, redirect, url_for, render_template


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