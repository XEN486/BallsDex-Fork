import logging
import random
import sys
from typing import TYPE_CHECKING, Dict
from dataclasses import dataclass, field

import discord
from discord import app_commands
from discord.ext import commands

import asyncio
import io
import re

from ballsdex.core.models import Ball
from ballsdex.core.models import balls as countryballs
from ballsdex.settings import settings

from ballsdex.core.utils.transformers import BallInstanceTransform
from ballsdex.packages.battle.xe_battle_lib import (
    BattleBall,
    BattleInstance,
    gen_battle,
)

from ballsdex.core.image_generator.image_gen import draw_card

if TYPE_CHECKING:
    from ballsdex.core.bot import BallsDexBot
log = logging.getLogger("ballsdex.packages.merge")

def gen_name(name1, name2):
    if len(name1) > len(name2):
        oldn = name2
        name2 = name1
        name1 = oldn
    if " " in name1:
        prefix = name1.split()[0]
        suffix = name2
        return prefix + " " + suffix
    else:
        return name1 + name2[len(name1):]

def gen_ability_name(ability1, ability2):
    half1 = len(ability1) // 2
    half2 = len(ability2) // 2

    return ability1[:half1]+ ability2[half2:]

def extract_components(ability: str):
    # Extract named countries/entities
    countries = re.findall(r'[A-Z][a-z]+', ability)
    
    effects = ['damage', 'change', 'boost', 'reflect', 'disable', 'shift', 'modify']
    conditions = ['if', 'while', 'when', 'until', 'and']
    actions = ['can change', 'takes', 'deals', 'modifies', 'limits', 'affects']

    ability_effects = [effect for effect in effects if effect in ability]
    ability_actions = [action for action in actions if action in ability]
    condition_phrases = re.findall(r'(if|while|when|until).*', ability, re.IGNORECASE)

    return {
        'countries': countries,
        'effects': ability_effects,
        'actions': ability_actions,
        'conditions': condition_phrases
    }

def gen_ability_desc(ability1: str, ability2: str) -> str:
    components1 = extract_components(ability1)
    components2 = extract_components(ability2)

    combined_countries = random.sample(
        components1['countries'] + components2['countries'],
        min(2, len(components1['countries'] + components2['countries']))
    )
    
    combined_effect = random.choice(components1['effects'] + components2['effects']) if components1['effects'] + components2['effects'] else 'damage'
    combined_action = random.choice(components1['actions'] + components2['actions']) if components1['actions'] + components2['actions'] else 'affects'

    if components1['conditions'] and components2['conditions']:
        combined_condition = random.choice(components1['conditions']) + " and " + random.choice(components2['conditions'])
    elif components1['conditions']:
        combined_condition = random.choice(components1['conditions'])
    elif components2['conditions']:
        combined_condition = random.choice(components2['conditions'])
    else:
        combined_condition = "under specific conditions"

    if len(combined_countries) == 2:
        new_ability = (
            f"If {combined_countries[0]} is in play and {combined_countries[1]} is not, "
            f"then {combined_action} will {combined_effect} all targets, "
            f"{combined_condition}."
        )
    else:
        new_ability = (
            f"When {combined_countries[0]} is involved, "
            f"{combined_action} will {combined_effect} the opponent, "
            f"{combined_condition}."
        )

    return new_ability

class Merge(commands.GroupCog):
    """
    Merge multiple countryballs!
    """

    def __init__(self, bot: "BallsDexBot"):
        self.bot = bot

    @app_commands.command()
    async def merge(self, interaction: discord.Interaction, ball1: BallInstanceTransform, ball2: BallInstanceTransform):
        """
        Merge two countryballs together.
        """

        name = gen_name(ball1.countryball.short_name, ball2.countryball.short_name)
        health = (ball1.countryball.health + ball2.countryball.health) // 2
        attack = (ball1.countryball.attack + ball2.countryball.attack) // 2
        economy = ball1.countryball.economy
        ability = gen_ability_name(ball1.countryball.capacity_name, ball2.countryball.capacity_name)
        desc = gen_ability_desc(ball1.countryball.capacity_description, ball2.countryball.capacity_description)

        newball = ball1
        newball.countryball.short_name = name
        newball.countryball.health = health
        newball.countryball.attack = attack
        newball.countryball.capacity_name = ability
        newball.countryball.capacity_description = desc

        card = draw_card(newball)

        with io.BytesIO() as image_binary:
            card.save(image_binary, 'PNG')
            image_binary.seek(0)
            await interaction.response.send_message(file=discord.File(image_binary, filename='card.png'))
        
