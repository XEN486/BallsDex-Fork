import logging
import random
import sys
from typing import TYPE_CHECKING
from dataclasses import dataclass, field

import discord
from discord import app_commands
from discord.ext import commands

import io

from ballsdex.core.models import Ball
from ballsdex.core.models import balls as countryballs
from ballsdex.settings import settings

from ballsdex.core.utils.transformers import BallInstanceTransform

from ballsdex.packages.battle.xe_battle_lib import (
    BattleBall,
    BattleInstance,
    gen_battle,
)

if TYPE_CHECKING:
    from ballsdex.core.bot import BallsDexBot

log = logging.getLogger("ballsdex.packages.battle")

@dataclass
class GuildBattle:
    author: discord.Member
    opponent: discord.Member
    battle: BattleInstance = field(default_factory=lambda: BattleInstance())

def gen_deck(balls):
    deck = ""
    for ball in balls:
        deck += f'- {ball.name} (HP: {ball.health} | DMG: {ball.attack})\n'

    return deck

def update_embed(author_balls, opponent_balls, author, opponent):
    embed = discord.Embed(
        title="Countryballs Battle Plan",
        description="Add or remove countryballs you want to propose to the other player using the '/battle add' and '/battle remove' commands. Once you've finished, click the tick button to start the battle.",
        color=discord.Colour.blurple(),
    )

    embed.add_field(
        name=f"{author}'s deck:",
        value=gen_deck(author_balls),
        inline=True
    )
    
    embed.add_field(
        name=f"{opponent}'s deck:",
        value=gen_deck(opponent_balls),
        inline=True
    )

    return embed

class Battle(commands.GroupCog):
    """
    Battle your countryballs!
    """

    def __init__(self, bot: "BallsDexBot"):
        self.bot = bot
        self.battles = {}
        self.interactions = {} # this is stuuuuuuuuuupid but it works!

    async def start_battle(self, interaction: discord.Interaction):
        if (
            interaction.user != self.battles[interaction.guild_id].author
            and interaction.user != self.battles[interaction.guild_id].opponent
        ):
            await interaction.response.send_message("You arent a part of this battle.")
            return
        elif (
            len(self.battles[interaction.guild_id].battle.p1_balls) == 0
            or len(self.battles[interaction.guild_id].battle.p2_balls) == 0
        ):
            await interaction.response.send_message(
                "Both players must add countryballs!"
            )
            return
        
        disabled_button = discord.ui.Button(
            style=discord.ButtonStyle.success,
            emoji="✅",
            label="Start!",
            disabled=True,
        )

        new_view = discord.ui.View()
        new_view.add_item(disabled_button)
        
        log = ""
        for attack_text in gen_battle(self.battles[interaction.guild_id].battle):
            log += attack_text + "\n"

        gbattle = self.battles[interaction.guild_id]
        
        author_deck = gen_deck(gbattle.battle.p1_balls)
        opponent_deck = gen_deck(gbattle.battle.p2_balls)
        
        embed = discord.Embed(
            title = "Countryballs Battle Plan",
            description = f"Battle between {gbattle.author.mention} and {gbattle.opponent.mention}",
            color = discord.Color.green(),
        )
        
        embed.add_field(
            name=f"{gbattle.author}'s deck:",
            value=author_deck,
            inline=True
        )
        
        embed.add_field(
            name=f"{gbattle.opponent}'s deck:",
            value=opponent_deck,
            inline=True
        )
        
        embed.add_field(
            name="Winner:",
            value=gbattle.battle.winner,
            inline=False
        )
        
        embed.set_footer(
            text="Battle log is attached."
        )

        await interaction.response.defer()
        await interaction.message.edit(
            content = f"{gbattle.author.mention} vs {gbattle.opponent.mention}",
            embed = embed,
            view = new_view,
            attachments=[discord.File(io.StringIO(log), filename="battle.log")]
        )

        self.battles[interaction.guild_id] = None
        

    @app_commands.command()
    async def start(self, interaction: discord.Interaction, opponent: discord.Member):
        """
        Start a battle with a chosen user.
        """

        embed = update_embed([], [], interaction.user.name, opponent.name)

        start_button = discord.ui.Button(
            style=discord.ButtonStyle.success,
            emoji="✅",
        )

        start_button.callback = self.start_battle

        view = discord.ui.View()
        view.add_item(start_button)
        
        try:
            if self.battles[interaction.guild_id] != None:
                await interaction.response.send_message(
                    "You cannot create a new battle at this time, as there is already a battle going on in this server."
                )
                return
            else:
                self.battles[interaction.guild_id] = GuildBattle(
                    interaction.user, opponent
                )
        except KeyError:
            self.battles[interaction.guild_id] = GuildBattle(interaction.user, opponent)
        await interaction.response.send_message(
            f"Hey, {opponent.mention}, {interaction.user.name} is proposing a battle with you!",
            embed=embed,
            view=view,
        )

        self.interactions[interaction.guild_id] = interaction
        print(self.interactions)

    @app_commands.command()
    async def add(
        self, interaction: discord.Interaction, countryball: BallInstanceTransform
    ):
        """
        Add a countryball to a battle.
        """
        try:
            battle = self.battles[interaction.guild_id]
        except:
            await interaction.response.send_message(
                "There is no battle going on in the server!"
            )
            return
        if (
            len(self.battles[interaction.guild_id].battle.p1_balls) > 3
            and self.battles[interaction.guild_id].author == interaction.user
        ):
            await interaction.response.send_message(
                "You can only have 3 countryballs in a battle!"
            )
            return
        elif (
            len(self.battles[interaction.guild_id].battle.p2_balls) > 3
            and self.battles[interaction.guild_id].author == opponent.user
        ):
            await interaction.response.send_message(
                "You can only have 3 countryballs in a battle!"
            )
            return
        
        ball = BattleBall(
            countryball.countryball.country,
            interaction.user.name,
            countryball.health,
            countryball.attack,
        )

        # add ball to p1 if we are p1
        if self.battles[interaction.guild_id].author == interaction.user:
            self.battles[interaction.guild_id].battle.p1_balls.append(ball)
            
        # add ball to p2 if we are p2
        elif self.battles[interaction.guild_id].opponent == interaction.user:
            self.battles[interaction.guild_id].battle.p2_balls.append(ball)
            
        # error out if we arent either
        else:
            await interaction.response.send_message("You aren't a part of this battle!")
            return
        
        attack_sign = "+" if countryball.attack_bonus >= 0 else ""
        health_sign = "+" if countryball.health_bonus >= 0 else ""

        await interaction.response.send_message(
            f"Added ``#{countryball.id} {countryball.countryball.country} ({attack_sign}{countryball.attack_bonus}%/{health_sign}{countryball.health_bonus}%)``!"
        )
        
        await self.interactions[interaction.guild_id].edit_original_response(
            embed = update_embed(
                self.battles[interaction.guild_id].battle.p1_balls,
                self.battles[interaction.guild_id].battle.p2_balls,
                self.battles[interaction.guild_id].author,
                self.battles[interaction.guild_id].opponent
            )
        )

        
