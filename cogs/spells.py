from discord.ext import commands
from sqlalchemy.exc import IntegrityError

import model as m
from util import Cog, get_character, sql_update, ItemNotFoundError


class SpellCog (Cog):
    @commands.group('spell', invoke_without_command=True)
    async def group(self, ctx):
        '''
        Manage character spell list
        '''
        message = 'Command "{} {}" is not found'.format(
            ctx.invoked_with, ctx.message.content.split()[1])
        raise commands.CommandNotFound(message)

    @group.command(aliases=['update'])
    async def add(self, ctx, name: str, level: int):
        '''
        Adds/updates a new spell for a character

        Parameters:
        [name] name of spell to store
        [level] the level of the spell
        '''
        character = get_character(ctx.session, ctx.author.id, ctx.guild.id)

        spell = sql_update(ctx.session, m.Spell, {
            'character': character,
            'name': name,
        }, {
            'level': level,
        })

        await ctx.send('`{}` now has `{}`'.format(str(character), str(spell)))

    @group.command()
    async def rename(self, ctx, name: str, * new_name: str):
        '''
        Changes the name of a spell

        Parameters:
        [name] the name of the spell to change
        [new_name] the new name of the spell
        '''
        character = get_character(ctx.session, ctx.author.id, ctx.guild.id)

        spell = ctx.session.query(m.Spell)\
            .filter_by(character_id=character.id, name=name).one_or_none()
        if spell is None:
            raise ItemNotFoundError(name)

        try:
            spell.name = new_name
            ctx.session.commit()
            await ctx.send('`{}` now has `{}`'.format(
                str(character), str(spell)))
        except IntegrityError:
            await ctx.send('`{}` already has a spell named `{}`'.format(
                str(character), new_name))

    @group.command()
    async def setlevel(self, ctx, level: int, *, name: str):
        '''
        Changes the level of a spell

        Parameters:
        [level] the new level of the spell
        [name] the name of the spell
        '''
        character = get_character(ctx.session, ctx.author.id, ctx.guild.id)

        spell = ctx.session.query(m.Spell)\
            .filter_by(character_id=character.id, name=name).one_or_none()
        if spell is None:
            raise ItemNotFoundError(name)

        spell.level = level
        ctx.session.commit()
        await ctx.send('`{}` now has `{}`'.format(str(character), str(spell)))

    @group.command(aliases=['desc'])
    async def description(self, ctx, name: str, *, description: str):
        '''
        Adds or updates a description for a spell

        Parameters:
        [name] the name of the spell
        [description] the new description for the spell
            the description does not need quotes
        '''
        character = get_character(ctx.session, ctx.author.id, ctx.guild.id)

        spell = ctx.session.query(m.Spell)\
            .filter_by(character_id=character.id, name=name).one_or_none()
        if spell is None:
            raise ItemNotFoundError(name)

        spell.description = description
        ctx.session.commit()
        await ctx.send('`{}` now has `{}`'.format(str(character), str(spell)))

    @group.command(aliases=['rmdesc'])
    async def remove_description(self, ctx, *, name: str):
        '''
        Removes a spell's description

        Parameters:
        [name] the name of the spell to remove the description from
        '''
        await self.description.callback(self, ctx, name, description=None)

    @group.command()
    async def check(self, ctx, *, name: str):
        '''
        Checks the status of a spell

        Parameters:
        [name] the name of the spell
        '''
        character = get_character(ctx.session, ctx.author.id, ctx.guild.id)
        spell = ctx.session.query(m.Spell)\
            .filter_by(character_id=character.id, name=name).one_or_none()
        if spell is None:
            raise ItemNotFoundError(name)
        await ctx.send('`{}`'.format(str(spell)))

    @group.command()
    async def list(self, ctx):
        '''
        Lists all of a character's spells
        '''
        character = get_character(ctx.session, ctx.author.id, ctx.guild.id)
        text = ["{}'s spells:".format(character.name)]
        for spell in character.spells:
            text.append(str(spell))
        await ctx.send('```\n{}\n```'.format('\n\n'.join(text)))

    @group.command(aliases=['delete'])
    async def remove(self, ctx, *, name: str):
        '''
        Deletes a spell from the character

        Parameters:
        [name] the name of the spell
        '''
        character = get_character(ctx.session, ctx.author.id, ctx.guild.id)

        spell = ctx.session.query(m.Spell)\
            .filter_by(character_id=character.id, name=name).one_or_none()
        if spell is None:
            raise ItemNotFoundError(name)

        ctx.session.delete(spell)
        ctx.session.commit()
        await ctx.send('`{}` no longer has `{}`'.format(
            str(character), str(spell)))


def setup(bot):
    bot.add_cog(SpellCog(bot))
