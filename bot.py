#!/usr/bin/env python3

import argparse
import asyncio
import logging
import random
from collections import OrderedDict
from contextlib import contextmanager

import discord
from discord.ext import commands
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound

import equations
import model as m

description = '''D&D manager bot for discord based RPGs'''
bot = commands.Bot(
    command_prefix='!',
    description=description,
    loop=asyncio.new_event_loop())

config = OrderedDict([
    ('token', None),
])


@contextmanager
def sqlalchemy_context(Session, autocommit=False):
    session = Session(autocommit=autocommit)
    try:
        yield session
    finally:
        session.close()


def roll_dice(a, b):
    out = 0
    for _ in range(a):
        out += random.randint(1, b)
    return out


def great_weapon_fighting(a, b):
    out = 0
    for _ in range(a):
        n = random.randint(1, b)
        if n <= 2:
            n = random.randint(1, b)
        out += n
    return out

operations = equations.operations.copy()
operations['d'] = roll_dice
operations['D'] = roll_dice
operations['ad'] = lambda a, b: max(roll_dice(a, b), roll_dice(a, b))
operations['dd'] = lambda a, b: min(roll_dice(a, b), roll_dice(a, b))
operations['gwf'] = great_weapon_fighting
operations['>'] = max
operations['<'] = min
order_of_operations = [['d', 'D', 'ad', 'dd', 'gwf'], ['>', '<']]
order_of_operations.extend(equations.order_of_operations)


class BotError (Exception):
    pass


class NoCharacterError (BotError):
    pass


class NoResourceError (BotError):
    pass


def sql_update(session, type, keys, values):
    '''
    Updates a sql object
    '''
    try:
        obj = session.query(type)\
            .filter_by(**keys).one()
        for value in values:
            setattr(obj, value, values[value])
    except NoResultFound:
        values = values.copy()
        values.update(keys)
        obj = type(**values)
        session.add(obj)

    session.commit()


# ----#-   Commands


@bot.command()
async def iam(ctx, *, name: str):
    '''
    Associates user with a character
    It is highly encouraged to change your nickname to match the character
    A user can only be associated with 1 character at a time

    Parameters:
    [name] is he name of the character to associate
        to remove character association use !iam done
    '''
    if name.lower() == 'done':
        # remove character association
        with sqlalchemy_context(Session) as session:
            try:
                character = session.query(m.Character)\
                    .filter_by(user=ctx.author.id).one()
                character.user = None
                await ctx.send('{} is no longer playing as {}'.format(
                    ctx.author.mention, character.name))
            except NoResultFound:
                await ctx.send('{} does not have a character to remove'.format(
                    ctx.author.mention))

            session.commit()
    elif name:
        # associate character
        with sqlalchemy_context(Session) as session:
            try:
                character = session.query(m.Character)\
                    .filter_by(name=name).one()
            except NoResultFound:
                character = m.Character(name=name)
                session.add(character)

            if character.user is None:
                character.user = ctx.author.id
                try:
                    session.commit()
                    await ctx.send('{} is {}'.format(
                        ctx.author.mention, character.name))
                except IntegrityError:
                    await ctx.send(
                        'You are already using a different character')
                    raise
            else:
                await ctx.send('Someone else is using {}'.format(
                    character.name))
    else:
        # error
        await ctx.send('No character name given')


@bot.command()
async def whois(ctx, member: discord.Member):
    '''
    Retrieves character information for a user

    Parameters:
    [user] should be a user on this channel
    '''
    if member:
        # whois
        with sqlalchemy_context(Session) as session:
            try:
                character = session.query(m.Character)\
                    .filter_by(user=member.id).one()
            except NoResultFound:
                character = None

            if character:
                text = '{} is {}'.format(member.mention, character.name)
                await ctx.send(text)
            else:
                await ctx.send('User has no character')
    else:
        # error
        await ctx.send('No one was mentioned')


@bot.group(invoke_without_command=True)
async def roll(ctx, *, expression: str):
    '''
    Rolls dice

    Parameters:
    [expression] standard dice notation specifying what to roll
    
    *Everything past here may change*
    
    There are special operators for advantage and disadvantage rolls:
    "ad" for advantage, "dd" for disadvantage
    So, use "1ad20" for advantage or "1dd20" for disadvantage
    
    There is also a special 'great weapon fighting' operator
    which rerolls a 1 or 2, i.e. "2gwf6+5"
    '''
    if expression:
        roll = equations.solve(expression, operations, order_of_operations)
        await ctx.send('I rolled {}'.format(roll))
    else:
        # error
        await ctx.send('No equation provided')


@roll.command('add', aliases=['set', 'update'])
async def roll_add(ctx, expression: str, *, name: str):
    '''
    Adds/updates a new roll for a character

    Parameters:
    [expression] dice equation
    [name] name of roll to store
    '''
    with sqlalchemy_context(Session) as session:
        try:
            character = session.query(m.Character)\
                .filter_by(user=ctx.author.id).one()
        except NoResultFound:
            raise NoCharacterError()
        
        sql_update(session, m.Roll, {
            'character': character,
            'name': name,
        }, {
            'expression': expression,
        })

        await ctx.send('{} now has {}'.format(character.name, roll))


@roll.command('use')
async def roll_use(ctx, *, name: str):
    '''
    Rolls a stored dice expression

    Parameters:
    [name] name of roll to use
    '''
    with sqlalchemy_context(Session) as session:
        try:
            character = session.query(m.Character)\
                .filter_by(user=ctx.author.id).one()
        except NoResultFound:
            raise NoCharacterError

        try:
            roll = session.query(m.Roll)\
                .filter_by(name=name, character=character).one()
        except NoResultFound:
            raise NoResourceError

        result = equations.solve(
            roll.expression, operations, order_of_operations)
        await ctx.send('Rolling: {}'.format(roll.expression))
        await ctx.send('I rolled {}'.format(result))


@roll.command('check')
async def roll_check(ctx, *, name: str):
    '''
    Checks the status of a roll

    Parameters:
    [name] the name of the roll
        use the value "all" to list all rolls
    '''
    with sqlalchemy_context(Session) as session:
        try:
            character = session.query(m.Character)\
                .filter_by(user=ctx.author.id).one()
        except NoResultFound:
            raise NoCharacterError

        if name != 'all':
            try:
                roll = session.query(m.Roll)\
                    .filter_by(name=name, character=character).one()
            except NoResultFound:
                raise NoResourceError

            await ctx.send(roll)
        else:
            for roll in character.rolls:
                await ctx.send(roll)


@roll.command('remove', aliases=['delete'])
async def roll_remove(ctx, *, name: str):
    '''
    Deletes a roll from the character

    Parameters:
    [name] the name of the roll
    '''
    with sqlalchemy_context(Session) as session:
        try:
            character = session.query(m.Character)\
                .filter_by(user=ctx.author.id).one()
        except NoResultFound:
            raise NoCharacterError

        try:
            roll = session.query(m.Roll)\
                .filter_by(name=name, character=character).one()
        except NoResultFound:
            raise NoResourceError

        session.delete(roll)
        session.commit()
        await ctx.send('{} removed'.format(roll))


@roll.error
@roll_add.error
@roll_use.error
@roll_check.error
@roll_remove.error
async def roll_error(ctx, error):
    if (isinstance(error, commands.BadArgument) or
            isinstance(error, commands.MissingRequiredArgument) or
            isinstance(error, commands.TooManyArguments)):
        await ctx.send('Invalid parameters')
        await ctx.send('See the help text for valid parameters')
    elif isinstance(error, commands.CommandInvokeError):
        error = error.original
        if isinstance(error, NoCharacterError):
            await ctx.send('User does not have a character')
        elif isinstance(error, NoResourceError):
            await ctx.send('Could not find roll')
        elif isinstance(error, ValueError):
            await ctx.send('Invalid dice expression')
        else:
            await ctx.send('Error: {}'.format(error))
    else:
        await ctx.send('Error: {}'.format(error))


@bot.group(invoke_without_command=True)
async def resource(ctx):
    '''
    Manages character resources
    '''
    await ctx.send('Invalid subcommand')


@resource.command('add', aliases=['update'])
async def resource_add(ctx, max_uses: int, recover: str, *, name: str):
    '''
    Adds or changes a character resource

    Parameters:
    [max uses] the maximum number of uses of the resource
    [recover] the rest required to recover the resource,
        can be short|long|other
    [name] the name of the new resource
    '''
    with sqlalchemy_context(Session) as session:
        try:
            character = session.query(m.Character)\
                .filter_by(user=ctx.author.id).one()
        except NoResultFound:
            raise NoCharacterError()
        
        sql_update(session, m.Resource, {
            'character': character,
            'name': name,
        }, {
            'max': max,
            'current': max,
            'recover': recover,
        })

        await ctx.send('{} now has {}'.format(character.name, resource))


@resource.command('use')
async def resource_use(ctx, *, name: str):
    '''
    Consumes 1 use of the resource

    Parameters:
    [name] the name of the resource
    '''
    with sqlalchemy_context(Session) as session:
        try:
            character = session.query(m.Character)\
                .filter_by(user=ctx.author.id).one()
        except NoResultFound:
            raise NoCharacterError

        try:
            resource = session.query(m.Resource)\
                .filter_by(name=name, character=character).one()
        except NoResultFound:
            raise NoResourceError

        if resource.current > 0:
            resource.current -= 1
            session.commit()
            await ctx.send('{} used {}, {} remaining'.format(
                character.name, resource.name, resource.current))
        else:
            await ctx.send('{} cannot use {}'.format(
                character.name, resource.name))


def int_or_max(value: str):
    if value == 'max':
        return value
    else:
        try:
            return int(value)
        except ValueError:
            raise commands.BadArgument(value)


@resource.command('set')
async def resource_set(ctx, uses: int_or_max, *, name: str):
    '''
    Sets the remaining uses of a resource

    Parameters:
    [uses] can be the number of remaining uses or
        the special value "max" to refill all uses
    [name] the name of the resource
    '''
    with sqlalchemy_context(Session) as session:
        try:
            character = session.query(m.Character)\
                .filter_by(user=ctx.author.id).one()
        except NoResultFound:
            raise NoCharacterError

        try:
            resource = session.query(m.Resource)\
                .filter_by(name=name, character=character).one()
        except NoResultFound:
            raise NoResourceError

        if uses == 'max':
            resource.current = resource.max_uses
        else:
            resource.current = uses
        session.commit()

        await ctx.send('{} now has {} uses of {}'.format(
            character.name, resource.current, resource.name))


@resource.command('check')
async def resource_check(ctx, *, name: str):
    '''
    Checks the status of a resource

    Parameters:
    [name] the name of the resource
        use the value "all" to list resources
    '''
    with sqlalchemy_context(Session) as session:
        try:
            character = session.query(m.Character)\
                .filter_by(user=ctx.author.id).one()
        except NoResultFound:
            raise NoCharacterError

        if name != 'all':
            try:
                resource = session.query(m.Resource)\
                    .filter_by(name=name, character=character).one()
            except NoResultFound:
                raise NoResourceError

            await ctx.send(resource)
        else:
            for resource in character.resources:
                await ctx.send(resource)


@resource.command('remove', aliases=['delete'])
async def resource_remove(ctx, *, name: str):
    '''
    Deletes a resource from the character

    Parameters:
    [name] the name of the resource
    '''
    with sqlalchemy_context(Session) as session:
        try:
            character = session.query(m.Character)\
                .filter_by(user=ctx.author.id).one()
        except NoResultFound:
            raise NoCharacterError

        try:
            resource = session.query(m.Resource)\
                .filter_by(name=name, character=character).one()
        except NoResultFound:
            raise NoResourceError

        session.delete(resource)
        session.commit()
        await ctx.send('{} removed'.format(resource))


@resource.error
@resource_add.error
@resource_use.error
@resource_set.error
@resource_check.error
@resource_remove.error
async def resource_error(ctx, error):
    if (isinstance(error, commands.BadArgument) or
            isinstance(error, commands.MissingRequiredArgument) or
            isinstance(error, commands.TooManyArguments)):
        await ctx.send('Invalid parameters')
        await ctx.send('See the help text for valid parameters')
    elif isinstance(error, commands.CommandInvokeError):
        error = error.original
        if isinstance(error, NoCharacterError):
            await ctx.send('User does not have a character')
        elif isinstance(error, NoResourceError):
            await ctx.send('Could not find resource')
        else:
            await ctx.send('Error: {}'.format(error))
    else:
        await ctx.send('Error: {}'.format(error))


@bot.command()
async def rest(ctx, data: str):
    '''
    Take a rest

    Parameters:
    [type] should be short|long
    '''
    if data in ['short', 'long']:
        # short or long rest
        with sqlalchemy_context(Session) as session:
            try:
                character = session.query(m.Character)\
                    .filter_by(user=ctx.author.id).one()
            except NoResultFound:
                character = None

            if character:
                for resource in character.resources:
                    if data == 'long' and resource.recover == m.Rest.long:
                        resource.current = resource.max
                    elif resource.recover == m.Rest.short:
                        resource.current = resource.max

                session.commit()

                await ctx.send('{} has rested'.format(character.name))
            else:
                await ctx.send('User has no character')
    else:
        # error
        await ctx.send('Invalid rest type')


# ----#-   Application


@bot.event
async def on_ready():
    '''
    Sets up the bot
    '''
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Discord D&D bot')
    parser.add_argument(
        '-d, --database', dest='database', default='sqlite:///:memory:',
        help='The database url to be accessed')
    parser.add_argument(
        '-i, --initialize', dest='initialize', action='store_true',
        help='Allows for initialization of config values')
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    engine = create_engine(args.database)
    m.Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    with sqlalchemy_context(Session) as session:
        for name in config:
            try:
                key = session.query(m.Config).filter_by(name=name).one()
                config[name] = key.value
            except NoResultFound:
                key = m.Config(name=name, value=config[name])
                session.add(key)
                session.commit()

            if args.initialize:
                arg = input('[{}] (default: {}): '.format(
                    name, repr(key.value)))
                if arg:
                    key.value = arg
                    config[name] = arg
                    session.commit()

    bot.run(config['token'])
