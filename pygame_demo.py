from collections import defaultdict
import json
import random
import jsonpickle
import sys
import traceback
import pygame
import simple_websocket
from multiprocessing import Process, Queue
import sys

from model import ARROW, JUMP, SWORD, Game, SymbolCard

"""NETWORKING"""
if len(sys.argv) > 1:
    hero_name = sys.argv[1]
if len(sys.argv) > 2:
    networking = sys.argv[2] != "no"
else:
    networking = True

def worker(recv_q, send_q):
    """
    Worker process for corralling input/output messages.
    recv_q is a queue of output messages received from the server.
    send_q is a queue of messages which we should send to the server.

    The worker runs in a non-blocking loop to receive and enqueue all messages,
    then dequeue and send all required messages.
    This process should be joined at close to ensure that cleanup happens.
    """
    ws = simple_websocket.Client('ws://localhost:5000/game')
    while True:
        try:
            data = ws.receive(0)
        except simple_websocket.ws.ConnectionClosed:
            break
        if data:
            print(f"{data=}")
            recv_q.put(data)
        while not send_q.empty():
            cmd = send_q.get()
            if cmd == "close":
                ws.close()
                break
            ws.send(cmd)
    ws.close()


def wait_for_data():
    while recv_q.empty():
        pass
    return recv_q.get()

def send_ws_command(cmd, wait_for_response=True):
    print("send_ws_command", cmd)
    if networking:
        send_q.put(cmd)
        if wait_for_response:
            return wait_for_data()

def close_network():
    if networking:
        send_ws_command("close", wait_for_response=False)
        p.join()


def initialize_from_network():
    if networking:
        data = send_ws_command(jsonpickle.encode({"command": "init"}))
        print("data =", repr(data))
        response = json.loads(data)
        print("response =", response)
        return jsonpickle.decode(response["game"])
    else:
        # Dummy data
        d = Game()
        d.init_boss("Baby Barbarian")
        ranger = d.add_hero(hero_name)
        ranger.hand += [
            SymbolCard({SWORD: 1}),
            SymbolCard({ARROW: 1}),
            SymbolCard({JUMP: 1})
        ]
        ranger.deck += [
            *([SymbolCard({SWORD: 1})] * 5),
            *([SymbolCard({ARROW: 1})] * 5),
            *([SymbolCard({JUMP: 1})] * 5),
        ]
        random.shuffle(ranger.deck)
        d.add_enemy("Slime", {SWORD: 2})
        d.add_enemy("Skeleton", {ARROW: 1})
        return d


"""NETWORKING"""


class Handle:
    """Grabbable handle on object"""

    def __init__(self):
        self.draggable = True
        self.grabbed = False
        self.grab_offset = pygame.Vector2()


class MyObject:
    def __init__(self, obj, rect=True, draggable=False, visible=True):
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
        self.fields["visible"] = visible
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
    
    def set_text(self, text):
        r = self.fields["rect"]
        self.fields["object"] = t = font.render(text, True, BLUE)
        self.fields["rect"] = t.get_rect()
        self.set_pos(pygame.Vector2(r.x, r.y))

    def __repr__(self):
        return f"{self.fields}"


class GameState:
    """Global game state"""

    def __init__(self):
        self.mouse_pos = pygame.Vector2(pygame.mouse.get_pos())
        self.object_handles = []
        self.named_objects = {}
        self.enemy_symbols = []
        self.won = False

        game = initialize_from_network()
        self.init_objects(game, hero_name)

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
            card_obj.set_pos(discard_pos)
            card_obj.fields["handle"].draggable = False
        elif position["area"] == "deck":
            card_obj.set_pos(deck_pos)
            card_obj.fields["handle"].draggable = False
        elif position["area"] == "other_hero_hand":
            base_pos = other_hero_pos[position["hero_name"]]
            card_obj.set_pos(base_pos + pygame.Vector2(position["index"] * 60, 0))

    def init_enemy(self, card_obj):
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

    def init_other_hero(self, hero):
        for i, card in enumerate(hero.hand):
            card_obj = self.add_object(
                pygame.transform.scale(pygame.image.load(
                    f"{card.name}.jpg"), (50, 75)),
                draggable=True,
            )
            card_obj.fields["position"] = {"area": "other_hero_hand", "hero_name": hero.name, "index": i}
            card_obj.fields["index"] = card.index
            card_obj.fields["model_type"] = "hero_card"
            card_obj.fields["hero_name"] = hero.name

    def init_objects(self, game, hero_name):
        enemy_board = self.add_object(pygame.transform.scale(
            pygame.image.load("playing_board.jpg"), (250, 100)))
        enemy_board.set_pos(pygame.Vector2(650, 400))

        self.add_object(pygame.Rect(200, 200, 400, 300), name="play_area")

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
                self.init_enemy(card_obj)
            else:
                card_obj.set_pos(enemy_pos)
        for other_hero_name, other_hero in [(n, h) for n, h in game.heroes.items() if n != hero_name]:
            print("other hero", other_hero_name, other_hero)
            for i, card in enumerate(game.heroes[other_hero_name].hand):
                card_obj = self.add_object(
                    pygame.transform.scale(pygame.image.load(
                        f"{card.name}.jpg"), (50, 75)),
                    draggable=True,
                )
                card_obj.fields["position"] = {"area": "other_hero_hand", "hero_name": other_hero_name, "index": i}
                card_obj.fields["index"] = card.index
                card_obj.fields["model_type"] = "hero_card"
                card_obj.fields["hero_name"] = other_hero_name

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
            card_obj.fields["visible"] = False
        player_discard = self.add_object(font.render(str(len(game.heroes[hero_name].discard)), True, BLUE), "player_discard")
        player_discard.set_pos(discard_pos)

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
            card_obj.fields["visible"] = False
        player_deck = self.add_object(font.render(str(len(game.heroes[hero_name].deck)), True, BLUE), "player_deck")
        player_deck.set_pos(deck_pos)

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
            self.init_enemy(card)
            play_stuff = list(filter(lambda o: "position" in o.fields and o.fields["position"]["area"] == "play_area", self.object_handles))
            for o in play_stuff:
                o.fields["position"] = {"area": "discard"}
                o.fields["visible"] = False
        elif action["action"] == "play_card":
            if action["hero_name"] == hero_name:
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
            # TODO: else
        elif action["action"] == "draw_card":
            if action["hero_name"] == hero_name:
                o = next(o for o in self.object_handles if o.fields.get(
                    "model_type", None) == "hero_card" and o.fields["index"] == action["entity"])
                if o.fields.get("position", {"area": None})["area"] != "hand":
                    hand_stuff = list(filter(lambda o: "position" in o.fields and o.fields["position"]["area"] == "hand", self.object_handles))
                    o.fields["position"] = {
                        "area": "hand",
                        "index": max(o.fields["position"]["index"] for o in hand_stuff) + 1 if len(hand_stuff) > 0 else 0,
                    }
                    o.fields["visible"] = True
            # TODO: else
        elif action["action"] == "player_join":
            self.init_other_hero(jsonpickle.decode(action["hero"]))
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
                            "hero_name": hero_name,
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
        counts = defaultdict(int)
        for o in self.object_handles:
            if (p := o.fields.get("position", None)) is not None:
                self.move_card_to(o, p)
                counts[p["area"]] += 1
        self.named_objects["player_discard"].set_text(str(counts["discard"]))
        self.named_objects["player_deck"].set_text(str(counts["deck"]))

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
        
        if networking:
            if not recv_q.empty():
                response = json.loads(recv_q.get())
                for action in response["actions"]:
                    self.handle_action(action)
                self.update_card_pos()

        for o in self.object_handles:
            if "handle" in o.fields:
                if o.fields["handle"].grabbed:
                    if "handle" in o.fields and "rect" in o.fields:
                        o_handle = o.fields["handle"]
                        o.set_pos(self.mouse_pos - o_handle.grab_offset)

        screen.blit(background, (0, 0))
        for o in self.object_handles:
            if not o.fields["visible"]:
                continue
            if isinstance(o.fields["object"], pygame.Surface):
                screen.blit(o.fields["object"], o.fields["rect"])
            elif isinstance(o.fields["object"], pygame.Rect):
                pygame.draw.rect(screen, "red", o.fields["rect"], width=5)
        pygame.display.flip()


if __name__ == "__main__":
    pygame.init()

    size = width, height = 1024, 768
    background = pygame.image.load("bg.png")
    win = pygame.image.load("win.png")
    font = pygame.font.SysFont(None, 24)
    RED = (255, 0, 0)
    GREEN = (0, 255, 0)
    BLUE = (0, 0, 255)

    enemy_pos = pygame.Vector2(750, 200)
    discard_pos = pygame.Vector2(900, 600)
    deck_pos = pygame.Vector2(100, 600)
    symbol_pos = {
        SWORD: pygame.Vector2(750, 400),
        ARROW: pygame.Vector2(750, 450),
        JUMP: pygame.Vector2(750, 500),
    }
    other_hero_pos = dict(zip([hn for hn in ["Ranger", "Barbarian"] if hn != hero_name], [
        pygame.Vector2(50, 50),
        pygame.Vector2((1024 // 2) - 25, 50),
        pygame.Vector2(1024 - 50 - 50, 50),
    ]))

    screen = pygame.display.set_mode(size)

    # Turn-on the worker thread.
    if networking:
        recv_q = Queue()
        send_q = Queue()

        p = Process(target=worker, args=(recv_q, send_q))
        p.start()

    state = GameState()
    while 1:
        try:
            state.step()
        except Exception:
            traceback.print_exc()
            close_network()
            exit(1)
