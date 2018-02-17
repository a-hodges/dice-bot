import discord
from discord.ext import commands

from .. import model as m


class BotError (Exception):
    pass


class NoCharacterError (BotError):
    pass


class ItemNotFoundError (BotError):
    def __init__(self, value=None):
        self.value = value


class Cog:
    def __init__(self, bot):
        self.bot = bot


def get_character(session, userid, server):
    '''
    Gets a character based on their user
    '''
    character = session.query(m.Character)\
        .filter(~m.Character.dm_character)\
        .filter_by(user=str(userid), server=str(server)).one_or_none()
    if character is None:
        raise NoCharacterError()
    return character


def sql_update(session, type, keys, values):
    '''
    Updates a sql object
    '''
    obj = session.query(type)\
        .filter_by(**keys).one_or_none()
    if obj is not None:
        for value in values:
            setattr(obj, value, values[value])
    else:
        values = values.copy()
        values.update(keys)
        obj = type(**values)
        session.add(obj)

    session.commit()

    return obj


async def send_pages(ctx, paginator):
    '''
    Displays a set of pages
    '''
    for page in paginator.pages:
        await send_embed(ctx, author=ctx.author, page)


def invalid_subcommand(ctx):
    message = 'Command "{} {}" is not found'.format(ctx.invoked_with, ctx.message.content.split()[1])
    return commands.CommandNotFound(message)


def strip_quotes(arg):
    '''
    Strips quotes from arguments
    '''
    if len(arg) >= 2 and arg.startswith('"') and arg.endswith('"'):
        arg = arg[1:-1]
    return arg


async def inspector(ctx, character, attr, desc=False):
    '''
    Inspects an attribute of a character
    [ctx] the command context
    [character] the name of the character to inspect or the character itself
    [attr] the attribute of the character to inspect
    [paginator] either desc_paginator or item_paginator
    Returns a Pages instance
    '''
    if isinstance(character, str):
        name = character
        character = ctx.session.query(m.Character)\
            .filter(~m.Character.dm_character)\
            .filter_by(name=name, server=str(ctx.guild.id)).one_or_none()
        if character is None:
            raise Exception('No character named {}'.format(name))
    else:
        name = character.name

    paginator = commands.Paginator(prefix='', suffix='')
    paginator.add_line("{}'s {}:".format(name, attr))
    for item in getattr(character, attr):
        head = str(item)
        if desc:
            head = '***{}***'.format(head)
        paginator.add_line(head)
        if desc and item.description:
            for line in item.description.splitlines():
                paginator.add_line(line)

    await send_pages(ctx, paginator)


async def send_embed(ctx, *, content=None, author=None, color=None, description=None, fields=[]):
    '''
    Creates and sends an embed
    '''
    embed = discord.Embed()
    if description is not None:
        embed.description = description
    if author is not None:
        embed.color = author.color
        icon_url = author.avatar_url_as(static_format='png')
        embed.set_author(name=author.nick, icon_url=icon_url)
    if color:
        embed.color = color
    if fields:
        for field in fields:
            embed.add_field(name=field[0], value=field[1], inline=field[2] if len(field) > 2 else False)
    await ctx.send(content=content, embed=embed)
