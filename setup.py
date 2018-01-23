#!/usr/bin/env python3

from setuptools import setup, find_packages

setup(name='Dice-bot',
      version='1.0.1',
      description='Discord bot for managing D&D characters',
      author='BHodges',
      url='https://github.com/b-hodges/dice-bot',
      scripts=['dicebot.py'],
      packages=find_packages())
