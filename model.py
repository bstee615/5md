from collections import defaultdict
from ecs_annotated import *
import pytest

SWORD = "SWORD"
ARROW = "ARROW"
JUMP = "JUMP"


def HeroCard():
    me = Entity()
    me.attach(Component("hero_card"))
    return me


def SymbolCard(symbols):
    me = HeroCard()
    me.attach(Component("symbol_count"))
    me.symbol_count.symbols = symbols
    return me


def EnemyCard(name, symbols):
    me = Entity()
    me.attach(Component("meta"))
    me.attach(Component("symbol_count"))
    me.meta.name = name
    me.symbol_count.symbols = symbols
    return me


def BossCard(name, symbols):
    me = Entity()
    me.attach(Component("meta"))
    me.attach(Component("symbol_count"))
    me.meta.name = name
    me.symbol_count.symbols = symbols
    return me


def Hero(name):
    me = Entity()
    me.attach(Component("meta"))
    me.meta.name = name
    return me


class EmitSystem(System):
    def __init__(self, server):
        super().__init__()
        self.subscribe("add_hero")
        self.subscribe("flip_enemy")
        self.subscribe("play_card")
        self.subscribe("clear_play_area")
        self.server = server

    def update(self):
        events = self.pending()
        for ev in events:
            self.server.send(
                {
                    "message": "event",
                    "event": ev,
                }
            )


class HeroCardPositionSystem(System):
    def __init__(self, heroes):
        super().__init__()
        self.subscribe("add_hero")
        self.subscribe("play_card")
        self.subscribe("draw_cards")
        self.subscribe("flip_enemy")
        self.hero_card = {}
        self.card_hero = {}
        self.play_area = []
        self.hand = {}
        self.deck = {}
        self.discard = {}
        for hero in heroes:
            hand = [c.id for c in hero["hand"]]
            deck = [c.id for c in hero["deck"]]
            discard = [c.id for c in hero["discard"]]
            all_cards = hand + deck + discard
            self.hand[hero["id"]] = hand
            self.deck[hero["id"]] = deck
            self.discard[hero["id"]] = discard
            self.hero_card[hero["id"]] = all_cards
            for card in all_cards:
                self.card_hero[card] = hero["id"]

    def update(self):
        events = self.pending()
        for ev in events:
            if ev["type"] == "draw_cards":
                hero = ev["hero"]
                card_limit = 3
                deck = self.deck[hero]
                while len(self.hand[hero]) < card_limit and len(deck) > 0:
                    self.hand[hero].append(deck.pop(0))
            if ev["type"] == "play_card":
                card = ev["card"]
                hero = self.card_hero[card]
                self.inject({"type": "draw_cards", "hero": hero})
                self.hand[hero].remove(card)
                self.play_area.append(card)
            if ev["type"] == "flip_enemy":
                for card in self.play_area:
                    self.discard[self.card_hero[card]].append(card)
                self.play_area = []


class EnemyDeckSystem(System):
    def __init__(self, deck, boss, hero_card_system):
        super().__init__()
        self.subscribe("flip_enemy")
        self.subscribe("play_card")
        self.deck = [c.id for c in deck]
        self.boss = boss.id
        self.hero_card_system = hero_card_system

    @property
    def top_enemy(self):
        if len(self.deck) > 0:
            return self.deck[0]
        else:
            return self.boss

    def update(self):
        events = self.pending()
        for ev in events:
            if ev["type"] == "flip_enemy":
                if len(self.deck) > 0:
                    self.deck.pop(0)
            if ev["type"] == "play_card":
                card = Entity.get(ev["card"])
                symbol_count = set(Entity.filter_id("symbol_count"))
                hero_card = set(Entity.filter_id("hero_card"))
                symbol_cards = symbol_count & hero_card
                cards_on_field = set(self.hero_card_system.play_area)
                symbol_cards_on_field = symbol_cards & cards_on_field
                all_symbols = defaultdict(int)
                for sc in symbol_cards_on_field:
                    sc = Entity.get(sc)
                    for symbol, count in sc.symbol_count.symbols.items():
                        all_symbols[symbol] += count
                enemy_symbols = Entity.get(self.top_enemy).symbol_count.symbols
                died = all(
                    all_symbols[symbol] >= count
                    for symbol, count in enemy_symbols.items()
                )
                if died:
                    self.inject({"type": "flip_enemy"})


@pytest.fixture(autouse=True)
def reset():
    System.reset()
    Entity.reset()


def get_enemy_deck_system(hero_card_position_system=None):
    if hero_card_position_system is None:
        hero_card_position_system = HeroCardPositionSystem([])
    return EnemyDeckSystem(
        [
            EnemyCard("Slime", {SWORD: 2}),
            EnemyCard("Bear", {ARROW: 1}),
            EnemyCard("Skeleton", {JUMP: 1}),
        ],
        BossCard("Baby Barbarian", {SWORD: 2, ARROW: 2, JUMP: 3}),
        hero_card_position_system,
    )


def test_defeat_enemy():
    enemy_deck_system = get_enemy_deck_system()

    assert len(enemy_deck_system.deck) == 3
    assert Entity.get(enemy_deck_system.top_enemy).meta.name == "Slime"
    System.inject({"type": "flip_enemy"})
    System.update_all()
    assert Entity.get(enemy_deck_system.top_enemy).meta.name == "Bear"
    System.inject({"type": "flip_enemy"})
    System.update_all()
    assert Entity.get(enemy_deck_system.top_enemy).meta.name == "Skeleton"
    System.inject({"type": "flip_enemy"})
    System.update_all()
    assert Entity.get(enemy_deck_system.top_enemy).meta.name == "Baby Barbarian"


def test_hero_play_hand():
    hero = Hero("Ranger")
    hero_card_system = HeroCardPositionSystem(
        [
            {
                "id": hero,
                "deck": [
                    SymbolCard({SWORD: 1}),
                    SymbolCard({ARROW: 1}),
                    SymbolCard({JUMP: 1}),
                ],
                "hand": [
                    SymbolCard({SWORD: 1}),
                    SymbolCard({ARROW: 1}),
                    SymbolCard({JUMP: 1}),
                ],
                "discard": [],
            }
        ]
    )

    assert len(hero_card_system.hand[hero]) == 3
    assert len(hero_card_system.deck[hero]) == 3
    assert len(hero_card_system.play_area) == 0
    System.inject({"type": "play_card", "card": hero_card_system.hand[hero][0]})
    System.update_all()
    assert len(hero_card_system.hand[hero]) == 3
    assert len(hero_card_system.deck[hero]) == 2
    assert len(hero_card_system.play_area) == 1


def test_defeat_enemy_with_cards():
    hero = Hero("Ranger").id

    sword_1 = SymbolCard({SWORD: 1})
    sword_2 = SymbolCard({SWORD: 1})
    arrow_1 = SymbolCard({ARROW: 1})
    arrow_2 = SymbolCard({SWORD: 1})
    hero_card_system = HeroCardPositionSystem(
        [
            {
                "id": hero,
                "hand": [
                    sword_1,
                    sword_2,
                    arrow_1,
                    arrow_2,
                ],
                "deck": [],
                "discard": [],
            }
        ]
    )
    enemy_deck_system = get_enemy_deck_system(hero_card_system)

    assert Entity.get(enemy_deck_system.top_enemy).meta.name == "Slime"
    System.inject({"type": "play_card", "card": sword_1.id})
    System.update_all()
    assert Entity.get(enemy_deck_system.top_enemy).meta.name == "Slime"
    System.inject({"type": "play_card", "card": arrow_1.id})
    System.update_all()
    assert Entity.get(enemy_deck_system.top_enemy).meta.name == "Slime"
    System.inject({"type": "play_card", "card": sword_2.id})
    System.update_all()
    assert Entity.get(enemy_deck_system.top_enemy).meta.name == "Bear"
