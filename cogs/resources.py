from discord.ext import commands

import model as m
from util import Cog, get_character, sql_update, ItemNotFoundError


def int_or_max(value: str):
    if value == 'max':
        return value
    else:
        try:
            return int(value)
        except ValueError:
            raise commands.BadArgument(value)


class ResourceCog (Cog):
    @commands.group('resource', invoke_without_command=True)
    async def group(self, ctx):
        '''
        Manages character resources
        '''
        await ctx.send('Invalid subcommand')

    @group.command(aliases=['update'])
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
            raise commands.BadArgument('recover')

        character = get_character(ctx.session, ctx.author.id, ctx.guild.id)

        resource = sql_update(ctx.session, m.Resource, {
            'character': character,
            'name': name,
        }, {
            'max': max_uses,
            'current': max_uses,
            'recover': recover,
        })

        await ctx.send('`{}` now has `{}`'.format(
            str(character), str(resource)))

    @group.command(aliases=['-'])
    async def consume(self, ctx, number: int, *, name: str):
        '''
        Consumes a number of uses of the resource

        Parameters:
        [number] the quantity of the resource to use
        [name] the name of the resource
        '''
        character = get_character(ctx.session, ctx.author.id, ctx.guild.id)

        resource = ctx.session.query(m.Resource)\
            .get((character.id, name))
        if resource is None:
            raise ItemNotFoundError

        prev = resource.current
        if resource.current - number >= 0:
            resource.current = resource.current - number
            if resource.current > resource.max:
                resource.current = resource.max
            ctx.session.commit()
            await ctx.send("`{0}`'s `{1}` went from {2}/{4} to {3}/{4}".format(
                str(character), resource.name, prev,
                resource.current, resource.max))
        else:
            await ctx.send('`{}` does not have enough to use: `{}`'.format(
                str(character), str(resource)))

    @group.command()
    async def use(self, ctx, *, name: str):
        '''
        Consumes 1 use of the resource

        Parameters:
        [name] the name of the resource
        '''
        await self.consume.callback(self, ctx, 1, name=name)

    @group.command(aliases=['+'])
    async def regain(self, ctx, number: int, *, name: str):
        '''
        Regains a number of uses of the resource

        Parameters:
        [number] the quantity of the resource to regain
        [name] the name of the resource
        '''
        await self.consume.callback(self, ctx, -number, name=name)

    @group.command()
    async def set(self, ctx, name: str, uses: int_or_max):
        '''
        Sets the remaining uses of a resource

        Parameters:
        [name] the name of the resource
        [uses] can be the number of remaining uses or
            the special value "max" to refill all uses
        '''
        character = get_character(ctx.session, ctx.author.id, ctx.guild.id)

        resource = ctx.session.query(m.Resource)\
            .get((character.id, name))
        if resource is None:
            raise ItemNotFoundError

        if uses == 'max':
            resource.current = resource.max
        else:
            resource.current = uses
        ctx.session.commit()

        await ctx.send('`{}` now has {}/{} uses of `{}`'.format(
            str(character), resource.current, resource.max, resource.name))

    @group.command()
    async def check(self, ctx, *, name: str):
        '''
        Checks the status of a resource

        Parameters:
        [name] the name of the resource
        '''
        character = get_character(ctx.session, ctx.author.id, ctx.guild.id)
        resource = ctx.session.query(m.Resource)\
            .get((character.id, name))
        if resource is None:
            raise ItemNotFoundError
        await ctx.send('`{}`'.format(str(resource)))

    @group.command()
    async def list(self, ctx):
        '''
        Lists all of a character's resources
        '''
        character = get_character(ctx.session, ctx.author.id, ctx.guild.id)
        text = ["{}'s resources:".format(character.name)]
        for resource in character.resources:
            text.append(str(resource))
        await ctx.send('```\n{}\n```'.format('\n'.join(text)))

    @group.command(aliases=['delete'])
    async def remove(self, ctx, *, name: str):
        '''
        Deletes a resource from the character

        Parameters:
        [name] the name of the resource
        '''
        character = get_character(ctx.session, ctx.author.id, ctx.guild.id)

        resource = ctx.session.query(m.Resource)\
            .get((character.id, name))
        if resource is None:
            raise ItemNotFoundError

        ctx.session.delete(resource)
        ctx.session.commit()
        await ctx.send('`{}` removed'.format(str(resource)))


def setup(bot):
    bot.add_cog(ResourceCog(bot))
