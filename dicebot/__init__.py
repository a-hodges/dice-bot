'''D&D manager bot for discord based RPGs

Note:
Any parameter value that has spaces in it needs to be wrapped in quotes "
Parameters marked with a * may omit the quotes

Certain commands are only usable by administrators
'''

import re
import asyncio
from collections import OrderedDict
from contextlib import closing

import discord
from discord.ext import commands
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from equations import EquationError

from . import model as m
from .cogs import util


default_prefix = ';'


async def get_prefix(bot: commands.Bot, message: discord.Message):
    match = re.match(r'^({}\s+)'.format(re.escape(bot.user.mention)), message.content)
    if match:
        return match.group(1)
    with closing(bot.Session()) as session:
        item = session.query(m.Prefix).get(str(message.guild.id))
        prefix = default_prefix if item is None else item.prefix
    return prefix


bot = commands.Bot(
    command_prefix=get_prefix,
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
    game = 'Type `@{} help` for command list'.format(bot.user.name)
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


def is_my_delete_emoji(reaction):
    return reaction.me and reaction.count > 1 and str(reaction.emoji) == delete_emoji


@bot.event
async def on_raw_reaction_add(emoji: discord.PartialEmoji, message_id: int, channel_id: int, user_id: int):
    if user_id != bot.user.id and str(emoji) == delete_emoji:
        message = await bot.get_channel(channel_id).get_message(message_id)
        if discord.utils.find(is_my_delete_emoji, message.reactions):
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
    elif isinstance(error, util.NoCharacterError):
        message = 'User does not have a character'
    elif isinstance(error, util.ItemNotFoundError):
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


# ----#-   Commands


@bot.command(ignore_extra=False)
@commands.has_permissions(administrator=True)
async def setprefix(ctx, prefix: str = default_prefix):
    '''
    Sets the prefix for the server

    Parameters:
    [prefix] the new prefix for the server
        leave blank to reset
    '''
    guild_id = str(ctx.guild.id)
    item = ctx.session.query(m.Prefix).get(guild_id)
    if prefix == default_prefix:
        if item is not None:
            ctx.session.delete(item)
    else:
        if item is None:
            item = m.Prefix(server=guild_id)
            ctx.session.add(item)
        item.prefix = prefix
    try:
        ctx.session.commit()
    except IntegrityError:
        ctx.session.rollback()
        raise Exception('Could not change prefix, an unknown error occured')
    else:
        await ctx.send('Prefix changed to `{}`'.format(prefix))


prefix = __name__ + '.cogs.'
for extension in [
    'characters',
    'rolls',
    'resources',
    'variables',
    'inventory',
    'spells',
    'information',
]:
    bot.load_extension(prefix + extension)


# ----#-


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
