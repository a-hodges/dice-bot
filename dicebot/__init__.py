'''D&D manager bot for discord based RPGs

Note:
Any parameter value that has spaces in it needs to be wrapped in quotes "
Parameters marked with a * may omit the quotes
Certain commands are only usable by the @DM role
'''

import asyncio
from collections import OrderedDict
from contextlib import closing

import discord
from discord.ext import commands
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from equations import EquationError

import model as m
from util import NoCharacterError, ItemNotFoundError

bot = commands.Bot(
    command_prefix=';',
    description=__doc__,
    loop=asyncio.new_event_loop())
delete_emoji = '❌'


@bot.event
async def on_ready():
    '''
    Sets up the bot
    '''
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')
    game = 'Type {}help for command list'.format(bot.command_prefix)
    if bot.config['url']:
        game = bot.config['url'] + ' | ' + game
    await bot.change_presence(game=discord.Game(name=game))


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
async def on_message_delete(message):
    ...


@bot.event
async def on_raw_reaction_add(emoji: discord.Emoji, message_id: int, channel_id: int, user_id: int):
    if user_id != bot.user.id:
        if str(emoji) == delete_emoji:
            channel = bot.get_channel(channel_id)
            message = await channel.get_message(message_id)
            emoji = [r for r in message.reactions if str(r.emoji) == delete_emoji and r.me and r.count > 1]
            if emoji:
                await message.delete()


@bot.event
async def on_command_error(ctx, error: Exception):
    if (isinstance(error, commands.CommandInvokeError)):
        error = error.original

    if (isinstance(error, AttributeError) and
            ctx.guild is None and
            str(error) == "'NoneType' object has no attribute 'id'"):
        message = "This command can only be used in a server"

    elif isinstance(error, commands.CheckFailure):
        message = 'Error: You do not meet the requirements to use this command'
    elif isinstance(error, commands.CommandNotFound):
        if error.args:
            message = error.args[0]
        else:
            message = 'Error: command not found'
    elif isinstance(error, commands.BadArgument):
        message = '{}\nSee the help text for valid parameters'.format(error)
    elif isinstance(error, commands.MissingRequiredArgument):
        message = 'Missing parameter: {}\nSee the help text for valid parameters'.format(error.param)
    elif isinstance(error, commands.TooManyArguments):
        message = 'Too many parameters\nSee the help text for valid parameters'
    elif isinstance(error, NoCharacterError):
        message = 'User does not have a character'
    elif isinstance(error, ItemNotFoundError):
        if error.value:
            message = "Couldn't find requested item: `{}`".format(error.value)
        else:
            message = "Couldn't find requested item"
    elif isinstance(error, EquationError):
        if error.args:
            message = 'Invalid dice expression: `{}`'.format(error.args[0])
        else:
            message = 'Invalid dice expression'
    elif isinstance(error, ValueError):
        if error.args:
            message = 'Invalid parameter: {}'.format(error.args[0])
        else:
            message = 'Invalid parameter'
    else:
        message = 'Error: {}'.format(error)
        raise error

    message += '\n(click {} below to delete this message)'.format(delete_emoji)
    msg = await ctx.send(message)
    await msg.add_reaction(delete_emoji)


for extension in [
    'characters',
    'rolls',
    'resources',
    'variables',
    'inventory',
    'spells',
    'information',
]:
    bot.load_extension('cogs.' + extension)


def main(database: str):
    bot.config = OrderedDict([
        ('token', None),
        ('url', None),
    ])

    engine = create_engine(database)
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

            if False:
                arg = input('[{}] (default: {}): '.format(name, repr(key.value)))
                if arg:
                    key.value = arg
                    bot.config[name] = arg
                    session.commit()

    bot.run(bot.config['token'])
