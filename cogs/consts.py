from discord.ext import commands

import model as m
from util import Cog, get_character, sql_update, ItemNotFoundError


class ConstCog (Cog):
    @commands.group('constant', aliases=['const'], invoke_without_command=True)
    async def group(self, ctx):
        '''
        Manage character values
        '''
        message = 'Command "{} {}" is not found'.format(
            ctx.invoked_with, ctx.message.content.split()[1])
        raise commands.CommandNotFound(message)

    @group.command(aliases=['set', 'update'])
    async def add(self, ctx, name: str, value: int):
        '''
        Adds/updates a new constant for a character

        Parameters:
        [name] name of constant to store
        [value] value to store
        '''
        character = get_character(ctx.session, ctx.author.id, ctx.guild.id)

        const = sql_update(ctx.session, m.Constant, {
            'character': character,
            'name': name,
        }, {
            'value': value,
        })

        await ctx.send('{} now has {}'.format(str(character), str(const)))

    @group.command()
    async def check(self, ctx, *, name: str):
        '''
        Checks the status of a constant

        Parameters:
        [name] the name of the constant
        '''
        character = get_character(ctx.session, ctx.author.id, ctx.guild.id)
        const = ctx.session.query(m.Constant)\
            .get((character.id, name))
        if const is None:
            raise ItemNotFoundError(name)
        await ctx.send(str(const))

    @group.command()
    async def list(self, ctx):
        '''
        Lists all of a character's constants
        '''
        character = get_character(ctx.session, ctx.author.id, ctx.guild.id)
        text = ["{}'s constants:\n".format(character.name)]
        for const in character.constants:
            text.append(str(const))
        await ctx.send('\n'.join(text))

    @group.command(aliases=['delete'])
    async def remove(self, ctx, *, name: str):
        '''
        Deletes a constant from the character

        Parameters:
        [name] the name of the constant
        '''
        character = get_character(ctx.session, ctx.author.id, ctx.guild.id)

        const = ctx.session.query(m.Constant)\
            .get((character.id, name))
        if const is None:
            raise ItemNotFoundError(name)

        ctx.session.delete(const)
        ctx.session.commit()
        await ctx.send('{} no longer has {}'.format(
            str(character), str(const)))

    @group.command()
    async def inspect(self, ctx, *, character: str):
        '''
        Lists the constants for a specified character

        Parameters:
        [character] the name of the character to inspect
        '''
        character = ctx.session.query(m.Character)\
            .filter_by(name=character, server=ctx.guild.id).one_or_none()
        text = ["{}'s constants:\n".format(character.name)]
        for item in character.constants:
            text.append(str(item))
        await ctx.send('\n'.join(text))


def setup(bot):
    bot.add_cog(ConstCog(bot))
