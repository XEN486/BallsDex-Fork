from dataclasses import dataclass, field
import random


@dataclass
class BattleBall:
    name: str
    owner: str
    health: int
    attack: int
    dead: bool = False


@dataclass
class BattleInstance:
    p1_balls: list = field(default_factory=lambda: [])
    p2_balls: list = field(default_factory=lambda: [])
    winner: str = ""


def attack(current_ball, enemy_balls):
    enemy = random.choice(enemy_balls)

    attack_dealt = int(current_ball.attack * random.uniform(0.5, 1.5))
    enemy.health -= attack_dealt

    if enemy.health <= 0:
        enemy.health = 0
        enemy.dead = True
    if enemy.dead:
        gen_text = f"{current_ball.owner}'s {current_ball.name} has killed {enemy.owner}'s {enemy.name}"
    else:
        gen_text = f"{current_ball.owner}'s {current_ball.name} has dealt {attack_dealt} damage to {enemy.owner}'s {enemy.name}"
    return gen_text


def gen_battle(battle: BattleInstance):
    while any(ball for ball in battle.p1_balls if not ball.dead) and any(
        ball for ball in battle.p2_balls if not ball.dead
    ):
        alive_p1_balls = [ball for ball in battle.p1_balls if not ball.dead]
        for ball in alive_p1_balls:
            yield attack(ball, battle.p2_balls)
        alive_p2_balls = [ball for ball in battle.p2_balls if not ball.dead]
        for ball in alive_p2_balls:
            yield attack(ball, battle.p1_balls)
    if all(ball.dead for ball in battle.p1_balls):
        battle.winner = battle.p2_balls[0].owner
    if all(ball.dead for ball in battle.p2_balls):
        battle.winner = battle.p1_balls[0].owner
