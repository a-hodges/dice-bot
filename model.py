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
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


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


class Character (Base):
    '''
    Character data
    '''
    __tablename__ = 'characters'

    id = Column(
        Integer,
        primary_key=True,
        doc='An autonumber id')
    name = Column(
        String(64),
        nullable=False,
        doc='The name of the character')
    server = Column(
        Integer,
        nullable=False,
        doc='The server the character is on')
    user = Column(
        BigInteger,
        doc='The id of the user of the character')

    __table_args__ = (
        UniqueConstraint(name, server),
        Index('_character_index', server, user, unique=True),
    )

    resources = relationship(
        'Resource',
        order_by='Resource.name',
        back_populates='character')
    rolls = relationship(
        'Roll',
        order_by='Roll.name',
        back_populates='character')
    constants = relationship(
        'Constant',
        order_by='Constant.name',
        back_populates='character')
    initiatives = relationship(
        'Initiative',
        order_by='Initiative.channel',
        back_populates='character')
    inventory = relationship(
        'Item',
        order_by='Item.name',
        back_populates='character')

    def __str__(self):
        return '`{}`'.format(self.name)


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

    character_id = Column(
        Integer,
        ForeignKey('characters.id'),
        primary_key=True,
        doc='Character foreign key')
    name = Column(
        String(64),
        primary_key=True,
        doc='Resource name')
    max = Column(
        Integer,
        doc='The maximum number of uses of the resource')
    current = Column(
        Integer,
        doc='The current remaining uses of the resource')
    recover = Column(
        Enum(Rest),
        doc='How the character recovers the resource')

    character = relationship(
        'Character',
        foreign_keys=[character_id],
        back_populates='resources')

    def __str__(self):
        ret = '`{0.name}: {0.current}/{0.max}'.format(self)
        if self.recover != Rest.other:
            ret += ' per {} rest'.format(self.recover.name)
        ret += '`'
        return ret


class Roll (Base):
    '''
    Character rolls to store
    '''
    __tablename__ = 'rolls'

    character_id = Column(
        Integer,
        ForeignKey('characters.id'),
        primary_key=True,
        doc='Character foreign key')
    name = Column(
        String(64),
        primary_key=True,
        doc='Roll name')
    expression = Column(
        String,
        doc='The dice expression to roll')

    character = relationship(
        'Character',
        foreign_keys=[character_id],
        back_populates='rolls')

    def __str__(self):
        return '`{0.name}: {0.expression}`'.format(self)


class Constant (Base):
    '''
    Character values to store
    '''
    __tablename__ = 'constants'

    character_id = Column(
        Integer,
        ForeignKey('characters.id'),
        primary_key=True,
        doc='Character foreign key')
    name = Column(
        String(64),
        primary_key=True,
        doc='Constant name')
    value = Column(
        Integer,
        doc='The value of the constant')

    character = relationship(
        'Character',
        foreign_keys=[character_id],
        back_populates='constants')

    def __str__(self):
        return '`{0.name}: {0.value}`'.format(self)


class Initiative (Base):
    '''
    Manages character initiative by channel
    '''
    __tablename__ = 'initiative'

    character_id = Column(
        Integer,
        ForeignKey('characters.id'),
        primary_key=True,
        doc='Character foreign key')
    channel = Column(
        BigInteger,
        primary_key=True,
        doc='Channel id')
    value = Column(
        Integer,
        doc='The initiative roll')

    character = relationship(
        'Character',
        foreign_keys=[character_id],
        back_populates='initiatives')

    def __str__(self):
        return '`{0.character.name}: {0.value}`'.format(self)


class Item (Base):
    '''
    Character inventory
    '''
    __tablename__ = 'items'

    id = Column(
        Integer,
        primary_key=True,
        doc='An autonumber id')
    character_id = Column(
        Integer,
        ForeignKey('characters.id'),
        nullable=False,
        doc='Character foreign key')
    name = Column(
        String(64),
        nullable=False,
        doc='Item name')
    number = Column(
        Integer,
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
        ret = '{0.name}: {0.current}'.format(self)
        if self.description:
            ret += '\n' + self.description
        return '`{}`'.format(ret)


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
