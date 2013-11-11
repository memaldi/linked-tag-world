# coding=utf-8

"""
    Linked Tag Workld Server
    ------------------------

    A little LTW configuring server written in Flask.

    :copyright: (c) 2013 by Jon Lazaro.
"""

from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash

import os

# Flask app initialization
app = Flask(__name__)


# Controllers
@app.route("/")
def hello():
    return "Hello from Python!"


# Server launch
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)