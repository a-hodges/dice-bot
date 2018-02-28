from discord.ext import commands

from . import util
from .util import m
from .rolls import do_roll


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

        await util.send_embed(ctx, description='{} now has {}'.format(str(character), str(resource)))

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
        description = "{0}'s {1} went from {2}/{4} to {3}/{4}".format(
            str(character), resource.name, prev, resource.current, resource.max)
        await util.send_embed(ctx, description=description)

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
            description = "{0}'s {1} went from {2}/{4} to {3}/{4}".format(
                str(character), resource.name, prev, resource.current, resource.max)
        else:
            raise Exception("{} has no {} to use".format(str(character), resource.name))

        await util.send_embed(ctx, description=description)

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

        description = '{} now has {}/{} uses of {}'.format(
            str(character), resource.current, resource.max, resource.name)
        await util.send_embed(ctx, description=description)

    @group.command(aliases=['recover'])
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

        description = '{} now has {}/{} uses of {}'.format(
            str(character), resource.current, resource.max, resource.name)
        await util.send_embed(ctx, description=description)

    @group.command()
    async def roll(self, ctx, name: str, *, expression: str):
        '''
        Adds the rolled value to the specified resource using the `roll` command

        Parameters:
        [name] the name of the resource to roll for
        [expression*] standard dice notation specifying what to roll the expression may include up to 1 saved roll
        [adv] (optional) roll with advantage or disadvantage respectively as specified in the `roll` command
        '''
        if not expression:
            raise commands.MissingRequiredArgument('expression')
        expression = util.strip_quotes(expression)

        character = util.get_character(ctx.session, ctx.author.id, ctx.guild.id)

        output = []
        number = await do_roll(expression, ctx.session, character, output=output)
        await util.send_embed(ctx, description=' **|** '.join(output))

        await ctx.invoke(self.plus, number, name=name)

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
        await util.send_embed(ctx, description=str(resource))

    @group.command(ignore_extra=False)
    async def list(self, ctx):
        '''
        Lists all of a character's resources
        '''
        character = util.get_character(ctx.session, ctx.author.id, ctx.guild.id)
        await util.inspector(ctx, character, 'resources')

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
        await util.send_embed(ctx, description='{} removed'.format(str(resource)))

    @group.command()
    async def inspect(self, ctx, *, name: str):
        '''
        Lists the resources for a specified character

        Parameters:
        [name*] the name of the character to inspect
        '''
        name = util.strip_quotes(name)

        await util.inspector(ctx, name, 'resources')

    @commands.command(aliases=['res4'], invoke_without_command=True)
    async def resourcefor(self, ctx, character: str, number: int, *, name: str):
        '''
        Regains a number of uses of the resource for the specified character
        Can accept negative numbers

        Parameters:
        [character] the name of the character to manage
        [number] the quantity of the resource to regain
        [name*] the name of the resource
        '''
        name = util.strip_quotes(name)

        character = ctx.session.query(m.Character)\
            .filter_by(name=character, server=str(ctx.guild.id)).one_or_none()
        if character is None:
            raise Exception('Character does not exist')

        resource = ctx.session.query(m.Resource)\
            .filter_by(character_id=character.id, name=name).one_or_none()
        if resource is None:
            raise util.ItemNotFoundError(name)

        prev = resource.current
        resource.current = resource.current + number
        ctx.session.commit()
        description = "{0}'s {1} went from {2}/{4} to {3}/{4}".format(
            str(character), resource.name, prev, resource.current, resource.max)
        await util.send_embed(ctx, description=description)


def setup(bot):
    bot.add_cog(ResourceCategory(bot))
