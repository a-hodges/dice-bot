#!/usr/bin/env python3

import argparse

from flask import Flask

app = Flask(__name__)


@app.route("/")
def hello():
    return "Hello World!"

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

    app.run(
        host=host,
        port=args.port,
        debug=args.debug,
        use_reloader=args.reload,
    )
