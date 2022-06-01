from collections import defaultdict
import json
import random
import time
import jsonpickle
import sys
import traceback
import pygame
import simple_websocket
from multiprocessing import Process, Queue, Value
import sys

from model import *

"""NETWORKING"""
if len(sys.argv) > 1:
    hero_name = sys.argv[1]
if len(sys.argv) > 2:
    networking = sys.argv[2] != "no"
else:
    networking = True
    should_close = Value('i', 0)
    should_init = Value('i', 0)

def try_connect():
    max_retry_strikes = 3
    retry_strikes = 0
    did_connect = False
    while retry_strikes < max_retry_strikes and should_close.value != 1:
        try:
            ws = simple_websocket.Client('ws://localhost:5000/game')
            did_connect = True
            break
        except (simple_websocket.ConnectionError, ConnectionRefusedError) as e:
            retry_strikes += 1
            print("error connecting to server:", retry_strikes, "strikes", e)
            time.sleep(1)
    if did_connect:
        ws.send(json.dumps({"message": "login", "hero_name": hero_name}))
        return ws
    else:
        raise Exception("Error connecting to goodies")

def worker(recv_q, send_q, should_close, should_init):
    """
    Worker process for corralling input/output messages.
    recv_q is a queue of output messages received from the server.
    send_q is a queue of messages which we should send to the server.

    The worker runs in a non-blocking loop to receive and enqueue all messages,
    then dequeue and send all required messages.
    This process should be joined at close to ensure that cleanup happens.
    """
    try:
        ws = try_connect()
        should_init.value = 1
        while True:
            try:
                if should_close.value == 1:
                    break
                data = ws.receive(0)
                if data:
                    # print(f"{data=}")
                    recv_q.put(data)
                while not send_q.empty():
                    cmd = send_q.get()
                    ws.send(cmd)
            except simple_websocket.ConnectionClosed:
                ws = try_connect()
        ws.close()
    except Exception:
        print("error in websocket thread")
        traceback.print_exc()
        should_close.value = 1
        pygame.quit()
        sys.exit()


def wait_for_data():
    while recv_q.empty():
        if should_close.value == 1:
            raise Exception("closed before data arrived in ingoing queue")
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
        should_close.value = 1
        if p is not None:
            p.join()


# def initialize_from_network():
#     if networking:
#         # print("data =", repr(data))
#         response = json.loads(data)
#         # print("response =", response)
#         return jsonpickle.decode(response["game"])
#     else:
#         pass


"""NETWORKING"""


# class ResourceManager:
#     def __init__(self):
#         self.resources = {}
    
#     def load_text(self, text, name=None, color=None):
#         if name is None:
#             name = f"text_{text}"
#         if color is None:
#             color = BLUE
#         self.resources[name] = font.render(text, True, color)
    
#     def load_image(self, filepath, name=None):
#         if name is None:
#             name = filepath
#         self.resources[name] = pygame.image.load(filepath)


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

class HeroCardGraphicSystem(System):
    def __init__(self, hcps):
        super().__init__()
        self.subscribe("add_hero")
        self.subscribe("play_card")
        self.subscribe("draw_cards")
        self.subscribe("flip_enemy")

        for card in Entity.filter("hero_card"):
            card.attach(Component("graphic"))
            card.graphic.asset = pygame.transform.scale(pygame.image.load(f"{symbols_to_name(card.symbol_count.symbols)}.jpg"), (100, 150))
            card.graphic.visible = False

        for hero_id in hcps.heroes:
            hero = Entity.get(hero_id)
            if hero.meta.name == hero_name:
                pass
            else:
                pass
            for i, card_id in enumerate(hcps.hand[hero_id]):
                card = Entity.get(card_id)
                space_between_cards = 125
                num_cards_in_hand = len(hcps.hand[hero_id])
                x = ((1024 // 2) - 50 - ((space_between_cards * num_cards_in_hand) // 2) + (space_between_cards * i))
                y = 600
                print(card, x, y)
                card.graphic.position = pygame.Vector2(x, y)
                card.graphic.visible = True
            player_discard = Entity()
            player_discard.attach(Component("graphic"))
            player_discard.graphic.asset = font.render(str(len(hcps.discard[hero_id])), True, BLUE)
            player_discard.graphic.position = discard_pos
            player_deck = Entity()
            player_deck.attach(Component("graphic"))
            player_deck.graphic.asset = font.render(str(len(hcps.deck[hero_id])), True, BLUE)
            player_deck.graphic.position = deck_pos

    
    def update(self):
        events = self.pending()
        for ev in events:
            # if ev["type"] == "draw_cards":
            pass


class GameState:
    """Global game state"""

    def __init__(self):
        self.mouse_pos = pygame.Vector2(pygame.mouse.get_pos())
        self.object_handles = []
        self.named_objects = {}
        self.won = False
        self.clock = pygame.time.Clock()

        self.hcps = None
        self.eds = None

        self.init_objects()

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

    # def init_enemy(self, card_obj):
    #     card_obj.set_pos(enemy_pos)
    #     i = 0
    #     while i < len(self.object_handles):
    #         if "model_type" in self.object_handles[i].fields and self.object_handles[i].fields["model_type"] == "symbol":
    #             self.object_handles.pop(i)
    #         else:
    #             i += 1
    #     for symbol, count in card_obj.fields["symbols"].items():
    #         for i in range(count):
    #             symbol_obj = self.add_object(
    #                 pygame.transform.scale(
    #                     pygame.image.load(f"{symbol}.jpg"), (50, 50)),
    #                 draggable=True
    #             )
    #             symbol_obj.set_pos(
    #                 symbol_pos[symbol] + pygame.Vector2(i * 50, 0))
    #             symbol_obj.fields["model_type"] = "symbol"


    # def create_card(self, hero_name, card, position, visible=True):
    #     card_obj = self.add_object(
    #         pygame.transform.scale(pygame.image.load(
    #             f"{card.name}.jpg"), (100, 150)),
    #         draggable=True,
    #     )
    #     card_obj.fields["position"] = position
    #     card_obj.fields["index"] = card.index
    #     card_obj.fields["model_type"] = "hero_card"
    #     card_obj.fields["hero_name"] = hero_name
    #     card_obj.fields["visible"] = visible

    # def init_other_hero(self, other_hero):
    #     other_pos = other_hero_pos[other_hero.name]
    #     other_deck = self.add_object(font.render(str(len(other_hero.deck)), True, BLUE), other_hero.name + "_deck")
    #     other_deck.set_pos(other_pos)
    #     other_hand = self.add_object(font.render(str(len(other_hero.hand)), True, BLUE), other_hero.name + "_hand")
    #     other_hand.set_pos(other_pos + pygame.Vector2(50, 0))
    #     other_discard = self.add_object(font.render(str(len(other_hero.discard)), True, BLUE), other_hero.name + "_discard")
    #     other_discard.set_pos(other_pos + pygame.Vector2(100, 0))
    #     for card in other_hero.hand + other_hero.deck + other_hero.discard:
    #         self.create_card(other_hero.name, card, {"area": "other_player"}, False)

    def init_objects(self):
        data = wait_for_data()
        message = json.loads(data)
        game = jsonpickle.decode(message["game"])
        self.hcps = game["HeroCardPositionSystem"]
        self.eds = game["EnemyDeckSystem"]
        Entity.reset(**game["Entity"])
        System.reset(**game["System"])
        # print(Entity.eindex)
        
        enemy_board = self.add_object(pygame.transform.scale(
            pygame.image.load("playing_board.jpg"), (250, 100)))
        enemy_board.set_pos(pygame.Vector2(650, 400))

        self.add_object(pygame.Rect(200, 200, 400, 300), name="play_area")

        for card_id in self.eds.deck + [self.eds.boss]:
            card = Entity.get(card_id)
            if card_id == self.eds.top_enemy:
                card.attach(Component("graphic"))
                card.graphic.asset = pygame.transform.scale(pygame.image.load(f"{card.meta.name}.jpg"), (100, 150))
                card.graphic.position = enemy_pos
                for sg in Entity.filter("symbol_graphic"):
                    sg.graphic.visible = False  # TODO: delete
                for symbol, count in card.symbol_count.symbols.items():
                    for i in range(count):
                        sg = Entity()
                        sg.attach(Component("graphic"))
                        sg.graphic.asset = pygame.transform.scale(pygame.image.load(f"{symbol}.jpg"), (50, 50))
                        sg.graphic.position = symbol_pos[symbol] + pygame.Vector2(i * 50, 0)

        self.hcgs = HeroCardGraphicSystem(self.hcps)
            
        return ## TODO: implement the rest

        for i, card in enumerate(game.heroes[hero_name].hand):
            self.create_card(hero_name, card, {"area": "hand", "index": i})

        for i, card in enumerate(game.heroes[hero_name].discard):
            card_obj = self.create_card(hero_name, card, {"area": "discard"}, False)
        for i, card in enumerate(game.heroes[hero_name].deck):
            card_obj = self.create_card(hero_name, card, {"area": "deck"}, False)
        player_discard = self.add_object(font.render(str(len(game.heroes[hero_name].discard)), True, BLUE), hero_name + "_discard")
        player_discard.set_pos(discard_pos)
        player_deck = self.add_object(font.render(str(len(game.heroes[hero_name].deck)), True, BLUE), hero_name + "_deck")
        player_deck.set_pos(deck_pos)

        for i, (_, card) in enumerate(game.hero_cards_played):
            card_obj = self.create_card(hero_name, card, {"area": "play_area", "index": i})
            
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
        elif action["action"] == "update_discard":
            for hn, indices in action["heroes_to_indices"].items():
                for o in [o for o in self.object_handles if o.fields.get("model_type", None) == "hero_card" and o.fields["index"] in indices]:
                    if hn == hero_name:
                        o.fields["position"] = {"area": "discard"}
                    else:
                        o.fields["position"] = {"area": "other_hero"}
                    o.fields["visible"] = False
                if hn + "_discard" in self.named_objects:
                    self.named_objects[hn + "_discard"].set_text(str(len(indices)))
        elif action["action"] == "play_card":
            o = next(o for o in self.object_handles if o.fields.get(
                "model_type", None) == "hero_card" and o.fields["index"] == action["entity"])
            play_stuff = list(filter(lambda o: "position" in o.fields and o.fields["position"]["area"] == "play_area", self.object_handles))
            o.fields["position"] = {
                "area": "play_area",
                "index": max(o.fields["position"]["index"] for o in play_stuff) + 1 if len(play_stuff) > 0 else 0,
            }
            o.fields["visible"] = True
            hand_stuff = list(filter(lambda o: "position" in o.fields and o.fields["position"]["area"] == "hand", self.object_handles))
            hand_stuff = list(sorted(hand_stuff, key=lambda o: o.fields["position"]["index"]))
            for i, o in enumerate(hand_stuff):
                o.fields["position"]["index"] = i
        elif action["action"] == "draw_card":
            if action["hero_name"] == hero_name:
                for entity in action["entities"]:
                    o = next(o for o in self.object_handles if o.fields.get(
                        "model_type", None) == "hero_card" and o.fields["index"] == entity)
                    if o.fields.get("position", {"area": None})["area"] != "hand":
                        hand_stuff = list(filter(lambda o: "position" in o.fields and o.fields["position"]["area"] == "hand", self.object_handles))
                        o.fields["position"] = {
                            "area": "hand",
                            "index": max(o.fields["position"]["index"] for o in hand_stuff) + 1 if len(hand_stuff) > 0 else 0,
                        }
                        o.fields["visible"] = True
            else:
                if (o := self.named_objects.get(action["hero_name"] + "_hand", None)) is not None:
                    o.set_text(str(action["new_hand_len"]))
                if (o := self.named_objects.get(action["hero_name"] + "_deck", None)) is not None:
                    o.set_text(str(action["new_deck_len"]))
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
                            "message": "play_hero_card",
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
        self.named_objects[hero_name + "_discard"].set_text(str(counts["discard"]))
        self.named_objects[hero_name + "_deck"].set_text(str(counts["deck"]))

    def step(self):
        dt = self.clock.tick(framerate)
        step_events = pygame.event.get()
        for event in step_events:
            if event.type == pygame.QUIT:
                close_network()
                pygame.quit()
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
        for e in Entity.filter("graphic"):
            if e.graphic.visible:
                screen.blit(e.graphic.asset, e.graphic.position)
        pygame.display.flip()


if __name__ == "__main__":
    try:
        # Turn-on the worker thread.
        if networking:
            print("initialize websocket thread")
            recv_q = Queue()
            send_q = Queue()

            p = Process(target=worker, args=(recv_q, send_q, should_close, should_init))
            p.start()
    
        while should_init.value != 1:
            if should_close.value == 1:
                raise Exception("closed before window initialized")

        pygame.init()

        size = width, height = 1024, 768
        background = pygame.image.load("bg.png")
        win = pygame.image.load("win.png")
        font = pygame.font.SysFont(None, 24)
        RED = (255, 0, 0)
        GREEN = (0, 255, 0)
        BLUE = (0, 0, 255)
        framerate = 60

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

        print("initialize game")
        state = GameState()
        while should_close.value != 1:
            state.step()
    except Exception:
        print("error in UI thread")
        traceback.print_exc()
        close_network()
        pygame.quit()
        sys.exit()
