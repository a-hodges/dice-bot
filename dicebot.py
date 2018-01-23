#!/usr/bin/env python3

import os
import logging

from dicebot import main

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main(os.environ['DB'])
