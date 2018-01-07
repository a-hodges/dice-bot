import model as m


class BotError (Exception):
    pass


class NoCharacterError (BotError):
    pass


class ItemNotFoundError (BotError):
    def __init__(self, value=None):
        self.value = value


class Cog:
    def __init__(self, bot):
        self.bot = bot


def get_character(session, userid, server):
    '''
    Gets a character based on their user
    '''
    character = session.query(m.Character)\
        .filter_by(user=str(userid), server=str(server)).one_or_none()
    if character is None:
        raise NoCharacterError()
    return character


def sql_update(session, type, keys, values):
    '''
    Updates a sql object
    '''
    obj = session.query(type)\
        .filter_by(**keys).one_or_none()
    if obj is not None:
        for value in values:
            setattr(obj, value, values[value])
    else:
        values = values.copy()
        values.update(keys)
        obj = type(**values)
        session.add(obj)

    session.commit()

    return obj
