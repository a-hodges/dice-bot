import random
import re

from sqlalchemy import func
from sqlalchemy.orm.exc import NoResultFound

import equations
import model as m


class BotError (Exception):
    pass


class NoCharacterError (BotError):
    pass


class ItemNotFoundError (BotError):
    pass


class Cog:
    def __init__(self, bot):
        self.bot = bot


async def do_roll(ctx, session, character, expression, adv=0):
    '''
    Does the dice rolling after const replacement
    '''
    original_expression = expression
    output = []

    # Set up operations
    def roll_dice(a, b, *, silent=False):
        out = 0
        for _ in range(a):
            n = random.randint(1, b)
            out += n
        if not silent:
            output.append('{}d{}: {}'.format(a, b, out))
        return out

    def great_weapon_fighting(a, b, *, silent=False):
        out = 0
        for _ in range(a):
            n = roll_dice(1, b, silent=True)
            if n <= 2:
                n2 = random.randint(1, b)
                if not silent:
                    output.append('1d{0}: {1}, rerolling, 1d{0}: {2}'.format(
                        b, n, n2))
                n = n2
            elif not silent:
                output.append('1d{}: {}'.format(b, n))
            out += n
        return out

    def roll_advantage(a, b, *, silent=False):
        if a == 1 and b == 20:
            first = roll_dice(a, b, silent=True)
            second = roll_dice(a, b, silent=True)
            out = max(first, second)
            if not silent:
                output.append('{}d{}, picking larger of {} and {}: {}'.format(
                    a, b, first, second, out))
        else:
            out = roll_dice(a, b, silent=silent)
        return out

    def roll_disadvantage(a, b, *, silent=False):
        if a == 1 and b == 20:
            first = roll_dice(a, b, silent=True)
            second = roll_dice(a, b, silent=True)
            out = min(first, second)
            if not silent:
                output.append('{}d{}, picking smaller of {} and {}: {}'.format(
                    a, b, first, second, out))
        else:
            out = roll_dice(a, b, silent=silent)
        return out

    operations = equations.operations.copy()
    if adv == 0:
        operations['d'] = roll_dice
    elif adv > 0:
        operations['d'] = roll_advantage
    else:
        operations['d'] = roll_disadvantage
    operations['D'] = operations['d']
    operations['g'] = great_weapon_fighting
    operations['G'] = operations['g']
    operations['>'] = max
    operations['<'] = min
    order_of_operations = [['d', 'D', 'g', 'G']]
    order_of_operations.extend(equations.order_of_operations)
    order_of_operations.append(['>', '<'])

    if character:
        # replace only 1 roll
        rolls = session.query(m.Roll)\
            .filter_by(character=character)\
            .order_by(func.char_length(m.Roll.name).desc())
        for roll in rolls:
            if roll.name in expression:
                expression = expression.replace(
                    roll.name, '({})'.format(roll.expression), 1)
                break

        # replace constants
        consts = session.query(m.Constant)\
            .filter_by(character=character)\
            .order_by(func.char_length(m.Constant.name).desc())
        for const in consts:
            expression = expression.replace(
                const.name, '({})'.format(const.value))

    # validate
    for token in re.findall(r'[a-zA-Z]+', expression):
        if token not in operations:
            search = r'[a-zA-Z]*' + re.escape(token) + r'[a-zA-Z]*'
            search = re.findall(search, original_expression)
            if search:
                token = search[0]
            raise equations.EquationError('Could not find `{}`'.format(token))

    # do roll
    output.append('Rolling: {}'.format(expression))
    roll = equations.solve(expression, operations, order_of_operations)
    output.append('I rolled {}'.format(roll))

    await ctx.send('\n'.join(output))

    return roll


def get_character(session, userid, server):
    '''
    Gets a character based on their user
    '''
    try:
        character = session.query(m.Character)\
            .filter_by(user=userid, server=server).one()
    except NoResultFound:
        raise NoCharacterError()
    return character


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

    return obj
