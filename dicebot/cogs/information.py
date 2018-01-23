from discord.ext import commands
from sqlalchemy.exc import IntegrityError

from .util import m, Cog, get_character, ItemNotFoundError, send_pages, desc_paginator, strip_quotes


class InformationCog (Cog):
    @commands.group('information', aliases=['info'], invoke_without_command=True)
    async def group(self, ctx):
        '''
        Manages character information
        '''
        message = 'Command "{} {}" is not found'.format(ctx.invoked_with, ctx.message.content.split()[1])
        raise commands.CommandNotFound(message)

    @group.command()
    async def add(self, ctx, name: str, *, description: str):
        '''
        Adds an information block to the character

        Parameters:
        [name] the name of the new information block
        [description*] the text of the information block
        '''
        description = strip_quotes(description)

        character = get_character(ctx.session, ctx.author.id, ctx.guild.id)

        info = m.Information(character_id=character.id, name=name, description=description)
        try:
            ctx.session.add(info)
            ctx.session.commit()
        except IntegrityError:
            ctx.session.rollback()
            info = None

        if info is not None:
            await ctx.send('{} now has {}'.format(str(character), str(info)))
        else:
            await ctx.send('{} already has a information block named {}'.format(str(character), name))

    @group.command(ignore_extra=False)
    async def rename(self, ctx, name: str, new_name: str):
        '''
        Changes the name of an information block

        Parameters:
        [name] the name of the block to change
        [new_name] the new name of the block
        '''
        character = get_character(ctx.session, ctx.author.id, ctx.guild.id)

        info = ctx.session.query(m.Information)\
            .filter_by(character_id=character.id, name=name).one_or_none()
        if info is None:
            raise ItemNotFoundError(name)

        try:
            info.name = new_name
            ctx.session.commit()
            await ctx.send('{} now has {}'.format(str(character), str(info)))
        except IntegrityError:
            ctx.session.rollback()
            await ctx.send('{} already has an information block named {}'.format(str(character), new_name))

    @group.command(aliases=['desc'])
    async def description(self, ctx, name: str, *, description: str):
        '''
        Adds or updates the description for an information block

        Parameters:
        [name] the name of the block
        [description*] the new description for the block
            the description does not need quotes
        '''
        description = strip_quotes(description)

        character = get_character(ctx.session, ctx.author.id, ctx.guild.id)

        info = ctx.session.query(m.Information)\
            .filter_by(character_id=character.id, name=name).one_or_none()
        if info is None:
            raise ItemNotFoundError(name)

        info.description = description
        ctx.session.commit()
        await ctx.send('{} now has {}'.format(str(character), str(info)))

    @group.command(aliases=['rmdesc'])
    async def removedescription(self, ctx, *, name: str):
        '''
        Clears an information block's description

        Parameters:
        [name*] the name of the block to clear the description for
        '''
        name = strip_quotes(name)

        await ctx.invoke(self.description, name, description='')

    @group.command()
    async def check(self, ctx, *, name: str):
        '''
        Shows the information block

        Parameters:
        [name*] the name of the block
        '''
        name = strip_quotes(name)

        character = get_character(ctx.session, ctx.author.id, ctx.guild.id)
        info = ctx.session.query(m.Information)\
            .filter_by(character_id=character.id, name=name).one_or_none()
        if info is None:
            raise ItemNotFoundError(name)
        text = str(info)
        if info.description:
            text += '\n' + info.description
        await ctx.send(text)

    @group.command(ignore_extra=False)
    async def list(self, ctx):
        '''
        Lists character's information
        '''
        character = get_character(ctx.session, ctx.author.id, ctx.guild.id)
        pages = desc_paginator(character.information, header="{}'s information:".format(character.name))
        await send_pages(ctx, pages)

    @group.command(aliases=['delete'])
    async def remove(self, ctx, *, name: str):
        '''
        Removes an information block from the character
        This deletes all of the data associated with the block

        Parameters:
        [name*] the name of the block
        '''
        name = strip_quotes(name)

        character = get_character(ctx.session, ctx.author.id, ctx.guild.id)

        info = ctx.session.query(m.Information)\
            .filter_by(character_id=character.id, name=name).one_or_none()
        if info is None:
            raise ItemNotFoundError(name)

        ctx.session.delete(info)
        ctx.session.commit()
        await ctx.send('{} removed'.format(str(info)))

    @group.command()
    async def inspect(self, ctx, *, name: str):
        '''
        Lists the information for a specified character

        Parameters:
        [name*] the name of the character to inspect
        '''
        name = strip_quotes(name)

        character = ctx.session.query(m.Character)\
            .filter_by(name=name, server=str(ctx.guild.id)).one_or_none()
        if character is None:
            await ctx.send('No character named {}'.format(name))
        else:
            pages = desc_paginator(character.information, header="{}'s information:".format(character.name))
            await send_pages(ctx, pages)


def setup(bot):
    bot.add_cog(InformationCog(bot))
