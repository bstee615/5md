from collections import defaultdict

SWORD = "SWORD"
ARROW = "ARROW"
JUMP = "JUMP"

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
        self.name = ",".join(f"{symbol}={count}" for symbol,
                             count in self.symbols.items())


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

    def __repr__(self) -> str:
        return f"{self.name}(symbols={self.symbols})"


class BossCard:
    def __init__(self, name, symbols) -> None:
        global enemy_global_index
        self.index = enemy_global_index
        enemy_global_index += 1
        self.name = name
        self.symbols = symbols

    def __repr__(self) -> str:
        return f"{self.name}(symbols={self.symbols})"


class Hero:
    def __init__(self, name):
        self.name = name
        self.deck = []
        self.discard = []
        self.hand = []

    def __repr__(self) -> str:
        return f"{self.name}(hand={self.hand}, deck={self.deck}, discard={self.discard})"


class Game:
    def __init__(self):
        self.boss = None
        self.heroes = {}
        self.enemy_deck = []
        self.timer = None
        self.hero_cards_played = []

    def init_boss(self, name):
        if name == "Baby Barbarian":
            symbols = {
                SWORD: 2,
                ARROW: 2,
                JUMP: 3,
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
        actions = []
        if len(self.enemy_deck) > 0:
            self.enemy_deck.pop(0)
            actions.append(
                {"action": "flip_enemy", "new_enemy_index": self.top_enemy().index})
        else:
            actions.append(
                {"action": "win"})
        for hero_name, card in self.hero_cards_played:
            self.heroes[hero_name].discard.append(card)
        actions.append({"action": "update_discard", "heroes_to_indices": {hero_name: [c.index for c in hero.discard] for hero_name, hero in self.heroes.items()}})
        self.hero_cards_played = []
        return actions

    def play_hero_card(self, hero_name, card_idx):
        status = None
        hero = self.heroes[hero_name]
        card_idx = next((i for i, c in enumerate(
            hero.hand) if c.index == card_idx), None)
        if card_idx is not None:
            actions = []
            card = hero.hand.pop(card_idx)
            actions.append({
                "action": "play_card",
                "hero_name": hero_name,
                "entity": card.index,
            })
            self.hero_cards_played.append((hero_name, card))
            actions += self.apply_hero_cards()
            status = "success"
            drawn_card_indices = []
            while len(hero.hand) < 3:
                draw_card = hero.deck.pop(0)
                hero.hand.append(draw_card)
                drawn_card_indices.append(draw_card.index)
            actions.append({"action": "draw_card", "hero_name": hero_name, "entities": drawn_card_indices, "new_deck_len": len(hero.deck), "new_hand_len": len(hero.hand)})
        else:
            status = "error"
            actions = [{"action": "revert"}]
        return status, actions

    def apply_hero_cards(self):
        actions = []
        top_enemy = self.top_enemy()

        all_symbols = defaultdict(int)
        for _, card in self.hero_cards_played:
            for symbol, count in card.symbols.items():
                all_symbols[symbol] += count
        beat = [all_symbols.get(symbol, -1) >= count for symbol, count in top_enemy.symbols.items()]
        if len(beat) > 0 and all(beat):
            actions += self.defeat_enemy()

        return actions

    def __repr__(self):
        return f"Game(\n\tboss={self.boss},\n\theroes={self.heroes},\n\tenemy_deck={self.enemy_deck},\n\ttimer={self.timer},\n\thero_cards_played={self.hero_cards_played}\n)"


def test_symbol_card():
    assert SymbolCard({SWORD: 1}).name == "SWORD=1"
    assert SymbolCard({SWORD: 1, ARROW: 1}).name == "SWORD=1,ARROW=1"


def test_empty():
    game = Game()


def test_init():
    game = Game()
    game.init_boss("Baby Barbarian")
    game.add_hero("Ranger")
    game.add_enemy("Slime", {SWORD: 1})
    game.add_enemy("Bear", {ARROW: 1})
    game.add_enemy("Skeleton", {JUMP: 1})
    assert game.top_enemy().name == "Slime"


def test_defeat_enemy():
    game = Game()
    game.init_boss("Baby Barbarian")
    game.add_hero("Ranger")
    game.add_enemy("Slime", {SWORD: 1})
    game.add_enemy("Bear", {ARROW: 1})
    game.add_enemy("Skeleton", {JUMP: 1})
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
    game.add_enemy("Slime", {SWORD: 2})
    assert game.top_enemy().name == "Slime"

    card = SymbolCard({SWORD: 1})
    game.play_hero_card(card)
    assert game.top_enemy().name == "Slime"

    card = SymbolCard({SWORD: 1})
    game.play_hero_card(card)
    assert game.top_enemy().name == "Baby Barbarian"

    game.add_enemy("Slime", {SWORD: 2})
    assert game.top_enemy().name == "Slime"
    card = SymbolCard({SWORD: 2})
    game.play_hero_card(card)
    assert game.top_enemy().name == "Baby Barbarian"
