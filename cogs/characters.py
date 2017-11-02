import discord
from discord.ext import commands
from sqlalchemy.exc import IntegrityError

import model as m
from util import Cog, get_character


class CharacterCog (Cog):
    @commands.command()
    async def iam(self, ctx, *, name: str):
        '''
        Associates user with a character
        It is highly encouraged to change your nickname to match the character
        A user can only be associated with 1 character at a time

        Parameters:
        [name] is the name of the character to associate
        '''
        character = ctx.session.query(m.Character)\
            .filter_by(name=name, server=ctx.guild.id).one_or_none()
        if character is None:
            character = m.Character(name=name, server=ctx.guild.id)
            ctx.session.add(character)
            await ctx.send('Creating character: {}'.format(name))

        if character.user is None:
            character.user = ctx.author.id
            try:
                ctx.session.commit()
                await ctx.send('{} is `{}`'.format(
                    ctx.author.mention, str(character)))
            except IntegrityError:
                await ctx.send(
                    'You are already using a different character')
        else:
            await ctx.send('Someone else is using `{}`'.format(
                str(character)))

    @commands.command()
    async def iamdone(self, ctx):
        '''
        Removes a character association
        '''
        character = ctx.session.query(m.Character)\
            .filter_by(user=ctx.author.id, server=ctx.guild.id).one_or_none()
        if character is not None:
            character.user = None
            await ctx.send('{} is no longer playing as `{}`'.format(
                ctx.author.mention, str(character)))
        else:
            await ctx.send(
                '{} does not have a character to remove'.format(
                    ctx.author.mention))
        ctx.session.commit()

    @commands.command()
    async def whois(self, ctx, *, member: discord.Member):
        '''
        Retrieves character information for a user

        Parameters:
        [user] should be a user on this channel
        '''
        character = get_character(ctx.session, member.id, ctx.guild.id)
        await ctx.send('{} is `{}`'.format(member.mention, str(character)))

    @commands.command()
    async def changename(self, ctx, *, name: str):
        '''
        Changes the character's name

        Parameters:
        [name] the new name
        '''
        try:
            character = get_character(ctx.session, ctx.author.id, ctx.guild.id)
            original_name = character.name
            character.name = name
            ctx.session.commit()
            await ctx.send("{} has changed `{}`'s name to `{}`".format(
                ctx.author.mention, original_name, name))
        except IntegrityError:
            await ctx.send('There is already a character with that name')

    @commands.command()
    async def listcharacters(self, ctx):
        '''
        Lists all of the characters for this server
        '''
        characters = ctx.session.query(m.Character)\
            .filter_by(server=ctx.guild.id).all()
        text = ['All characters:']
        for character in characters:
            text.append(str(character))
        await ctx.send('```\n{}\n```'.format('\n'.join(text)))

    @commands.command()
    async def rest(self, ctx, *, rest: str):
        '''
        Take a rest

        Parameters:
        [type] should be short|long
        '''
        if rest not in ['short', 'long']:
            raise commands.BadArgument('rest')
        # short or long rest
        character = get_character(ctx.session, ctx.author.id, ctx.guild.id)

        if character:
            for resource in character.resources:
                if resource.recover == m.Rest.long and rest == 'long':
                    resource.current = resource.max
                elif resource.recover == m.Rest.short:
                    resource.current = resource.max

            ctx.session.commit()

            await ctx.send(
                '`{}` has taken a {} rest, resources recovered'.format(
                    str(character), rest))
        else:
            await ctx.send('User has no character')


def setup(bot):
    bot.add_cog(CharacterCog(bot))
