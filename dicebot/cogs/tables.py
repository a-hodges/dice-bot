import re
import random

from discord.ext import commands

from . import util
from .util import m

table_expression = re.compile(r'^\s*(?:(\d+)\s*\|\s*)?(.*)\s*$')


class TableCategory (util.Cog):
    @commands.command()
    async def choose(self, ctx, *, table: str):
        '''
        Randomly choose an item from a list

        This command has special formatting:
        Starting on the line after the command name, each line is an item
        Items can have a 'weight' by putting a number followed by a pipe `|` at the beginning of the line
        Lines without a specified weight have a weight of 1

        e.x. (would have a 25% chance of Item One, a 50% chance of Item Two, and a 25% chance of Item Three):
        ;choose
        Item one
        2 | Item two
        Item three
        '''
        options = []
        for line in table.splitlines():
            match = table_expression.match(line)
            if match:
                count, item = match.groups()
                count = 1 if count is None else int(count)
                options.extend([item] * count)
            else:
                raise Exception('Misformatted item: {}'.format(line))
        final = random.choice(options)
        await util.send_embed(ctx, author=False, fields=[('Randomly chosen:', final)])


def setup(bot):
    bot.add_cog(TableCategory(bot))
