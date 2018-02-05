from discord.ext import commands

from . import util
from .util import m


class ResourceCategory (util.Cog):
    @commands.group('resource', aliases=['res'], invoke_without_command=True)
    async def group(self, ctx, *, input: str):
        '''
        Manages character resources
        '''
        try:
            number, name = input.split(maxsplit=1)
            number = int(number)
        except ValueError:
            raise util.invalid_subcommand(ctx)
        await ctx.invoke(self.plus, number, name=name)

    @group.command(aliases=['update'], ignore_extra=False)
    async def add(self, ctx, name: str, max_uses: int, recover: str):
        '''
        Adds or changes a character resource

        Parameters:
        [name] the name of the new resource
        [max uses] the maximum number of uses of the resource
        [recover] the rest required to recover the resource,
            can be short|long|other
        '''
        if recover not in ['short', 'long', 'other']:
            raise commands.BadArgument('Bad argument: recover')

        character = util.get_character(ctx.session, ctx.author.id, ctx.guild.id)

        resource = util.sql_update(ctx.session, m.Resource, {
            'character': character,
            'name': name,
        }, {
            'max': max_uses,
            'current': max_uses,
            'recover': recover,
        })

        await ctx.send('{} now has {}'.format(str(character), str(resource)))

    @group.command('+')
    async def plus(self, ctx, number: int, *, name: str):
        '''
        Regains a number of uses of the resource

        Parameters:
        [number] the quantity of the resource to regain
        [name*] the name of the resource
        '''
        name = util.strip_quotes(name)

        character = util.get_character(ctx.session, ctx.author.id, ctx.guild.id)

        resource = ctx.session.query(m.Resource)\
            .filter_by(character_id=character.id, name=name).one_or_none()
        if resource is None:
            raise util.ItemNotFoundError(name)

        prev = resource.current
        resource.current = resource.current + number
        ctx.session.commit()
        await ctx.send("{0}'s {1} went from {2}/{4} to {3}/{4}".format(
            str(character), resource.name, prev, resource.current, resource.max))

    @group.command('-')
    async def minus(self, ctx, number: int, *, name: str):
        '''
        Consumes a number of uses of the resource

        Parameters:
        [number] the quantity of the resource to use
        [name*] the name of the resource
        '''
        name = util.strip_quotes(name)

        await ctx.invoke(self.plus, -number, name=name)

    @group.command()
    async def use(self, ctx, *, name: str):
        '''
        Consumes 1 use of the resource

        Parameters:
        [name*] the name of the resource
        '''
        name = util.strip_quotes(name)

        character = util.get_character(ctx.session, ctx.author.id, ctx.guild.id)

        resource = ctx.session.query(m.Resource)\
            .filter_by(character_id=character.id, name=name).one_or_none()
        if resource is None:
            raise util.ItemNotFoundError(name)

        if resource.current >= 1:
            prev = resource.current
            resource.current = resource.current - 1
            ctx.session.commit()
            await ctx.send("{0}'s {1} went from {2}/{4} to {3}/{4}".format(
                str(character), resource.name, prev, resource.current, resource.max))
        else:
            await ctx.send("{} has no {} to use".format(str(character), resource.name))

    @group.command(ignore_extra=False)
    async def set(self, ctx, name: str, uses: int):
        '''
        Sets the remaining uses of a resource

        Parameters:
        [name] the name of the resource
        [uses] the new number of remaining uses
        '''
        character = util.get_character(ctx.session, ctx.author.id, ctx.guild.id)

        resource = ctx.session.query(m.Resource)\
            .filter_by(character_id=character.id, name=name).one_or_none()
        if resource is None:
            raise util.ItemNotFoundError(name)

        resource.current = uses
        ctx.session.commit()

        await ctx.send('{} now has {}/{} uses of {}'.format(
            str(character), resource.current, resource.max, resource.name))

    @group.command()
    async def regain(self, ctx, *, name: str):
        '''
        Returns the remaining uses of a resource to max

        Parameters:
        [name*] the name of the resource
        '''
        name = util.strip_quotes(name)

        character = util.get_character(ctx.session, ctx.author.id, ctx.guild.id)

        resource = ctx.session.query(m.Resource)\
            .filter_by(character_id=character.id, name=name).one_or_none()
        if resource is None:
            raise util.ItemNotFoundError(name)

        resource.current = resource.max
        ctx.session.commit()

        await ctx.send('{} now has {}/{} uses of {}'.format(
            str(character), resource.current, resource.max, resource.name))

    @group.command()
    async def check(self, ctx, *, name: str):
        '''
        Checks the status of a resource

        Parameters:
        [name*] the name of the resource
        '''
        name = util.strip_quotes(name)

        character = util.get_character(ctx.session, ctx.author.id, ctx.guild.id)
        resource = ctx.session.query(m.Resource)\
            .filter_by(character_id=character.id, name=name).one_or_none()
        if resource is None:
            raise util.ItemNotFoundError(name)
        await ctx.send(str(resource))

    @group.command(ignore_extra=False)
    async def list(self, ctx):
        '''
        Lists all of a character's resources
        '''
        character = util.get_character(ctx.session, ctx.author.id, ctx.guild.id)
        pages = util.item_paginator(character.resources, header="{}'s resources:".format(character.name))
        await util.send_pages(ctx, pages)

    @group.command(aliases=['delete'])
    async def remove(self, ctx, *, name: str):
        '''
        Deletes a resource from the character

        Parameters:
        [name*] the name of the resource
        '''
        name = util.strip_quotes(name)

        character = util.get_character(ctx.session, ctx.author.id, ctx.guild.id)

        resource = ctx.session.query(m.Resource)\
            .filter_by(character_id=character.id, name=name).one_or_none()
        if resource is None:
            raise util.ItemNotFoundError(name)

        ctx.session.delete(resource)
        ctx.session.commit()
        await ctx.send('{} removed'.format(str(resource)))

    @group.command()
    async def inspect(self, ctx, *, name: str):
        '''
        Lists the resources for a specified character

        Parameters:
        [name*] the name of the character to inspect
        '''
        name = util.strip_quotes(name)

        await util.inspector(ctx, name, 'resources', util.item_paginator)


def setup(bot):
    bot.add_cog(ResourceCategory(bot))
