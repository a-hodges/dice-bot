from discord.ext import commands

import model as m
from util import Cog, do_roll, get_character, sql_update, ItemNotFoundError


class InitiativeCog (Cog):
    @commands.group('initiative', invoke_without_command=True)
    async def group(self, ctx):
        '''
        Manage initiative by channel
        '''
        await ctx.send('Invalid subcommand')

    @group.command(aliases=['add', 'update', 'roll'])
    async def set(self, ctx, *, expression: str):
        '''
        Set initiative

        Parameters:
        [expression] a roll expression or the value to set
        '''
        character = get_character(ctx.session, ctx.author.id, ctx.guild.id)

        value = await do_roll(ctx, ctx.session, character, expression)

        initiative = sql_update(ctx.session, m.Initiative, {
            'character': character,
            'channel': ctx.channel.id,
        }, {
            'value': value,
        })

        await ctx.send('Initiative {} added'.format(str(initiative)))

    @group.command()
    async def check(self, ctx):
        '''
        Checks the user's initiative for this channel
        '''
        character = get_character(ctx.session, ctx.author.id, ctx.guild.id)
        initiative = ctx.session.query(m.Initiative)\
            .get((character.id, ctx.channel.id))
        if initiative is not None:
            await ctx.send(str(initiative))
        else:
            await ctx.send('No initiative for {}'.format(str(character)))

    @group.command()
    async def list(self, ctx):
        '''
        Lists all initiatives currently stored in this channel
        '''
        initiatives = ctx.session.query(m.Initiative)\
            .filter_by(channel=ctx.channel.id).all()
        text = ['Initiatives:']
        for initiative in initiatives:
            text.append(str(initiative))
        await ctx.send('\n'.join(text))

    @group.command(aliases=['delete'])
    async def remove(self, ctx):
        '''
        Deletes a character's current initiative
        '''
        character = get_character(ctx.session, ctx.author.id, ctx.guild.id)

        initiative = ctx.session.query(m.Initiative)\
            .get((character.id, ctx.channel.id))
        if initiative is None:
            raise ItemNotFoundError

        ctx.session.delete(initiative)
        ctx.session.commit()
        await ctx.send('Initiative removed')

    @group.command(aliases=['deleteall', 'endcombat'])
    @commands.has_role('DM')
    async def removeall(self, ctx):
        '''
        Removes all initiative entries for the current channel
        See also: !endcombat
        '''
        ctx.session.query(m.Initiative)\
            .filter_by(channel=ctx.channel.id).delete(False)
        await ctx.send('All initiatives removed')

    @commands.command()
    @commands.has_role('DM')
    async def endcombat(self, ctx):
        '''
        Removes all initiative entries for the current channel
        See also: !initiative removeall
        '''
        await self.removeall.callback(self, ctx)


def setup(bot):
    bot.add_cog(InitiativeCog(bot))
