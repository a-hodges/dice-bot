from discord.ext import commands

import model as m
from util import Cog, get_character, sql_update, ItemNotFoundError
from .cog_utils import send_pages, item_paginator, strip_quotes


class VariableCog (Cog):
    @commands.group('variable', aliases=['var'], invoke_without_command=True)
    async def group(self, ctx):
        '''
        Manage character values
        '''
        message = 'Command "{} {}" is not found'.format(ctx.invoked_with, ctx.message.content.split()[1])
        raise commands.CommandNotFound(message)

    @group.command(aliases=['set', 'update'], ignore_extra=False)
    async def add(self, ctx, name: str, value: int):
        '''
        Adds/updates a new variable for a character

        Parameters:
        [name] name of variable to store
        [value] value to store
        '''
        character = get_character(ctx.session, ctx.author.id, ctx.guild.id)

        variable = sql_update(ctx.session, m.Variable, {
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
        name = strip_quotes(name)

        character = get_character(ctx.session, ctx.author.id, ctx.guild.id)
        variable = ctx.session.query(m.Variable)\
            .filter_by(character_id=character.id, name=name).one_or_none()
        if variable is None:
            raise ItemNotFoundError(name)
        await ctx.send(str(variable))

    @group.command(ignore_extra=False)
    async def list(self, ctx):
        '''
        Lists all of a character's variables
        '''
        character = get_character(ctx.session, ctx.author.id, ctx.guild.id)
        pages = item_paginator(character.variables, header="{}'s variables:".format(character.name))
        await send_pages(ctx, pages)

    @group.command(aliases=['delete'])
    async def remove(self, ctx, *, name: str):
        '''
        Deletes a variable from the character

        Parameters:
        [name*] the name of the variable
        '''
        name = strip_quotes(name)

        character = get_character(ctx.session, ctx.author.id, ctx.guild.id)

        variable = ctx.session.query(m.Variable)\
            .filter_by(character_id=character.id, name=name).one_or_none()
        if variable is None:
            raise ItemNotFoundError(name)

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
        name = strip_quotes(name)

        character = ctx.session.query(m.Character)\
            .filter_by(name=name, server=str(ctx.guild.id)).one_or_none()
        if character is None:
            await ctx.send('No character named {}'.format(name))
        else:
            pages = item_paginator(character.variables, header="{}'s variables:".format(character.name))
            await send_pages(ctx, pages)


def setup(bot):
    bot.add_cog(VariableCog(bot))
