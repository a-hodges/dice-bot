from discord.ext import commands

from . import util
from .util import m


class TimerCategory (util.Cog):
    @commands.group('timer', aliases=['t'], invoke_without_command=True)
    async def group(self, ctx, *, input: str):
        '''
        Manages character timers

        Timers help track values that change over time such as countdowns
        The timer changes by delta when `t tick` or `endturn` are used
        '''
        try:
            number, name = input.split(maxsplit=1)
            number = int(number)
        except ValueError:
            raise util.invalid_subcommand(ctx)
        await ctx.invoke(self.plus, number, name=name)

    @group.command(aliases=['update'], ignore_extra=False)
    async def add(self, ctx, name: str, initial: int, delta: int=-1):
        '''
        Adds or changes a character resource
        Parameters:
        [name] the name of the new timer
        [initial] the value to start the timer at
        [delta] the change every tick. defaults to -1
        '''
        character = util.get_character(ctx.session, ctx.author.id, ctx.guild.id)

        timer = util.sql_update(ctx.session, m.Timer, {
            'character': character,
            'name': name,
        }, {
            'initial': initial,
            'delta': delta,
        })

        await util.send_embed(ctx, description='{} now has {}'.format(str(character), str(timer)))

    @group.command('+')
    async def plus(self, ctx, number: int, *, name: str):
        '''
        Increase the value of a timer
        A space is not required between the + and the number argument
        Parameters:
        [number] the value to increase the timer by
        [name*] the name of the timer
        '''
        name = util.strip_quotes(name)

        character = util.get_character(ctx.session, ctx.author.id, ctx.guild.id)

        timer = ctx.session.query(m.Timer)\
            .filter_by(character_id=character.id, name=name).one_or_none()
        if timer is None:
            raise util.ItemNotFoundError(name)
        if timer.value is None:
            raise Exception("{}'s {} is not running".format(str(character), timer.name))

        prev = timer.value
        timer.value = prev + number
        ctx.session.commit()
        description = "{}'s {}: `{} => {}`".format(
            str(character), timer.name, prev, timer.value)
        await util.send_embed(ctx, description=description)

    @group.command('-')
    async def minus(self, ctx, number: int, *, name: str):
        '''
        Decrease the value of a timer
        A space is not required between the - and the number argument
        Parameters:
        [number] the value to decrease the timer by
        [name*] the name of the timer
        '''
        name = util.strip_quotes(name)

        await ctx.invoke(self.plus, -number, name=name)

    @group.command(ignore_extra=False)
    async def set(self, ctx, name: str, value: int):
        '''
        Sets the current value of a timer
        Also starts the timer if it is not running
        Parameters:
        [name] the name of the time
        [value] the new value of the timer
        '''
        character = util.get_character(ctx.session, ctx.author.id, ctx.guild.id)

        timer = ctx.session.query(m.Timer)\
            .filter_by(character_id=character.id, name=name).one_or_none()
        if timer is None:
            raise util.ItemNotFoundError(name)

        prev = timer.value
        if prev is None:
            prev = timer.initial
        timer.value = value
        ctx.session.commit()

        description = "{}'s {}: `{} => {}`".format(
            str(character), timer.name, prev, timer.value)
        await util.send_embed(ctx, description=description)

    @group.command(aliases=['reset'], ignore_extra=False)
    async def start(self, ctx, *, name: str):
        '''
        Starts the specified timer with the initial value
        '''
        character = util.get_character(ctx.session, ctx.author.id, ctx.guild.id)

        timer = ctx.session.query(m.Timer)\
            .filter_by(character_id=character.id, name=name).one_or_none()
        if timer is None:
            raise util.ItemNotFoundError(name)

        timer.value = timer.initial
        ctx.session.commit()

        description = "{}'s {} started at {}".format(str(character), timer.name, timer.value)
        await util.send_embed(ctx, description=description)

    @group.command(ignore_extra=False)
    async def stop(self, ctx, *, name: str):
        '''
        Stops the specified timer, removing its current value
        '''
        character = util.get_character(ctx.session, ctx.author.id, ctx.guild.id)

        timer = ctx.session.query(m.Timer)\
            .filter_by(character_id=character.id, name=name).one_or_none()
        if timer is None:
            raise util.ItemNotFoundError(name)

        timer.value = None
        ctx.session.commit()

        description = "{}'s {} stopped".format(str(character), timer.name)
        await util.send_embed(ctx, description=description)

    @group.command(ignore_extra=False)
    async def stopall(self, ctx):
        '''
        Stops all timers for the character
        '''
        character = util.get_character(ctx.session, ctx.author.id, ctx.guild.id)

        for timer in character.timers:
            if timer.value is not None:
                timer.value = None
        ctx.session.commit()

        description = "All of {}'s timers are stopped".format(str(character))
        await util.send_embed(ctx, description=description)

    @group.command(ignore_extra=False)
    async def tick(self, ctx):
        '''
        Changes all running timers by their deltas
        '''
        character = util.get_character(ctx.session, ctx.author.id, ctx.guild.id)

        description = ''

        for timer in character.timers:
            if timer.value is not None:
                prev = timer.value
                timer.value += timer.delta
                description += "{}'s {} ({:+}): `{} => {}`\n".format(
                    str(character), timer.name, timer.delta, prev, timer.value)
        ctx.session.commit()

        description += "{}'s turn is over".format(str(character))

        await util.send_embed(ctx, description=description)

    @commands.command(ignore_extra=False)
    async def endturn(self, ctx):
        '''
        Changes all running timers by their deltas
        '''
        await ctx.invoke(self.tick)

    @group.command()
    async def check(self, ctx, *, name: str):
        '''
        Checks the status of a timer
        Parameters:
        [name*] the name of the timer
        '''
        name = util.strip_quotes(name)

        character = util.get_character(ctx.session, ctx.author.id, ctx.guild.id)
        timer = ctx.session.query(m.Timer)\
            .filter_by(character_id=character.id, name=name).one_or_none()
        if timer is None:
            raise util.ItemNotFoundError(name)
        await util.send_embed(ctx, description=str(timer))

    @group.command(ignore_extra=False)
    async def list(self, ctx):
        '''
        Lists all of a character's timers
        '''
        character = util.get_character(ctx.session, ctx.author.id, ctx.guild.id)
        await util.inspector(ctx, character, 'timers')

    @group.command(aliases=['delete'])
    async def remove(self, ctx, *, name: str):
        '''
        Deletes a timer from the character
        Parameters:
        [name*] the name of the timer
        '''
        name = util.strip_quotes(name)

        character = util.get_character(ctx.session, ctx.author.id, ctx.guild.id)

        timer = ctx.session.query(m.Timer)\
            .filter_by(character_id=character.id, name=name).one_or_none()
        if timer is None:
            raise util.ItemNotFoundError(name)

        ctx.session.delete(timer)
        ctx.session.commit()
        await util.send_embed(ctx, description='{} removed'.format(str(timer)))

    @group.command()
    async def inspect(self, ctx, *, name: str):
        '''
        Lists the timers for a specified character
        Parameters:
        [name*] the name of the character to inspect
        '''
        name = util.strip_quotes(name)

        await util.inspector(ctx, name, 'timers')


def setup(bot):
    bot.add_cog(TimerCategory(bot))
