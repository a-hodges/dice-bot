import re
import random
from itertools import chain

from discord.ext import commands
from sqlalchemy import func
import equations

from . import util
from .util import m


async def do_roll(expression, session, character=None, output=[]):
    '''
    Does the variable replacement and dice rolling
    '''
    expression = expression.strip()
    match = re.match(r'^(.*)\s+((?:dis)?adv|dis|(?:dis)?advantage)$', expression)
    if match:
        expression = match.group(1)
        if match.group(2) in ['adv', 'advantage']:
            adv = 1
        elif match.group(2) in ['dis', 'disadv', 'disadvantage']:
            adv = -1
        else:
            raise Exception('Invalid adv/disadv operator')
    else:
        adv = 0

    original_expression = expression

    # Set up operations
    def roll_dice(a, b, *, silent=False):
        rolls = []
        for _ in range(a):
            if b > 0:
                n = random.randint(1, b)
            elif b < 0:
                n = random.randint(b, -1)
            else:
                n = 0
            rolls.append(n)
        value = sum(rolls)
        if not silent:
            output.append('{}d{}: {} = {}'.format(a, b, ' + '.join(map(str, rolls)), value))
        return value

    def great_weapon_fighting(a, b, low=2, *, silent=False):
        rolls = []
        rerolls = []
        value = 0
        for _ in range(a):
            n = roll_dice(1, b, silent=True)
            rolls.append(n)
            if n <= low:
                n2 = random.randint(1, b)
                rerolls.append(n2)
                value += n2
            else:
                value += n
        if not silent:
            rolled = ' + '.join(map(str, rolls))
            if rerolls:
                rerolled = list(filter(lambda a: a > low, rolls))
                rerolled.extend(rerolls)
                rerolled = ' + '.join(map(str, rerolled))
                output.append('{}g{}: {}, rerolled: {} = {}'.format(a, b, rolled, rerolled, value))
            else:
                output.append('{}g{}: {} = {}'.format(a, b, rolled, value))
        return value

    def roll_advantage(a, b, *, silent=False):
        if a == 1 and b == 20:
            first = roll_dice(a, b, silent=True)
            second = roll_dice(a, b, silent=True)
            out = max(first, second)
            if not silent:
                output.append('{}d{}: max({}, {}) = {}'.format(a, b, first, second, out))
        else:
            out = roll_dice(a, b, silent=silent)
        return out

    def roll_disadvantage(a, b, *, silent=False):
        if a == 1 and b == 20:
            first = roll_dice(a, b, silent=True)
            second = roll_dice(a, b, silent=True)
            out = min(first, second)
            if not silent:
                output.append('{}d{}: min({}, {}) = {}'.format(a, b, first, second, out))
        else:
            out = roll_dice(a, b, silent=silent)
        return out

    operations = equations.operations.copy()
    operations.append({'>': max, '<': min})

    dice = {}
    if adv == 0:
        dice['d'] = roll_dice
    elif adv > 0:
        dice['d'] = roll_advantage
    else:
        dice['d'] = roll_disadvantage
    dice['D'] = dice['d']
    dice['g'] = great_weapon_fighting
    dice['G'] = dice['g']
    operations.append(dice)

    unary = equations.unary.copy()
    unary['!'] = lambda a: a // 2 - 5

    output.append('`{}`'.format(expression))

    if character:
        # replace rolls
        rolls = session.query(m.Roll)\
            .filter_by(character=character)\
            .order_by(func.char_length(m.Roll.name).desc())
        rep = {roll.name: '({})'.format(roll.expression) for roll in rolls}
        expr = re.compile('|'.join(map(re.escape, sorted(rep.keys(), key=len, reverse=True))))
        for _ in range(3):
            expression = expr.sub(lambda m: rep[m.group(0)], expression)
            temp = '`{}`'.format(expression)
            if temp != output[-1]:
                output.append(temp)
            else:
                break

        # replace variables
        variables = session.query(m.Variable)\
            .filter_by(character=character)\
            .order_by(func.char_length(m.Variable.name).desc())
        rep = {var.name: '({})'.format(var.value) for var in variables}
        expr = re.compile('|'.join(map(re.escape, sorted(rep.keys(), key=len, reverse=True))))
        expression = expr.sub(lambda m: rep[m.group(0)], expression)
        temp = '`{}`'.format(expression)
        if temp != output[-1]:
            output.append(temp)

    # validate
    for token in re.findall(r'[a-zA-Z]+', expression):
        if token not in chain(*operations) and token not in unary:
            search = r'[a-zA-Z]*({})[a-zA-Z]*'.format(re.escape(token))
            search = re.search(search, original_expression)
            if search:
                token = search.group(1)
            raise equations.EquationError('Could not find: {}'.format(token))

    # do roll
    roll = equations.solve(expression, operations=operations, unary=unary)
    if roll % 1 == 0:
        roll = int(roll)

    if character:
        output.append('{} rolled {}'.format(str(character), roll))
    else:
        output.append('You rolled {}'.format(roll))

    return roll


class RollCategory (util.Cog):
    @commands.group('roll', aliases=['r'], invoke_without_command=True)
    async def group(self, ctx, *, expression: str):
        '''
        Rolls dice
        Note: If a variable name is included in a roll the name will be replaced with the value of the variable

        Parameters:
        [expression*] standard dice notation specifying what to roll
            The expression may include saved rolls, replacing the name with the roll itself
            Rolls may contain other rolls up to 3 levels deep
        [adv] (optional) roll any 1d20s with advantage or disadvantage for the following options:
            Advantage: `adv` | `advantage`
            Disadvantage: `dis` | `disadv` | `disadvantage`

        Mathematic operations from highest precedence to lowest:

        d : NdM rolls an M sided die N times and adds the results together
        g : NgM rolls an M sided die N times, rerolls any 1 or 2 once

        > : picks larger operand
        < : picks smaller operand

        ^ : exponentiation

        * : multiplication
        / : division
        //: division, rounded down

        + : addition
        - : subtraction

        Unary prefixes:
        - : negates a number
        + : does nothing to a number
        ! : gets the modifier of an ability score using standard D&D modifier rules (score/2-5) i.e. !16 = 3
        '''
        if not expression:
            raise commands.MissingRequiredArgument('expression')
        expression = util.strip_quotes(expression)

        if ctx.guild:
            try:
                character = util.get_character(ctx.session, ctx.author.id, ctx.guild.id)
            except util.NoCharacterError:
                character = None
        else:
            character = None

        output = []
        await do_roll(expression, ctx.session, character, output=output)
        await util.send_embed(ctx, description='\n'.join(output))

    @group.command(aliases=['set', 'update'], ignore_extra=False)
    async def add(self, ctx, name: str, expression: str):
        '''
        Adds/updates a new roll for a character

        Parameters:
        [name] name of roll to store
        [expression] dice equation
        '''
        character = util.get_character(ctx.session, ctx.author.id, ctx.guild.id)

        roll = util.sql_update(ctx.session, m.Roll, {
            'character': character,
            'name': name,
        }, {
            'expression': expression,
        })

        await util.send_embed(ctx, description='{} now has {}'.format(str(character), str(roll)))

    @group.command()
    async def check(self, ctx, *, name: str):
        '''
        Checks the status of a roll

        Parameters:
        [name*] the name of the roll
        '''
        name = util.strip_quotes(name)

        character = util.get_character(ctx.session, ctx.author.id, ctx.guild.id)
        roll = ctx.session.query(m.Roll)\
            .filter_by(character_id=character.id, name=name).one_or_none()
        if roll is None:
            raise util.ItemNotFoundError(name)
        await util.send_embed(ctx, description=str(roll))

    @group.command(ignore_extra=False)
    async def list(self, ctx):
        '''
        Lists all of a character's rolls
        '''
        character = util.get_character(ctx.session, ctx.author.id, ctx.guild.id)
        await util.inspector(ctx, character, 'rolls')

    @group.command(aliases=['delete'])
    async def remove(self, ctx, *, name: str):
        '''
        Deletes a roll from the character

        Parameters:
        [name*] the name of the roll
        '''
        name = util.strip_quotes(name)

        character = util.get_character(ctx.session, ctx.author.id, ctx.guild.id)

        roll = ctx.session.query(m.Roll)\
            .filter_by(character_id=character.id, name=name).one_or_none()
        if roll is None:
            raise util.ItemNotFoundError(name)

        ctx.session.delete(roll)
        ctx.session.commit()
        await util.send_embed(ctx, description='{} removed'.format(str(roll)))

    @group.command()
    async def inspect(self, ctx, *, name: str):
        '''
        Lists the rolls for a specified character

        Parameters:
        [name*] the name of the character to inspect
        '''
        name = util.strip_quotes(name)

        await util.inspector(ctx, name, 'rolls')

    @commands.command(aliases=['r4'])
    @commands.has_permissions(administrator=True)
    async def rollfor(self, ctx, character: str, *, expression: str):
        '''
        Make a roll for the specified character
        Uses the same rules as the `roll` command
        Can only be done by an administrator

        Parameters:
        [character] the name of the character to roll for
        [expression*] standard dice notation specifying what to roll the expression may include up to 1 saved roll
        [adv] (optional) roll with advantage or disadvantage respectively as specified in the `roll` command
        '''
        if not expression:
            raise commands.MissingRequiredArgument('expression')
        expression = util.strip_quotes(expression)

        character = ctx.session.query(m.Character)\
            .filter_by(name=character, server=str(ctx.guild.id)).one_or_none()
        if character is None:
            raise Exception('Character does not exist')

        output = []
        await do_roll(expression, ctx.session, character, output=output)
        await util.send_embed(ctx, description='\n'.join(output))


def setup(bot):
    bot.add_cog(RollCategory(bot))
