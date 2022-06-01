import functools
import json
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
    should_close = Value("i", 0)
    should_init = Value("i", 0)


def try_connect():
    max_retry_strikes = 3
    retry_strikes = 0
    did_connect = False
    while retry_strikes < max_retry_strikes and should_close.value != 1:
        try:
            ws = simple_websocket.Client("ws://localhost:5000/game")
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
        send_q.put(json.dumps(cmd))
        if wait_for_response:
            return wait_for_data()


def close_network():
    if networking:
        should_close.value = 1
        if p is not None:
            p.join()


"""NETWORKING"""


"""ECS"""


class HeroCardGraphicSystem(System):
    def __init__(self, hcps):
        super().__init__()
        self.won = False
        self.subscribe("add_hero")
        self.subscribe("play_card")
        self.subscribe("draw_cards")
        self.subscribe("flip_enemy")

        self.hcps = hcps

        for card in Entity.filter("hero_card"):
            card.attach(Component("graphic"))
            card.graphic.asset = pygame.transform.scale(
                pygame.image.load(f"{symbols_to_name(card.symbol_count.symbols)}.jpg"),
                (100, 150),
            )
            card.graphic.rect = card.graphic.asset.get_rect()
            card.graphic.visible = False

        for i, card_id in enumerate(hcps.play_area):
            card = Entity.get(card_id)
            card_offset = 125
            x = card_offset * i
            card.graphic.rect = card.graphic.asset.get_rect()
            card.graphic.rect.x, card.graphic.rect.y = play_pos + pygame.Vector2(x, 0)
            card.graphic.visible = True

        for hero_id in hcps.heroes:
            hero = Entity.get(hero_id)
            if hero.meta.name == hero_name:
                self.my_hero_id = hero_id
                for i, card_id in enumerate(hcps.hand[hero_id]):
                    card = Entity.get(card_id)
                    space_between_cards = 125
                    num_cards_in_hand = len(hcps.hand[hero_id])
                    x = (
                        (1024 // 2)
                        - 50
                        - ((space_between_cards * num_cards_in_hand) // 2)
                        + (space_between_cards * i)
                    )
                    y = 600
                    card.graphic.rect.x = x
                    card.graphic.rect.y = y
                    card.graphic.visible = True
                player_discard = Entity()
                player_discard.attach(Component("graphic"))
                player_discard.graphic.asset = font.render(
                    str(len(hcps.discard[hero_id])), True, BLUE
                )
                player_discard.graphic.rect = card.graphic.asset.get_rect()
                player_discard.graphic.rect.x = discard_pos.x
                player_discard.graphic.rect.y = discard_pos.y
                self.player_discard = player_discard

                player_deck = Entity()
                player_deck.attach(Component("graphic"))
                player_deck.graphic.asset = font.render(
                    str(len(hcps.deck[hero_id])), True, BLUE
                )
                player_deck.graphic.rect = card.graphic.asset.get_rect()
                player_deck.graphic.rect.x = deck_pos.x
                player_deck.graphic.rect.y = deck_pos.y
                self.player_deck = player_deck

    def update_deck(self):
        old_rect = self.player_deck.graphic.rect
        self.player_deck.graphic.asset = font.render(str(len(self.hcps.deck[self.my_hero_id])), True, BLUE)
        self.player_deck.graphic.rect = self.player_deck.graphic.asset.get_rect()
        self.player_deck.graphic.rect.move_ip(pygame.Vector2(old_rect.x, old_rect.y))

    def update_discard(self):
        old_rect = self.player_discard.graphic.rect
        self.player_discard.graphic.asset = font.render(str(len(self.hcps.discard[self.my_hero_id])), True, BLUE)
        self.player_discard.graphic.rect = self.player_discard.graphic.asset.get_rect()
        self.player_discard.graphic.rect.move_ip(pygame.Vector2(old_rect.x, old_rect.y))

    def update(self):
        events = self.pending()
        for ev in events:
            if ev["type"] == "flip_enemy":
                print("flip_enemy")
                self.update_deck()
                self.update_discard()
                for o in self.hcps.play_area:
                    Entity.get(o).graphic.visible = False
            elif ev["type"] == "play_card":
                card = Entity.get(ev["card"])
                card.graphic.visible = True
                new_pos = play_pos + pygame.Vector2(125 * len(self.hcps.play_area), 0)
                card.graphic.rect.x, card.graphic.rect.y = new_pos
            elif ev["type"] == "draw_cards":
                self.update_deck()
                if ev["hero"] == self.my_hero_id:
                    hand = self.hcps.hand[ev["hero"]]
                    for i, card_id in enumerate(hand):
                        card = Entity.get(card_id)
                        card.graphic.visible = True
                        space_between_cards = 125
                        num_cards_in_hand = len(hand)
                        x = (
                            (1024 // 2)
                            - 50
                            - ((space_between_cards * num_cards_in_hand) // 2)
                            + (space_between_cards * i)
                        )
                        y = 600
                        card.graphic.rect.x, card.graphic.rect.y = x, y
            elif ev["type"] == "win":
                self.won = True

        mouse_pos = get_mouse_pos()
        graphic_handles = [
            gh for gh in set(Entity.filter("graphic")) if gh.graphic.grabbed
        ]
        for gh in graphic_handles:
            new_pos = mouse_pos - gh.graphic.grab_offset
            gh.graphic.rect.x, gh.graphic.rect.y = new_pos

        if self.won:
            screen.blit(win, (0, 0))
        else:
            screen.blit(background, (0, 0))
            for e in Entity.filter("graphic"):
                if e.graphic.visible:
                    screen.blit(e.graphic.asset, e.graphic.rect)
        pygame.display.flip()


def get_mouse_pos():
    return pygame.Vector2(pygame.mouse.get_pos())


class InputSystem(System):
    def __init__(self):
        super().__init__()
        self.left_down = False

    def update(self):
        events = self.pending()
        for ev in events:
            pass

        step_events = pygame.event.get()
        left, middle, right = pygame.mouse.get_pressed()
        for event in step_events:
            if event.type == pygame.QUIT:
                print("quit")
                close_network()
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                self.left_down = left
                if left:
                    mouse_pos = get_mouse_pos()
                    handleable = set(Entity.filter("hero_card")) & set(
                        Entity.filter("graphic")
                    )
                    grabbed = [h for h in handleable if h.graphic.visible]
                    for h in handleable:
                        hr = h.graphic.rect
                        if hr.collidepoint(mouse_pos):
                            h.graphic.grab_offset = mouse_pos - pygame.Vector2(
                                h.graphic.rect.x, h.graphic.rect.y
                            )
                            h.graphic.grabbed = True
                if middle:
                    print(pygame.mouse.get_pos())
            if event.type == pygame.MOUSEBUTTONUP:
                if not self.left_down:
                    continue
                self.left_down = left

                handleable = set(Entity.filter("hero_card")) & set(
                    Entity.filter("graphic")
                )
                grabbed = [h for h in handleable if h.graphic.grabbed]
                for h in grabbed:
                    h.graphic.grabbed = False
                    if play_rect.colliderect(h.graphic.rect):
                        send_ws_command({"type": "remote_event", "sender": "client", "event": {"type": "play_card", "card": h.id}}, wait_for_response=False)
                        # functools.partial(send_ws_command, wait_for_response=False)
                        # System.inject({"type": "remote_event", "name": "client", "event": {"type": "play_card", "card": h.id}})

class GetFromQueueSystem(System):
    def __init__(self):
        super().__init__(prioritize=True)
    
    def update(self):
        while not recv_q.empty():
            ev = json.loads(recv_q.get())
            if ev["type"] == "init":
                continue
            print("event", ev)
            self.inject(ev)

"""ECS"""


class Game:
    """Global game state"""

    def __init__(self):
        self.clock = pygame.time.Clock()

        data = wait_for_data()
        message = json.loads(data)
        assert message["type"] == "init"
        game = jsonpickle.decode(message["game"])
        self.hcps = game["HeroCardPositionSystem"]
        self.eds = game["EnemyDeckSystem"]
        Entity.reset(**game["Entity"])
        self.gqs = GetFromQueueSystem()

        self.ins = InputSystem()
        # self.es = EmitSystem(functools.partial(send_ws_command, wait_for_response=False), "server")
        self.ees = EchoEmitSystem("client")
        # System.reset(**game["System"])
        # print("subscriptions", System.subscriptions)

        for card_id in self.eds.deck + [self.eds.boss]:
            card = Entity.get(card_id)
            if card_id == self.eds.top_enemy:
                card.attach(Component("graphic"))
                card.graphic.asset = pygame.transform.scale(
                    pygame.image.load(f"{card.meta.name}.jpg"), (100, 150)
                )
                card.graphic.rect = card.graphic.asset.get_rect()
                card.graphic.rect.x, card.graphic.rect.y = enemy_pos
                for sg in Entity.filter("symbol_graphic"):
                    sg.graphic.visible = False  # TODO: delete
                for symbol, count in card.symbol_count.symbols.items():
                    for i in range(count):
                        sg = Entity()
                        sg.attach(Component("graphic"))
                        sg.graphic.asset = pygame.transform.scale(
                            pygame.image.load(f"{symbol}.jpg"), (50, 50)
                        )
                        sg.graphic.rect = sg.graphic.asset.get_rect()
                        sg.graphic.rect.x, sg.graphic.rect.y = symbol_pos[
                            symbol
                        ] + pygame.Vector2(i * 50, 0)

        self.hcgs = HeroCardGraphicSystem(self.hcps)
        System.systems.append(self.hcps)
        System.systems.append(self.eds)
        self.hcps.subscribe("add_hero")
        self.hcps.subscribe("play_card")
        self.hcps.subscribe("draw_cards")
        self.hcps.subscribe("flip_enemy")
        self.eds.subscribe("add_hero")
        self.eds.subscribe("flip_enemy")
        self.eds.subscribe("play_card")
        self.eds.subscribe("clear_play_area")

    def run(self):
        while should_close.value != 1:
            dt = self.clock.tick(framerate)

            # if networking:
            #     if not recv_q.empty():
            #         response = json.loads(recv_q.get())
            #         for action in response["actions"]:
            #             self.handle_action(action)
            #         self.update_card_pos()

            System.update_all()


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
        play_rect = pygame.Rect(200, 200, 400, 300)
        play_pos = pygame.Vector2(play_rect.x, play_rect.y)
        deck_pos = pygame.Vector2(100, 600)
        symbol_pos = {
            SWORD: pygame.Vector2(750, 400),
            ARROW: pygame.Vector2(750, 450),
            JUMP: pygame.Vector2(750, 500),
        }
        other_hero_pos = dict(
            zip(
                [hn for hn in ["Ranger", "Barbarian"] if hn != hero_name],
                [
                    pygame.Vector2(50, 50),
                    pygame.Vector2((1024 // 2) - 25, 50),
                    pygame.Vector2(1024 - 50 - 50, 50),
                ],
            )
        )

        screen = pygame.display.set_mode(size)

        print("initialize game")
        Game().run()
    except Exception:
        print("error in UI thread")
        traceback.print_exc()
        close_network()
        pygame.quit()
        sys.exit()
