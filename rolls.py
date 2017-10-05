from discord.ext import commands

import model as m
from util import Cog, do_roll, get_character, sql_update, ItemNotFoundError


class RollCog (Cog):
    @commands.group('roll', invoke_without_command=True)
    async def group(self, ctx, *, expression: str):
        '''
        Rolls dice
        Note: consts can be used in rolls and are replaced by the const value

        Parameters:
        [expression] standard dice notation specifying what to roll
            the expression may include up to 1 saved roll
        [adv] (optional) if present should be adv|disadv to indicate that any
            1d20 should be rolled with advantage or disadvantage respectively

        For finer control over advantage/disadvantage the > operator
        picks the larger operand and the < operator picks the smaller

        There is also a special 'great weapon fighting' operator
        which rerolls a 1 or 2, i.e. "2g6+5"
        '''
        if not expression:
            raise commands.MissingRequiredArgument('expression')

        if expression.endswith(' disadv'):
            adv = -1
            expression = expression[:-7]
        elif expression.endswith(' adv'):
            adv = 1
            expression = expression[:-4]
        else:
            adv = 0

        expression = expression.strip()

        character = ctx.session.query(m.Character)\
            .filter_by(user=ctx.author.id, server=ctx.guild.id).one_or_none()

        await do_roll(ctx, ctx.session, character, expression, adv)

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
        if not roll:
            raise ItemNotFoundError
        await ctx.send(str(roll))

    @group.command()
    async def list(self, ctx):
        '''
        Lists all rolls for the user
        '''
        character = get_character(ctx.session, ctx.author.id, ctx.guild.id)
        text = ["{}'s rolls:".format(str(character))]
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
        if not roll:
            raise ItemNotFoundError

        ctx.session.delete(roll)
        ctx.session.commit()
        await ctx.send('{} removed'.format(str(roll)))


def setup(bot):
    bot.add_cog(RollCog(bot))
