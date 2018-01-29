import discord
from discord.ext import commands
from sqlalchemy.exc import IntegrityError

from . import util
from .util import m


class CharacterCog (util.Cog):
    @commands.group('character', aliases=['char'], invoke_without_command=True)
    async def group(self, ctx):
        '''
        Manage character data
        '''
        raise util.invalid_subcommand(ctx)

    @group.command()
    async def create(self, ctx, *, name: str):
        '''
        Creates a character then claims it

        Parameters:
        [name*] is the name of the character to associate
        '''
        name = util.strip_quotes(name)

        character = ctx.session.query(m.Character)\
            .filter_by(name=name, server=str(ctx.guild.id)).one_or_none()

        if character is None:
            character = m.Character(name=name, server=str(ctx.guild.id))
            ctx.session.add(character)
            ctx.session.commit()
            await ctx.send('Creating character: {}'.format(name))

        await ctx.invoke(self.claim, name=name)

    @group.command()
    async def claim(self, ctx, *, name: str):
        '''
        Associates user with a character
        It is highly encouraged to change your nickname to match the character
        A user can only be associated with 1 character at a time
        The character must be created first with the create command

        Parameters:
        [name*] is the name of the character to associate
        '''
        name = util.strip_quotes(name)

        character = ctx.session.query(m.Character)\
            .filter_by(name=name, server=str(ctx.guild.id)).one_or_none()

        if character is not None:
            if character.user is None:
                user = ctx.session.query(m.Character)\
                    .filter_by(user=str(ctx.author.id), server=str(ctx.guild.id)).one_or_none()
                if user is not None:
                    user.user = None
                    ctx.session.commit()
                    await ctx.send('{} is no longer playing as {}'.format(ctx.author.mention, str(user)))

                character.user = str(ctx.author.id)
                ctx.session.commit()
                await ctx.send('{} is {}'.format(ctx.author.mention, str(character)))
            else:
                raise Exception('Someone else is using {}'.format(str(character)))
        else:
            raise Exception('There is no character named {}'.format(name))

    @commands.command()
    async def iam(self, ctx, *, name: str):
        '''
        Associates a user with a character
        See `character claim` for more information

        Parameters:
        [name*] is the name of the character to associate
        '''
        await ctx.invoke(self.claim, name=name)

    @group.command(ignore_extra=False)
    async def unclaim(self, ctx):
        '''
        Removes a character association
        '''
        character = ctx.session.query(m.Character)\
            .filter_by(user=str(ctx.author.id), server=str(ctx.guild.id)).one_or_none()
        if character is not None:
            character.user = None
            ctx.session.commit()
            await ctx.send('{} is no longer playing as {}'.format(ctx.author.mention, str(character)))
        else:
            raise util.NoCharacterError

    @commands.command(ignore_extra=False)
    async def whois(self, ctx, user: discord.Member):
        '''
        Retrieves character information for a user

        Parameters:
        [user] @mention the user
        '''
        character = util.get_character(ctx.session, user.id, ctx.guild.id)
        await ctx.send('{} is {}'.format(user.mention, str(character)))

    @group.command()
    async def rename(self, ctx, *, name: str):
        '''
        Changes the character's name

        Parameters:
        [name*] the new name
        '''
        name = util.strip_quotes(name)

        try:
            character = util.get_character(ctx.session, ctx.author.id, ctx.guild.id)
            original_name = character.name
            character.name = name
            ctx.session.commit()
            await ctx.send("{} has changed {}'s name to {}".format(ctx.author.mention, original_name, name))
        except IntegrityError:
            ctx.session.rollback()
            raise Exception('There is already a character with that name')

    @group.command(ignore_extra=False)
    async def list(self, ctx):
        '''
        Lists all of the characters for this server
        '''
        characters = ctx.session.query(m.Character)\
            .filter_by(server=str(ctx.guild.id)).all()
        pages = util.item_paginator(characters, header='All characters')
        await util.send_pages(ctx, pages)

    def recover_resources(self, ctx, character, rest):
        '''
        Helper function for recovering resources
        '''
        for resource in character.resources:
            if resource.recover == m.Rest.long and rest == 'long':
                resource.current = resource.max
            elif resource.recover == m.Rest.short:
                resource.current = resource.max
        ctx.session.commit()

    @commands.command(ignore_extra=False)
    async def rest(self, ctx, rest: str):
        '''
        Take a rest
        A short rest recovers only short rest resources
        A long rest recovers both long and short rest resources

        Parameters:
        [rest] should be short|long
        '''
        if rest not in ['short', 'long']:
            raise commands.BadArgument('Bad argument: rest')
        character = util.get_character(ctx.session, ctx.author.id, ctx.guild.id)

        if character:
            self.recover_resources(ctx, character, rest)
            await ctx.send('{} has taken a {} rest, resources recovered'.format(str(character), rest))
        else:
            raise util.NoCharacterError

    @commands.command(ignore_extra=False)
    @commands.has_permissions(administrator=True)
    async def restall(self, ctx, rest: str):
        '''
        Have all characters on the server rest
        Can only be done by an administrator

        Parameters:
        [rest] should be short|long
        '''
        if rest not in ['short', 'long']:
            raise commands.BadArgument('Bad argument: rest')
        characters = ctx.session.query(m.Character)\
            .filter_by(server=str(ctx.guild.id)).all()

        for character in characters:
            self.recover_resources(ctx, character, rest)

        await ctx.send('All characters have taken a {} rest, resources recovered'.format(rest))

    @group.command(ignore_extra=False)
    @commands.has_permissions(administrator=True)
    async def forceunclaim(self, ctx, user: discord.Member):
        '''
        Forcibly removes a user's association with a character
        Can only be done by an administrator

        Parameters:
        [user] @mention the user
        '''
        character = util.get_character(ctx.session, user.id, ctx.guild.id)
        character.user = None
        ctx.session.commit()
        await ctx.send('{} is no longer playing as {}'.format(user.mention, str(character)))

    @group.command(ignore_extra=False)
    @commands.has_permissions(administrator=True)
    async def kill(self, ctx, name: str, confirmation: str):
        '''
        Deletes a character
        This is permanent and removes all associated attributes!
        Can only be done by an administrator

        Parameters:
        [name] the name of the character to delete
        [confirmation] enter `100%` to confirm that you want to delete the character permanently
        '''
        if confirmation == '100%':
            character = ctx.session.query(m.Character)\
                .filter_by(name=name, server=str(ctx.guild.id)).one_or_none()
            if character is not None:
                for attribute in character.attributes:
                    for item in getattr(character, attribute):
                        ctx.session.delete(item)
                ctx.session.commit()
                ctx.session.delete(character)
                ctx.session.commit()
                await ctx.send('{} is dead'.format(str(character)))
            else:
                raise Exception('No character named {}'.format(name))
        else:
            raise Exception('Please confirm deletion correctly')


def setup(bot):
    bot.add_cog(CharacterCog(bot))
