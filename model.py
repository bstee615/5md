from calendar import c
from collections import defaultdict
from enum import Enum
import json

class Symbols(Enum):
    SWORD = 1
    ARROW = 2
    JUMP = 3

card_global_index = 0
class HeroCard:
    def __init__(self, index) -> None:
        if index is None:
            global card_global_index
            self.index = card_global_index
            card_global_index += 1
        else:
            self.index = index

class SymbolCard(HeroCard):
    def __init__(self, symbols, index=None):
        super().__init__(index)
        self.symbols = symbols
        self.name = ",".join(f"{symbol.name}={count}" for symbol, count in self.symbols.items())
    
    def view(self):
        d = {symbol.name: count for symbol, count in self.symbols.items()}
        d.update({
            "index": self.index,
            "name": self.name,
        })
        return d

    def __repr__(self):
        return json.dumps(self.view())

class ActionCard(HeroCard):
    def __init__(self):
        super().__init__(None)
        pass

enemy_global_index = 0
class EnemyCard:
    def __init__(self, name, symbols) -> None:
        global enemy_global_index
        self.index = enemy_global_index
        enemy_global_index += 1
        self.name = name
        self.symbols = symbols

    def view(self):
        return {
            "name": self.name,
            "symbols": self.symbols,
        }
    
    def __repr__(self) -> str:
        return f"{self.name}(symbols={self.symbols})"

class BossCard:
    def __init__(self, name, symbols) -> None:
        global enemy_global_index
        self.index = enemy_global_index
        enemy_global_index += 1
        self.name = name
        self.symbols = symbols

    def view(self):
        return {
            "name": self.name,
            "symbols": self.symbols,
        }
    
    def __repr__(self) -> str:
        return f"{self.name}(symbols={self.symbols})"

class Hero:
    def __init__(self, name):
        self.name = name
        self.deck = []
        self.discard = []
        self.hand = []

    def view(self):
        return {
            "name": self.name,
            "deck": [c.view() for c in self.deck],
            "discard": [c.view() for c in self.discard],
            "hand": [c.view() for c in self.hand],
        }
    
    def __repr__(self) -> str:
        return f"{self.name}(hand={self.hand}, deck={self.deck}, discard={self.discard})"

class Game:
    def __init__(self):
        self.boss = None
        self.heroes = {}
        self.enemy_deck = []
        self.timer = None
        self.hero_cards_played = []
    
    def view(self):
        return {
            "boss": self.boss.view(),
            "heroes": {
                name: data.view()
                for name, data in self.heroes.items()
            },
            "enemy_deck": [c.view() for c in self.enemy_deck],
            "hero_cards_played": [c.view() for c in self.hero_cards_played]
        }
    
    def init_boss(self, name):
        if name == "Baby Barbarian":
            symbols = {
                Symbols.SWORD: 2,
                Symbols.ARROW: 2,
                Symbols.JUMP: 3,
            }
        else:
            raise NotImplementedError(f"boss {name}")
        card = BossCard(name, symbols)
        self.boss = card
    
    def add_hero(self, name):
        card = Hero(name)
        self.heroes[name] = card
        return card
    
    def add_enemy(self, name, symbols):
        card = EnemyCard(name, symbols)
        self.enemy_deck.append(card)
        return card

    def top_enemy(self):
        if len(self.enemy_deck) > 0:
            return self.enemy_deck[0]
        else:
            return self.boss

    def defeat_enemy(self):
        if len(self.enemy_deck) > 0:
            self.enemy_deck.pop(0)
        self.hero_cards_played = []

    def play_hero_card(self, hero_name, card_idx):
        hero = self.heroes[hero_name]
        card_idx = next((i for i, c in enumerate(hero.hand) if c.index == card_idx), None)
        if card_idx is not None:
            card = hero.hand.pop(card_idx)
            self.hero_cards_played.append(card)
            self.apply_hero_cards()
            return "success"
        return "error"
    
    def apply_hero_cards(self):
        top_enemy = self.top_enemy()

        all_symbols = defaultdict(int)
        for card in self.hero_cards_played:
            for symbol, count in card.symbols.items():
                all_symbols[symbol] += count
        if all(count >= top_enemy.symbols.get(symbol, -1) for symbol, count in all_symbols.items()):
            self.defeat_enemy()
    
    def __repr__(self):
        return f"Game(\n\tboss={self.boss},\n\theroes={self.heroes},\n\tenemy_deck={self.enemy_deck},\n\ttimer={self.timer},\n\thero_cards_played={self.hero_cards_played}\n)"

def test_symbol_card():
    assert SymbolCard({Symbols.SWORD: 1}).name == "SWORD=1"
    assert SymbolCard({Symbols.SWORD: 1, Symbols.ARROW: 1}).name == "SWORD=1,ARROW=1"

def test_empty():
    game = Game()

def test_init():
    game = Game()
    game.init_boss("Baby Barbarian")
    game.add_hero("Ranger")
    game.add_enemy("Slime", {Symbols.SWORD: 1})
    game.add_enemy("Bear", {Symbols.ARROW: 1})
    game.add_enemy("Skeleton", {Symbols.JUMP: 1})
    assert game.top_enemy().name == "Slime"

def test_defeat_enemy():
    game = Game()
    game.init_boss("Baby Barbarian")
    game.add_hero("Ranger")
    game.add_enemy("Slime", {Symbols.SWORD: 1})
    game.add_enemy("Bear", {Symbols.ARROW: 1})
    game.add_enemy("Skeleton", {Symbols.JUMP: 1})
    assert game.top_enemy().name == "Slime"
    game.defeat_enemy()
    assert game.top_enemy().name == "Bear"
    game.defeat_enemy()
    assert game.top_enemy().name == "Skeleton"
    game.defeat_enemy()
    assert game.top_enemy().name == "Baby Barbarian"

def test_play_hero_card():
    game = Game()
    game.init_boss("Baby Barbarian")
    game.add_hero("Ranger")
    game.add_enemy("Slime", {Symbols.SWORD: 2})
    assert game.top_enemy().name == "Slime"

    card = SymbolCard({Symbols.SWORD: 1})
    game.play_hero_card(card)
    assert game.top_enemy().name == "Slime"

    card = SymbolCard({Symbols.SWORD: 1})
    game.play_hero_card(card)
    assert game.top_enemy().name == "Baby Barbarian"
    
    game.add_enemy("Slime", {Symbols.SWORD: 2})
    assert game.top_enemy().name == "Slime"
    card = SymbolCard({Symbols.SWORD: 2})
    game.play_hero_card(card)
    assert game.top_enemy().name == "Baby Barbarian"
