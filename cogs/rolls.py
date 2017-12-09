import re
import random

from discord.ext import commands
from sqlalchemy import func

import model as m
from util import Cog, get_character, sql_update, ItemNotFoundError, equations


async def do_roll(ctx, session, character, expression):
    '''
    Does the dice rolling after const replacement
    '''
    if expression.endswith(' disadv'):
        adv = -1
        expression = expression[:-7]
    elif expression.endswith(' adv'):
        adv = 1
        expression = expression[:-4]
    else:
        adv = 0

    original_expression = expression
    output = []

    # Set up operations
    def roll_dice(a, b, *, silent=False):
        out = 0
        for _ in range(a):
            if b > 0:
                n = random.randint(1, b)
            elif b < 0:
                n = random.randint(b, -1)
            else:
                n = 0
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
    order_of_operations = [['d', 'D', 'g', 'G'], ['>', '<']]
    order_of_operations.extend(equations.order_of_operations)

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
            search = r'[a-zA-Z]*({})[a-zA-Z]*'.format(re.escape(token))
            search = re.search(search, original_expression)
            if search:
                token = search.group(1)
            raise equations.EquationError('Could not find: {}'.format(token))

    # do roll
    output.append('Rolling: `{}`'.format(expression))
    roll = equations.solve(expression, operations, order_of_operations)
    if roll % 1 == 0:
        roll = int(roll)
    output.append('I rolled {}'.format(roll))

    await ctx.send('\n'.join(output))

    return roll


class RollCog (Cog):
    @commands.group('roll', aliases=['r'], invoke_without_command=True)
    async def group(self, ctx, *, expression: str):
        '''
        Rolls dice
        Note: If a const name is included in a roll the name will be replaced
            with the value of the const

        Parameters:
        [expression] standard dice notation specifying what to roll
            the expression may include up to 1 saved roll
        [adv] (optional) if present should be adv|disadv to indicate that any
            1d20 should be rolled with advantage or disadvantage respectively

        Mathematic operations from highest precedence to lowest:

        d : NdM rolls an M sided die N times and adds the results together
            operates specially for adv/disadv
        g : NgM rolls an M sided die N times, rerolls any 1 or 2 once

        > : picks larger operand
        < : picks smaller operand

        ^ : exponentiation

        * : multiplication
        / : division
        //: division, rounded down

        + : addition
        - : subtraction
        '''
        if not expression:
            raise commands.MissingRequiredArgument('expression')

        character = ctx.session.query(m.Character)\
            .filter_by(user=ctx.author.id, server=ctx.guild.id).one_or_none()

        await do_roll(ctx, ctx.session, character, expression)

    @group.command(aliases=['set', 'update'])
    async def add(self, ctx, name: str, expression: str):
        '''
        Adds/updates a new roll for a character

        Parameters:
        [name] name of roll to store
        [expression] dice equation
        '''
        character = get_character(ctx.session, ctx.author.id, ctx.guild.id)

        roll = sql_update(ctx.session, m.Roll, {
            'character': character,
            'name': name,
        }, {
            'expression': expression,
        })

        await ctx.send('{} now has {}'.format(str(character), str(roll)))

    @group.command()
    async def check(self, ctx, *, name: str):
        '''
        Checks the status of a roll

        Parameters:
        [name] the name of the roll
        '''
        character = get_character(ctx.session, ctx.author.id, ctx.guild.id)
        roll = ctx.session.query(m.Roll)\
            .get((character.id, name))
        if roll is None:
            raise ItemNotFoundError(name)
        await ctx.send(str(roll))

    @group.command()
    async def list(self, ctx):
        '''
        Lists all of a character's rolls
        '''
        character = get_character(ctx.session, ctx.author.id, ctx.guild.id)
        text = ["{}'s rolls:".format(character.name)]
        for roll in character.rolls:
            text.append(str(roll))
        await ctx.send('\n'.join(text))

    @group.command(aliases=['delete'])
    async def remove(self, ctx, *, name: str):
        '''
        Deletes a roll from the character

        Parameters:
        [name] the name of the roll
        '''
        character = get_character(ctx.session, ctx.author.id, ctx.guild.id)

        roll = ctx.session.query(m.Roll)\
            .get((character.id, name))
        if roll is None:
            raise ItemNotFoundError(name)

        ctx.session.delete(roll)
        ctx.session.commit()
        await ctx.send('{} removed'.format(str(roll)))


def setup(bot):
    bot.add_cog(RollCog(bot))
