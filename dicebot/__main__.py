#!/usr/bin/env python3

import os
import logging

try:
    from . import main
except SystemError:
    from __init__ import main

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main(os.environ['DB'])
