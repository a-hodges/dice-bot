#!/usr/bin/env python3

import argparse

from flask import Flask, url_for, send_from_directory
from flask_sqlalchemy import SQLAlchemy, _QueryProperty
from sqlalchemy.orm.exc import NoResultFound

import model as m

app = Flask(__name__)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# Attach Database
db = SQLAlchemy(app)
db.Model = m.Base
# Ugly code to make Base.query work
m.Base.query_class = db.Query
m.Base.query = _QueryProperty(db)


def create_app(args):
    r"""
    Sets up app for use
    Adds database configuration
    """
    app.jinja_env.trim_blocks = True
    app.jinja_env.lstrip_blocks = True

    # setup Database
    app.config['SQLALCHEMY_DATABASE_URI'] = args.database
    db.create_all()

    # setup config values
    with app.app_context():
        # these settings are stored in the configuration table
        # values here are defaults (and should all be strings or null)
        # defaults will autopopulate the database when first initialized
        # when run subsequently, they will be populated from the database
        # only populated on startup, changes not applied until restart
        url = ('https://discordapp.com/oauth2/authorize' +
               '?client_id=%s&scope=bot&permissions=0')
        config = {
            'INVITE_URL': url,
            'CLIENT_ID': '',
        }
        # get Config values from database
        for name in config:
            try:
                key = m.Config.query.filter_by(name=name).one()
                config[name] = key.value
            except NoResultFound:
                key = m.Config(name=name, value=config[name])
                db.session.add(key)
                db.session.commit()


@app.route("/")
def hello():
    html = '''<!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Dice Bot Invite</title>
        <link rel="shortcut icon" href="{favicon}">
        <style>
        a {{
            display: inline-block;
            border: 3px outset grey;
            background-color: lightgrey;
            border-radius: 10px;
        }}
        a:active {{
            border-style: inset;
        }}
        </style>
    </head>
    <body>
        <h1>Dice Bot</h1>
        <p>Invite Bot:</p>
        <a href="{link}">
            <img src="{favicon}">
        </a>
    </body>
    </html>
    '''

    url = m.Config.query.filter_by(name='INVITE_URL').one().value
    id = m.Config.query.filter_by(name='CLIENT_ID').one().value

    html = html.format(
        favicon=url_for('favicon'),
        link=url % id,
    )
    return html


@app.route('/favicon.ico')
def favicon():
    r"""
    The favorites icon for the site
    """
    return send_from_directory(
        app.root_path,
        'dice-bot-icon.png',
        mimetype='image/png',
    )

if __name__ == '__main__':
    port = 80
    parser = argparse.ArgumentParser(
        description='Basic Server',
        epilog='The server runs locally on port %d if PORT is not specified.'
        % port)
    parser.add_argument(
        '-p, --port', dest='port', type=int,
        help='The port where the server will run')
    parser.add_argument(
        '-d, --database', dest='database', default='sqlite:///:memory:',
        help='The database url to be accessed')
    parser.add_argument(
        '--debug', dest='debug', action='store_true',
        help='run the server in debug mode')
    parser.add_argument(
        '--reload', dest='reload', action='store_true',
        help='reload on source update without restarting server (also debug)')
    args = parser.parse_args()
    if args.reload:
        args.debug = True

    if args.port is None:  # Private System
        args.port = port
        host = '127.0.0.1'
    else:  # Public System
        host = '0.0.0.0'

    if args.reload:
        app.config['TEMPLATES_AUTO_RELOAD'] = True

    create_app(args)

    app.run(
        host=host,
        port=args.port,
        debug=args.debug,
        use_reloader=args.reload,
    )
