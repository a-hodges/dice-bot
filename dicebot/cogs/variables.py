from discord.ext import commands

from . import util
from .util import m


class VariableCog (util.Cog):
    @commands.group('variable', aliases=['var'], invoke_without_command=True)
    async def group(self, ctx):
        '''
        Manage character values
        '''
        raise util.invalid_subcommand(ctx)

    @group.command(aliases=['set', 'update'], ignore_extra=False)
    async def add(self, ctx, name: str, value: int):
        '''
        Adds/updates a new variable for a character

        Parameters:
        [name] name of variable to store
        [value] value to store
        '''
        character = util.get_character(ctx.session, ctx.author.id, ctx.guild.id)

        variable = util.sql_update(ctx.session, m.Variable, {
            'character': character,
            'name': name,
        }, {
            'value': value,
        })

        await ctx.send('{} now has {}'.format(str(character), str(variable)))

    @group.command()
    async def check(self, ctx, *, name: str):
        '''
        Checks the status of a variable

        Parameters:
        [name*] the name of the variable
        '''
        name = util.strip_quotes(name)

        character = util.get_character(ctx.session, ctx.author.id, ctx.guild.id)
        variable = ctx.session.query(m.Variable)\
            .filter_by(character_id=character.id, name=name).one_or_none()
        if variable is None:
            raise util.ItemNotFoundError(name)
        await ctx.send(str(variable))

    @group.command(ignore_extra=False)
    async def list(self, ctx):
        '''
        Lists all of a character's variables
        '''
        character = util.get_character(ctx.session, ctx.author.id, ctx.guild.id)
        pages = util.item_paginator(character.variables, header="{}'s variables:".format(character.name))
        await util.send_pages(ctx, pages)

    @group.command(aliases=['delete'])
    async def remove(self, ctx, *, name: str):
        '''
        Deletes a variable from the character

        Parameters:
        [name*] the name of the variable
        '''
        name = util.strip_quotes(name)

        character = util.get_character(ctx.session, ctx.author.id, ctx.guild.id)

        variable = ctx.session.query(m.Variable)\
            .filter_by(character_id=character.id, name=name).one_or_none()
        if variable is None:
            raise util.ItemNotFoundError(name)

        ctx.session.delete(variable)
        ctx.session.commit()
        await ctx.send('{} no longer has {}'.format(str(character), str(variable)))

    @group.command()
    async def inspect(self, ctx, *, name: str):
        '''
        Lists the variables for a specified character

        Parameters:
        [name*] the name of the character to inspect
        '''
        name = util.strip_quotes(name)

        character = ctx.session.query(m.Character)\
            .filter_by(name=name, server=str(ctx.guild.id)).one_or_none()
        if character is None:
            raise Exception('No character named {}'.format(name))
        else:
            pages = util.item_paginator(character.variables, header="{}'s variables:".format(character.name))
            await util.send_pages(ctx, pages)


def setup(bot):
    bot.add_cog(VariableCog(bot))
