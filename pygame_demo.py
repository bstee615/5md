import json
from turtle import back
import jsonpickle
import sys
import traceback
import pygame
import simple_websocket

from model import ARROW, JUMP, SWORD, Game, SymbolCard
pygame.init()

size = width, height = 1024, 768
background = pygame.image.load("bg.png")
win = pygame.image.load("win.png")

screen = pygame.display.set_mode(size)

"""NETWORKING"""
networking = True

if networking:
    ws = simple_websocket.Client('ws://localhost:5000/game')


def send_ws_command(cmd):
    print("send_ws_command", cmd)
    if networking:
        ws.send(cmd)
        return ws.receive()


def close_network():
    if networking:
        ws.close()


def initialize_from_network():
    if networking:
        ws.send(jsonpickle.encode({"command": "init"}))
        data = ws.receive()
        print("data =", repr(data))
        response = json.loads(data)
        print("response =", response)
        return jsonpickle.decode(response["game"])
    else:
        # Dummy data
        d = Game()
        ranger = d.add_hero("Ranger")
        ranger.hand += [
            SymbolCard({SWORD: 1}),
            SymbolCard({ARROW: 1}),
            SymbolCard({JUMP: 1})
        ]
        return d


"""NETWORKING"""


class Handle:
    """Grabbable handle on object"""

    def __init__(self):
        self.draggable = True
        self.grabbed = False
        self.grab_offset = pygame.Vector2()


class MyObject:
    def __init__(self, obj, rect=True, draggable=False):
        self.fields = {}
        self.fields["object"] = obj
        if rect:
            if isinstance(obj, pygame.Surface):
                self.fields["rect"] = obj.get_rect()
            elif isinstance(obj, pygame.Rect):
                self.fields["rect"] = obj
            else:
                raise NotImplementedError(type(obj))
        if draggable:
            self.fields["handle"] = Handle()
        self.children = []

    def set_pos(self, p, touched=None):
        if touched is None:
            touched = set()
        self.fields["rect"].x = p.x
        self.fields["rect"].y = p.y
        for ch, off in self.children:
            if ch not in touched:
                ch.set_pos(p + off, touched.union({self}))
        if "parent" in self.fields:
            p, p_off = self.fields["parent"]
            p.set_pos(pygame.Vector2(
                self.fields["rect"].x, self.fields["rect"].y) - p_off, touched.union({self}))

    def add_child(self, obj, offset):
        obj.set_pos(pygame.Vector2(
            self.fields["rect"].x, self.fields["rect"].y) + offset)
        self.children.append((obj, offset))
        obj.fields["parent"] = (self, offset)

    def __repr__(self):
        return f"{self.fields}"


enemy_pos = pygame.Vector2(750, 200)
discard_pos = pygame.Vector2(900, 600)
deck_pos = pygame.Vector2(100, 600)
symbol_pos = {
    SWORD: pygame.Vector2(750, 400),
    ARROW: pygame.Vector2(750, 450),
    JUMP: pygame.Vector2(750, 500),
}


class GameState:
    """Global game state"""

    def __init__(self):
        self.mouse_pos = pygame.Vector2(pygame.mouse.get_pos())
        self.object_handles = []
        self.named_objects = {}
        self.enemy_symbols = []
        self.won = False

        game = initialize_from_network()
        self.init_objects(game, "Ranger")

    def move_card_to(self, card_obj, position):
        if position["area"] == "hand":
            space_between_cards = 125
            num_cards_in_hand = len([o for o in self.object_handles if o.fields.get("position", {"area": None})["area"] == "hand"])
            x = ((1024 // 2) - 50 - ((space_between_cards * num_cards_in_hand) // 2) + (space_between_cards * position["index"]))
            y = 600
            card_obj.set_pos(pygame.Vector2(x, y))
            card_obj.fields["handle"].draggable = True
        elif position["area"] == "play_area":
            play_rect = self.named_objects["play_area"].fields["rect"]
            card_offset = 125
            left = play_rect.x + (card_offset * position["index"])
            card_obj.set_pos(pygame.Vector2(left, play_rect.y))
            card_obj.fields["handle"].draggable = True
        elif position["area"] == "discard":
            r = self.named_objects["discard_area"].fields["rect"]
            card_obj.set_pos(pygame.Vector2(r.x, r.y))
            card_obj.fields["handle"].draggable = False
        elif position["area"] == "deck":
            r = self.named_objects["deck_area"].fields["rect"]
            card_obj.set_pos(pygame.Vector2(r.x, r.y))
            card_obj.fields["handle"].draggable = False

    def show_enemy(self, card_obj):
        card_obj.set_pos(enemy_pos)
        i = 0
        while i < len(self.object_handles):
            if "model_type" in self.object_handles[i].fields and self.object_handles[i].fields["model_type"] == "symbol":
                self.object_handles.pop(i)
            else:
                i += 1
        self.enemy_symbols = []
        for symbol, count in card_obj.fields["symbols"].items():
            for i in range(count):
                symbol_obj = self.add_object(
                    pygame.transform.scale(
                        pygame.image.load(f"{symbol}.jpg"), (50, 50)),
                    draggable=True
                )
                symbol_obj.set_pos(
                    symbol_pos[symbol] + pygame.Vector2(i * 50, 0))
                symbol_obj.fields["model_type"] = "symbol"
                self.enemy_symbols.append(symbol_obj)

    def init_objects(self, game, hero_name):
        enemy_board = self.add_object(pygame.transform.scale(
            pygame.image.load("playing_board.jpg"), (250, 100)))
        enemy_board.set_pos(pygame.Vector2(650, 400))

        self.add_object(pygame.Rect(200, 200, 400, 300), name="play_area")
        self.add_object(pygame.Rect(
            discard_pos.x, discard_pos.y, 100, 150), name="discard_area")
        self.add_object(pygame.Rect(
            deck_pos.x, deck_pos.y, 100, 150), name="deck_area")

        enemy_index = game.top_enemy().index
        for i, card in enumerate(game.enemy_deck + [game.boss]):
            card_obj = self.add_object(
                pygame.transform.scale(pygame.image.load(
                    f"{card.name}.jpg"), (100, 150)),
                draggable=True,
            )
            card_obj.fields["index"] = card.index
            card_obj.fields["model_type"] = "enemy"
            card_obj.fields["symbols"] = card.symbols
            if card.index == enemy_index:
                self.show_enemy(card_obj)

        hand_cards = []
        for i, card in enumerate(game.heroes[hero_name].hand):
            card_obj = self.add_object(
                pygame.transform.scale(pygame.image.load(
                    f"{card.name}.jpg"), (100, 150)),
                draggable=True,
            )
            card_obj.fields["position"] = {"area": "hand", "index": i}
            card_obj.fields["index"] = card.index
            card_obj.fields["model_type"] = "hero_card"
            card_obj.fields["hero_name"] = hero_name
            hand_cards.append(card_obj)

        for i, card in enumerate(game.heroes[hero_name].discard):
            card_obj = self.add_object(
                pygame.transform.scale(pygame.image.load(
                    f"{card.name}.jpg"), (100, 150)),
                draggable=True,
            )
            card_obj.fields["position"] = {"area": "discard"}
            card_obj.fields["index"] = card.index
            card_obj.fields["model_type"] = "hero_card"
            card_obj.fields["hero_name"] = hero_name

        for i, card in enumerate(game.heroes[hero_name].deck):
            card_obj = self.add_object(
                pygame.transform.scale(pygame.image.load(
                    f"{card.name}.jpg"), (100, 150)),
                draggable=True,
            )
            card_obj.fields["position"] = {"area": "deck"}
            card_obj.fields["index"] = card.index
            card_obj.fields["model_type"] = "hero_card"
            card_obj.fields["hero_name"] = hero_name

        for i, (_, card) in enumerate(game.hero_cards_played):
            print("play area", card)
            card_obj = self.add_object(
                pygame.transform.scale(pygame.image.load(
                    f"{card.name}.jpg"), (100, 150)),
                draggable=True
            )
            card_obj.fields["position"] = {"area": "play_area", "index": i}
            card_obj.fields["index"] = card.index
            card_obj.fields["model_type"] = "hero_card"
            card_obj.fields["hero_name"] = hero_name
            
        self.update_card_pos()

    def add_object(self, obj, name=None, **kwargs):
        my_obj = MyObject(obj, **kwargs)
        if name is not None:
            self.named_objects[name] = my_obj
        self.object_handles.append(my_obj)
        return my_obj

    def try_pickup(self):
        for obj in self.object_handles:
            if not("handle" in obj.fields and "rect" in obj.fields):
                continue
            obj_rect = obj.fields["rect"]
            if obj_rect.collidepoint(self.mouse_pos):
                obj_handle = obj.fields["handle"]
                obj_handle.grab_offset = pygame.Vector2(
                    self.mouse_pos.x - obj_rect.x, self.mouse_pos.y - obj_rect.y)
                print("mouse", self.mouse_pos, "object",
                      obj_rect, "offset", obj_handle.grab_offset)
                obj_handle.grabbed = True

    def handle_action(self, action):
        print("handling", action)
        if action["action"] == "flip_enemy":
            card = next(c for c in self.object_handles if c.fields.get(
                "model_type", None) == "enemy" and c.fields["index"] == action["new_enemy_index"])
            self.show_enemy(card)
            play_stuff = list(filter(lambda o: "position" in o.fields and o.fields["position"]["area"] == "play_area", self.object_handles))
            for o in play_stuff:
                o.fields["position"] = {"area": "discard"}
        elif action["action"] == "play_card":
            o = next(o for o in self.object_handles if o.fields.get(
                "model_type", None) == "hero_card" and o.fields["index"] == action["entity"])
            play_stuff = list(filter(lambda o: "position" in o.fields and o.fields["position"]["area"] == "play_area", self.object_handles))
            o.fields["position"] = {
                "area": "play_area",
                "index": max(o.fields["position"]["index"] for o in play_stuff) + 1 if len(play_stuff) > 0 else 0,
            }
            hand_stuff = list(filter(lambda o: "position" in o.fields and o.fields["position"]["area"] == "hand", self.object_handles))
            hand_stuff = list(sorted(hand_stuff, key=lambda o: o.fields["position"]["index"]))
            for i, o in enumerate(hand_stuff):
                o.fields["position"]["index"] = i
        elif action["action"] == "draw_card":
            o = next(o for o in self.object_handles if o.fields.get(
                "model_type", None) == "hero_card" and o.fields["index"] == action["entity"])
            if o.fields.get("position", {"area": None})["area"] != "hand":
                hand_stuff = list(filter(lambda o: "position" in o.fields and o.fields["position"]["area"] == "hand", self.object_handles))
                o.fields["position"] = {
                    "area": "hand",
                    "index": max(o.fields["position"]["index"] for o in hand_stuff) + 1 if len(hand_stuff) > 0 else 0,
                }
        elif action["action"] == "win":
            self.won = True
        else:
            print("unhandled action", action)

    def drop(self):
        play_rect = self.named_objects["play_area"].fields["rect"]
        for o in self.object_handles:
            if "handle" in o.fields and "rect" in o.fields:
                o_rect = o.fields["rect"]
                if o.fields["handle"].grabbed:
                    o.fields["handle"].grabbed = False
                    if play_rect.colliderect(o_rect) and o.fields.get("position", {"area": None})["area"] == "hand":
                        data = send_ws_command(json.dumps({
                            "command": "play_hero_card",
                            "hero_name": "Ranger",
                            "card_index": o.fields["index"],
                        }))
                        response = json.loads(data)
                        print("result", response["result"])
                        if response["result"] == "error":
                            continue
                        else:
                            for action in response["actions"]:
                                self.handle_action(action)
        self.update_card_pos()

    def update_mouse_pos(self):
        self.mouse_pos.update(pygame.mouse.get_pos())
    
    def update_card_pos(self):
        print("update_card_pos")
        for o in self.object_handles:
            if (p := o.fields.get("position", None)) is not None:
                self.move_card_to(o, p)

    def step(self):
        step_events = pygame.event.get()
        for event in step_events:
            if event.type == pygame.QUIT:
                close_network()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                left, middle, right = pygame.mouse.get_pressed()
                if left:
                    self.try_pickup()
                if middle:
                    print(pygame.mouse.get_pos())
            if event.type == pygame.MOUSEBUTTONUP:
                left, middle, right = pygame.mouse.get_pressed()
                if not left:
                    self.drop()
        
        if self.won:
            screen.blit(win, (0, 0))
            pygame.display.flip()
            return

        state.update_mouse_pos()

        for o in self.object_handles:
            if "handle" in o.fields:
                if o.fields["handle"].grabbed:
                    if "handle" in o.fields and "rect" in o.fields:
                        o_handle = o.fields["handle"]
                        o.set_pos(self.mouse_pos - o_handle.grab_offset)

        screen.blit(background, (0, 0))
        for o in self.object_handles:
            if isinstance(o.fields["object"], pygame.Surface):
                screen.blit(o.fields["object"], o.fields["rect"])
            elif isinstance(o.fields["object"], pygame.Rect):
                pygame.draw.rect(screen, "red", o.fields["rect"], width=5)
        pygame.display.flip()


state = GameState()

while 1:
    try:
        state.step()
    except Exception:
        traceback.print_exc()
        close_network()
        exit(1)
