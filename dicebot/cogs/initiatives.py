import discord
from discord.ext import commands

import model as m
from util import Cog, get_character, sql_update, ItemNotFoundError
from .rolls import do_roll


class InitiativeCog (Cog):
    @commands.group('initiative', aliases=['init'], invoke_without_command=True)
    async def group(self, ctx):
        '''
        Manage initiative by channel
        '''
        message = 'Command "{} {}" is not found'.format(ctx.invoked_with, ctx.message.content.split()[1])
        raise commands.CommandNotFound(message)

    @group.command(aliases=['add', 'update', 'roll'])
    async def set(self, ctx, *, expression: str):
        '''
        Set initiative

        Parameters:
        [expression] a roll expression or the value to set
        '''
        character = get_character(ctx.session, ctx.author.id, ctx.guild.id)

        value = await do_roll(ctx, ctx.session, character, expression)
        value = int(value)

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
        initiative = ctx.session.query(m.Initiative).get((character.id, ctx.channel.id))
        if initiative is not None:
            await ctx.send(str(initiative))
        else:
            await ctx.send('No initiative for {}'.format(str(character)))

    @group.command()
    async def list(self, ctx, channel: discord.TextChannel):
        '''
        Lists all initiatives currently stored in the specified channel

        Parameters:
        [channel] the channel to list initiative for
        '''
        initiatives = ctx.session.query(m.Initiative)\
            .filter_by(channel=channel.id)\
            .order_by(m.Initiative.value.desc()).all()
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
            raise ItemNotFoundError()

        ctx.session.delete(initiative)
        ctx.session.commit()
        await ctx.send("{}'s initiative removed".format(str(character)))

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
