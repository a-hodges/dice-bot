#!/usr/bin/env python3

import argparse
import asyncio
import logging
from collections import OrderedDict
from contextlib import closing

from discord.ext import commands
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import model as m
from util import NoCharacterError, ItemNotFoundError
from util.equations import EquationError

description = '''D&D manager bot for discord based RPGs

Note:
Any parameter value that has spaces in it needs to be wrapped in quotes "
unless it is the final parameter
'''
bot = commands.Bot(
    command_prefix='!',
    description=description,
    loop=asyncio.new_event_loop())


@bot.event
async def on_ready():
    '''
    Sets up the bot
    '''
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')


@bot.before_invoke
async def before_any_command(ctx):
    '''
    Set up database connection
    '''
    ctx.session = bot.Session()


@bot.after_invoke
async def after_any_command(ctx):
    '''
    Tear down database connection
    '''
    ctx.session.close()
    ctx.session = None


@bot.event
async def on_command_error(ctx, error):
    if (isinstance(error, commands.CommandInvokeError)):
        error = error.original

    if isinstance(error, commands.CommandNotFound):
        if error.args:
            await ctx.send(error.args[0])
        else:
            await ctx.send('Error: command not found')
    elif isinstance(error, commands.BadArgument):
        await ctx.send(
            '{}\n'.format(error) +
            'See the help text for valid parameters')
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(
            'Missing parameter: {}\n'.format(error.param) +
            'See the help text for valid parameters')
    elif isinstance(error, commands.TooManyArguments):
        await ctx.send(
            'Too many parameters\nSee the help text for valid parameters')
    elif isinstance(error, NoCharacterError):
        await ctx.send('User does not have a character')
    elif isinstance(error, ItemNotFoundError):
        if error.value:
            await ctx.send("Couldn't find requested item: `{}`".format(
                error.value))
        else:
            await ctx.send("Couldn't find requested item")
    elif isinstance(error, EquationError):
        if error.args:
            await ctx.send('Invalid dice expression: {}'.format(error.args[0]))
        else:
            await ctx.send('Invalid dice expression')
    elif isinstance(error, ValueError):
        if error.args:
            await ctx.send('Invalid parameter: {}'.format(error.args[0]))
        else:
            await ctx.send('Invalid parameter')
    else:
        await ctx.send('Error: {}'.format(error))
        raise error


for extension in [
    'characters',
    'rolls',
    'resources',
    'consts',
    'initiatives',
    'inventory',
    'spells',
]:
    bot.load_extension('cogs.' + extension)


def main(args):
    bot.config = OrderedDict([
        ('token', None),
    ])

    engine = create_engine(args.database)
    m.Base.metadata.create_all(engine)
    bot.Session = sessionmaker(bind=engine)
    with closing(bot.Session()) as session:
        for name in bot.config:
            key = session.query(m.Config).get(name)
            if key is not None:
                bot.config[name] = key.value
            else:
                key = m.Config(name=name, value=bot.config[name])
                session.add(key)
                session.commit()

            if args.initialize:
                arg = input('[{}] (default: {}): '.format(
                    name, repr(key.value)))
                if arg:
                    key.value = arg
                    bot.config[name] = arg
                    session.commit()

    bot.run(bot.config['token'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Discord D&D bot')
    parser.add_argument(
        'database', nargs='?', default='sqlite:///:memory:',
        help='The database url to be accessed')
    parser.add_argument(
        '-i, --initialize', dest='initialize', action='store_true',
        help='Allows for initialization of config values')
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    main(args)
