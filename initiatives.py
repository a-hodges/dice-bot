from discord.ext import commands
from sqlalchemy.orm.exc import NoResultFound

import model as m
from util import Cog, do_roll, get_character, sql_update, ItemNotFoundError


class InitiativeCog (Cog):
    @commands.group('initiative', invoke_without_command=True)
    async def group(self, ctx):
        '''
        Manage initiative by channel
        '''
        await ctx.send('Invalid subcommand')

    @group.command(aliases=['set', 'update'])
    async def add(self, ctx, *, value: int):
        '''
        Set initiative

        Parameters:
        [value] the initiative to store
        '''
        character = get_character(ctx.session, ctx.author.id, ctx.guild.id)

        initiative = sql_update(ctx.session, m.Initiative, {
            'character': character,
            'channel': ctx.channel.id,
        }, {
            'value': value,
        })

        await ctx.send('Initiative {} added'.format(str(initiative)))

    @group.command()
    async def roll(self, ctx, *, expression: str):
        '''
        Roll initiative using the notation from the roll command

        Parameters:
        [expression] either the expression to roll or the name of a stored roll
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
        try:
            initiative = ctx.session.query(m.Initiative)\
                .filter_by(character=character, channel=ctx.channel.id).one()
            await ctx.send(str(initiative))
        except NoResultFound:
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

        try:
            channel = ctx.channel.id
            initiative = ctx.session.query(m.Initiative)\
                .filter_by(character=character, channel=channel).one()
        except NoResultFound:
            raise ItemNotFoundError

        ctx.session.delete(initiative)
        ctx.session.commit()
        await ctx.send('Initiative removed')

    @group.command(aliases=['removeall', 'deleteall'])
    @commands.has_role('DM')
    async def endcombat(self, ctx):
        '''
        Removes all initiative entries for the current channel
        '''
        ctx.session.query(m.Initiative)\
            .filter_by(channel=ctx.channel.id).delete(False)


def setup(bot):
    bot.add_cog(InitiativeCog(bot))
