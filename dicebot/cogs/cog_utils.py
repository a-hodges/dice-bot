from discord.ext import commands


async def send_pages(ctx, paginator):
    for page in paginator.pages:
        await ctx.send(page)


def item_paginator(items, header=None):
    paginator = commands.Paginator(prefix='', suffix='')
    if header:
        paginator.add_line(header)
    for item in items:
        paginator.add_line(str(item))
    return paginator


def desc_paginator(items, header=None):
    paginator = commands.Paginator(prefix='', suffix='')
    if header:
        paginator.add_line(header)
    for item in items:
        paginator.add_line('***{}***'.format(str(item)))
        if item.description:
            for line in item.description.splitlines():
                paginator.add_line(line)
    return paginator


def strip_quotes(arg):
    if len(arg) >= 2 and arg.startswith('"') and arg.endswith('"'):
        arg = arg[1:-1]
    return arg
