from discord.ext import commands
from sqlalchemy.exc import IntegrityError

import model as m
from util import Cog, get_character, ItemNotFoundError


class InventoryCog (Cog):
    @commands.group('inventory', aliases=['inv'], invoke_without_command=True)
    async def group(self, ctx, *, input: str):
        '''
        Manages character inventory
        '''
        try:
            number, name = input.split(maxsplit=1)
            number = int(number)
        except ValueError:
            message = 'Command "{} {}" is not found'.format(
                ctx.invoked_with, ctx.message.content.split()[1])
            raise commands.CommandNotFound(message)
        await self.plus.callback(self, ctx, number, name=name)

    @group.command()
    async def add(self, ctx, name: str, number: int):
        '''
        Adds an item to your inventory

        Parameters:
        [name] the name of the new item
        [number] the number of the item you currently possess
        '''
        character = get_character(ctx.session, ctx.author.id, ctx.guild.id)

        item = m.Item(character_id=character.id, name=name, number=number)
        try:
            ctx.session.add(item)
            ctx.session.commit()
        except IntegrityError:
            ctx.session.rollback()
            item = None

        if item is not None:
            await ctx.send('{} now has {}'.format(
                str(character), str(item)))
        else:
            await ctx.send('{} already has an item named {}'.format(
                str(character), name))

    @group.command()
    async def rename(self, ctx, name: str, *, new_name: str):
        '''
        Changes the name of an inventory item

        Parameters:
        [name] the name of the item to change
        [new_name] the new name of the item
        '''
        character = get_character(ctx.session, ctx.author.id, ctx.guild.id)

        item = ctx.session.query(m.Item)\
            .filter_by(character_id=character.id, name=name).one_or_none()
        if item is None:
            raise ItemNotFoundError(name)

        try:
            item.name = new_name
            ctx.session.commit()
            await ctx.send('{} now has {}'.format(
                str(character), str(item)))
        except IntegrityError:
            ctx.session.rollback()
            await ctx.send('{} already has an item named {}'.format(
                str(character), new_name))

    @group.command(aliases=['desc'])
    async def description(self, ctx, name: str, *, description: str):
        '''
        Adds or updates a description for an item

        Parameters:
        [name] the name of the item
        [description] the new description for the item
            the description does not need quotes
        '''
        character = get_character(ctx.session, ctx.author.id, ctx.guild.id)

        item = ctx.session.query(m.Item)\
            .filter_by(character_id=character.id, name=name).one_or_none()
        if item is None:
            raise ItemNotFoundError(name)

        item.description = description
        ctx.session.commit()
        await ctx.send('{} now has {}'.format(str(character), str(item)))

    @group.command(aliases=['rmdesc'])
    async def remove_description(self, ctx, *, name: str):
        '''
        Removes an item's description

        Parameters:
        [name] the name of the item to remove the description from
        '''
        await self.description.callback(self, ctx, name, description=None)

    @group.command()
    async def has(self, ctx, number: int, *, name: str):
        '''
        Sets the number carried for an item

        Parameters:
        [number] the new quantity of the item
        [name] the name of the item
        '''
        character = get_character(ctx.session, ctx.author.id, ctx.guild.id)

        item = ctx.session.query(m.Item)\
            .filter_by(character_id=character.id, name=name).one_or_none()
        if item is None:
            raise ItemNotFoundError(name)

        item.number = number
        ctx.session.commit()
        await ctx.send('{} now has {}'.format(str(character), str(item)))

    @group.command('+')
    async def plus(self, ctx, number: int, *, name: str):
        '''
        Increases the amount of the item carried

        Parameters:
        [number] the number to increase the item count by
        [name] the name of the item
        '''
        character = get_character(ctx.session, ctx.author.id, ctx.guild.id)

        item = ctx.session.query(m.Item)\
            .filter_by(character_id=character.id, name=name).one_or_none()
        if item is None:
            raise ItemNotFoundError(name)

        item.number += number
        ctx.session.commit()
        await ctx.send('{} now has {}'.format(str(character), str(item)))

    @group.command('-')
    async def minus(self, ctx, number: int, *, name: str):
        '''
        Decreases the amount of the item carried

        Parameters:
        [number] the number to decrease the item count by
        [name] the name of the item
        '''
        await self.plus.callback(self, ctx, -number, name=name)

    @group.command()
    async def check(self, ctx, *, name: str):
        '''
        Checks the status of an item

        Parameters:
        [name] the name of the item
        '''
        character = get_character(ctx.session, ctx.author.id, ctx.guild.id)
        item = ctx.session.query(m.Item)\
            .filter_by(character_id=character.id, name=name).one_or_none()
        if item is None:
            raise ItemNotFoundError(name)
        await ctx.send(str(item))

    @group.command()
    async def list(self, ctx):
        '''
        Lists character's inventory
        '''
        character = get_character(ctx.session, ctx.author.id, ctx.guild.id)
        text = ["{}'s inventory:".format(character.name)]
        for item in character.inventory:
            text.append(str(item))
        await ctx.send('\n'.join(text))

    @group.command(aliases=['delete'])
    async def remove(self, ctx, *, name: str):
        '''
        Removes an item from the character's inventory
        This deletes all of the data associated with the item,
        use the `has` command if you just want to set the number to 0

        Parameters:
        [name] the name of the item
        '''
        character = get_character(ctx.session, ctx.author.id, ctx.guild.id)

        item = ctx.session.query(m.Item)\
            .filter_by(character_id=character.id, name=name).one_or_none()
        if item is None:
            raise ItemNotFoundError(name)

        ctx.session.delete(item)
        ctx.session.commit()
        await ctx.send('{} removed'.format(str(item)))

    @group.command()
    async def inspect(self, ctx, *, name: str):
        '''
        Lists the inventory for a specified character

        Parameters:
        [name] the name of the character to inspect
        '''
        character = ctx.session.query(m.Character)\
            .filter_by(name=name, server=str(ctx.guild.id)).one_or_none()
        if character is None:
            await ctx.send('No character named {}'.format(name))
        else:
            text = ["{}'s inventory:".format(character.name)]
            for item in character.inventory:
                text.append(str(item))
            await ctx.send('\n'.join(text))


def setup(bot):
    bot.add_cog(InventoryCog(bot))
