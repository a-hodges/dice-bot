#!/usr/bin/env python3

import enum

from sqlalchemy import (
    Column,
    String,
    Integer,
    BigInteger,
    Boolean,
    Enum,
    ForeignKey,
)
from sqlalchemy.orm import relationship
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
        unique=True,
        doc='The name of the character')
    user = Column(
        BigInteger,
        unique=True,
        doc='The id of the user of the character')

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

    def __str__(self):
        return self.name


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
        ret = '{0.name}: {0.current}/{0.max}'.format(self)
        if self.recover != Rest.other:
            ret += ' per {} rest'.format(self.recover.name)
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
        return '{0.name}: {0.expression}'.format(self)


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
        return '{0.name}: {0.value}'.format(self)


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
        String(64),
        primary_key=True,
        doc='Channel name')
    value = Column(
        Integer,
        doc='The initiative roll')

    character = relationship(
        'Character',
        foreign_keys=[character_id],
        back_populates='initiatives')

    def __str__(self):
        return '{0.character.name}: {0.value}'.format(self)
