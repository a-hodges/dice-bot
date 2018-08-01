#!/usr/bin/env python3

import enum

from sqlalchemy import (
    Column,
    String,
    Integer,
    BigInteger,
    Enum,
    ForeignKey,
)
from sqlalchemy.orm import relationship
from sqlalchemy.schema import Index, UniqueConstraint
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.ext.declarative import declarative_base

dmkey = 'DM'


class Base:
    def dict(self):
        '''
        Returns a dict of the object
        Primarily for json serialization
        '''
        return {c.key: getattr(self, c.key) for c in self.__mapper__.column_attrs}


Base = declarative_base(cls=Base)


class Config (Base):
    '''
    Stores the configuration values for the application in key value pairs
    '''
    __tablename__ = 'configuration'

    name = Column(
        String(64),
        primary_key=True,
        doc="The setting's name")
    value = Column(
        'setting', String,
        doc="The setting's value")


class Prefix (Base):
    '''
    Stores the prefixes for servers
    '''
    __tablename__ = 'prefixes'

    server = Column(
        String(64),
        primary_key=True,
        doc='The server id for the prefix')
    prefix = Column(
        String(64),
        doc='The prefix for the server')


class Character (Base):
    '''
    Character data
    '''
    __tablename__ = 'characters'

    id = Column(
        BigInteger,
        primary_key=True,
        doc='An autonumber id')
    name = Column(
        String(64),
        nullable=False,
        doc='The name of the character')
    server = Column(
        String(64),
        nullable=False,
        doc='The server the character is on')
    user = Column(
        String(64),
        doc='The id of the user of the character')

    @hybrid_property
    def dm_character(self):
        return (self.user != None) & (self.user == dmkey)  # noqa: E711

    __table_args__ = (
        UniqueConstraint(name, server),
        Index('_character_index', server, user, unique=True, postgresql_where=(user != dmkey)),
    )

    resources = relationship(
        'Resource',
        order_by='Resource.name',
        back_populates='character')
    rolls = relationship(
        'Roll',
        order_by='Roll.name',
        back_populates='character')
    variables = relationship(
        'Variable',
        order_by='Variable.name',
        back_populates='character')
    inventory = relationship(
        'Item',
        order_by='Item.name',
        back_populates='character')
    spells = relationship(
        'Spell',
        order_by='Spell.level,Spell.name',
        back_populates='character')
    information = relationship(
        'Information',
        order_by='Information.name',
        back_populates='character')
    timers = relationship(
        'Timer',
        order_by='Timer.name',
        back_populates='character')

    attributes = [
        'resources',
        'rolls',
        'variables',
        'inventory',
        'spells',
        'information',
    ]

    def __str__(self):
        return str(self.name)


class Rest (enum.Enum):
    r"""
    The types of rest that can be taken
    """
    short = 1
    long = 2
    other = 3


class Resource (Base):
    '''
    Character resources, limited use abilities/items
    '''
    __tablename__ = 'resources'

    id = Column(
        BigInteger,
        primary_key=True,
        doc='An autonumber id')
    character_id = Column(
        BigInteger,
        ForeignKey('characters.id'),
        nullable=False,
        doc='Character foreign key')
    name = Column(
        String(64),
        nullable=False,
        doc='Resource name')
    max = Column(
        Integer,
        nullable=False, default=1,
        doc='The maximum number of uses of the resource')
    current = Column(
        Integer,
        nullable=False, default=1,
        doc='The current remaining uses of the resource')
    recover = Column(
        Enum(Rest),
        nullable=False, default=Rest.other,
        doc='How the character recovers the resource')

    __table_args__ = (
        Index('_resource_index', character_id, name, unique=True),
    )

    character = relationship(
        'Character',
        foreign_keys=[character_id],
        back_populates='resources')

    def __str__(self):
        ret = '{0.name}: {0.current}/{0.max}'.format(self)
        if self.recover != Rest.other:
            ret += ' per {} rest'.format(self.recover.name)
        return ret


class Roll (Base):
    '''
    Character rolls to store
    '''
    __tablename__ = 'rolls'

    id = Column(
        BigInteger,
        primary_key=True,
        doc='An autonumber id')
    character_id = Column(
        BigInteger,
        ForeignKey('characters.id'),
        nullable=False,
        doc='Character foreign key')
    name = Column(
        String(64),
        nullable=False,
        doc='Roll name')
    expression = Column(
        String,
        doc='The dice expression to roll')

    __table_args__ = (
        Index('_roll_index', character_id, name, unique=True),
    )

    character = relationship(
        'Character',
        foreign_keys=[character_id],
        back_populates='rolls')

    def __str__(self):
        return '{0.name}: `{0.expression}`'.format(self)


class Variable (Base):
    '''
    Character values to store
    '''
    __tablename__ = 'variables'

    id = Column(
        BigInteger,
        primary_key=True,
        doc='An autonumber id')
    character_id = Column(
        BigInteger,
        ForeignKey('characters.id'),
        nullable=False,
        doc='Character foreign key')
    name = Column(
        String(64),
        nullable=False,
        doc='Variable name')
    value = Column(
        Integer,
        nullable=False, default=0,
        doc='The value of the variable')

    __table_args__ = (
        Index('_variable_index', character_id, name, unique=True),
    )

    character = relationship(
        'Character',
        foreign_keys=[character_id],
        back_populates='variables')

    def __str__(self):
        return '{0.name}: {0.value}'.format(self)


class Item (Base):
    '''
    Character inventory
    '''
    __tablename__ = 'items'

    id = Column(
        BigInteger,
        primary_key=True,
        doc='An autonumber id')
    character_id = Column(
        BigInteger,
        ForeignKey('characters.id'),
        nullable=False,
        doc='Character foreign key')
    name = Column(
        String(64),
        nullable=False,
        doc='Item name')
    number = Column(
        Integer,
        nullable=False, default=1,
        doc='The quantity of the item possessed')
    description = Column(
        String,
        doc='A short description of the item')

    __table_args__ = (
        Index('_inventory_index', character_id, name, unique=True),
    )

    character = relationship(
        'Character',
        foreign_keys=[character_id],
        back_populates='inventory')

    def __str__(self):
        ret = '{0.name}: {0.number}'.format(self)
        return ret


class Spell (Base):
    '''
    Character spell list
    '''
    __tablename__ = 'spells'

    id = Column(
        BigInteger,
        primary_key=True,
        doc='An autonumber id')
    character_id = Column(
        BigInteger,
        ForeignKey('characters.id'),
        nullable=False,
        doc='Character foreign key')
    name = Column(
        String(64),
        nullable=False,
        doc='Spell name')
    level = Column(
        Integer,
        nullable=False, default=0,
        doc='Spell level')
    description = Column(
        String,
        doc='A short description of the spell')

    __table_args__ = (
        Index('_spell_index', character_id, name, unique=True),
    )

    character = relationship(
        'Character',
        foreign_keys=[character_id],
        back_populates='spells')

    def __str__(self):
        ret = '{0.name} | level {0.level}'.format(self)
        return ret


class Information (Base):
    '''
    Character information
    '''
    __tablename__ = 'information'

    id = Column(
        BigInteger,
        primary_key=True,
        doc='An autonumber id')
    character_id = Column(
        BigInteger,
        ForeignKey('characters.id'),
        nullable=False,
        doc='Character foreign key')
    name = Column(
        String(64),
        nullable=False,
        doc='Info block name')
    description = Column(
        String,
        nullable=False, default='',
        doc='The actual info block')

    __table_args__ = (
        Index('_information_index', character_id, name, unique=True),
    )

    character = relationship(
        'Character',
        foreign_keys=[character_id],
        back_populates='information')

    def __str__(self):
        ret = '{0.name}'.format(self)
        return ret


class Timer (Base):
    '''
    Character timers, values that change over time
    '''
    __tablename__ = 'timers'

    id = Column(
        BigInteger,
        primary_key=True,
        doc='An autonumber id')
    character_id = Column(
        BigInteger,
        ForeignKey('characters.id'),
        nullable=False,
        doc='Character foreign key')
    name = Column(
        String(64),
        nullable=False,
        doc='Resource name')
    delta = Column(
        Integer,
        nullable=False, default=-1,
        doc='The amount this value changes by every tick')
    initial = Column(
        Integer,
        nullable=False, default=10,
        doc='The value for the timer when it starts')
    value = Column(
        Integer,
        doc='The current value of the timer, null for not running')

    __table_args__ = (
        Index('_timer_index', character_id, name, unique=True),
    )

    character = relationship(
        'Character',
        foreign_keys=[character_id],
        back_populates='timers')

    def __str__(self):
        ret = '{0.name} ({0.initial}, {0.delta:+}): {1}'.format(
            self, self.value if self.value is not None else 'stopped')
        return ret


if __name__ == '__main__':
    from operator import attrgetter

    for table in sorted(Base.metadata.tables.values(), key=attrgetter('name')):
        print(table.name)
        for column in table.columns:
            col = '{}: {}'.format(column.name, column.type)

            if column.primary_key and column.foreign_keys:
                col += ' PK & FK'
            elif column.primary_key:
                col += ' PK'
            elif column.foreign_keys:
                col += ' FK'

            if not column.nullable:
                col += ' NOT NULL'

            doc = column.doc
            if isinstance(column.type, Enum):
                doc += ': ' + ', '.join(
                    column.type.python_type.__members__.keys())
            print('\t{}\n\t\t{}'.format(col, doc))
        print()
