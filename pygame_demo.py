import sys
import pygame
import simple_websocket

from model import SymbolCard, Symbols
pygame.init()

size = width, height = 1024, 768
background = pygame.image.load("bg.png")

screen = pygame.display.set_mode(size)

"""NETWORKING"""
networking = False

if networking:
    ws = simple_websocket.Client('ws://localhost:5000/game')

def send_ws_command(cmd):
    print("send_ws_command", cmd)
    if networking:
        ws.send(cmd)
def close_network():
    if networking:
        ws.close()
"""NETWORKING"""

class Handle:
    """Grabbable handle on object"""
    def __init__(self):
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
            p.set_pos(pygame.Vector2(self.fields["rect"].x, self.fields["rect"].y) - p_off, touched.union({self}))

    def add_child(self, obj, offset):
        obj.set_pos(pygame.Vector2(self.fields["rect"].x, self.fields["rect"].y) + offset)
        self.children.append((obj, offset))
        obj.fields["parent"] = (self, offset)
    
    def __repr__(self):
        return f"{self.fields}"

class GameModel:
    def __init__(self):
        self.cards = [
            SymbolCard({Symbols.SWORD: 1}),
            SymbolCard({Symbols.ARROW: 1}),
            SymbolCard({Symbols.JUMP: 1})
        ]
        self.play_area_cards = []

class GameState:
    """Global game state"""
    def __init__(self):
        self.mouse_pos = pygame.Vector2(pygame.mouse.get_pos())
        self.object_handles = []
        self.named_objects = {}
        self.model = GameModel()
        
        self.init_objects()
    
    def move_to_hand_position(self, card_obj, i):
        space_between_cards = 125
        x = (1024 // 2) - 50 - ((space_between_cards * len(self.model.cards)) // 2) + (space_between_cards * i)
        y = 600
        card_obj.set_pos(pygame.Vector2(x, y))
    
    def move_to_play_area_position(self, card_obj, i):
        play_rect = self.named_objects["play_area"].fields["rect"]
        card_offset = 125
        left = play_rect.x + (card_offset * i)
        card_obj.set_pos(pygame.Vector2(left, play_rect.y))

    def init_objects(self):
        enemy_board = self.add_object(pygame.transform.scale(pygame.image.load("playing_board.jpg"), (250, 100)))
        enemy_board.set_pos(pygame.Vector2(650, 400))

        self.add_object(pygame.Rect(200, 200, 400, 300), name="play_area")

        for i, card in enumerate(self.model.cards):
            card_obj = self.add_object(
                pygame.transform.scale(pygame.image.load("card_king_hearts.jpg"), (100, 150)),
                draggable=True
                )
            card_obj.fields["hand_index"] = i
            card_obj.fields["model"] = card
            self.move_to_hand_position(card_obj, i)

        p1 = self.add_object(pygame.Rect(50, 50, 50, 50))
        p2 = self.add_object(pygame.Rect((1024 // 2) - 25, 50, 50, 50))
        p3 = self.add_object(pygame.Rect(1024 - 50 - 50, 50, 50, 50))

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
                obj_handle.grab_offset = pygame.Vector2(self.mouse_pos.x - obj_rect.x, self.mouse_pos.y - obj_rect.y)
                print("mouse", self.mouse_pos, "object", obj_rect, "offset", obj_handle.grab_offset)
                obj_handle.grabbed = True

    def drop(self):
        play_rect = self.named_objects["play_area"].fields["rect"]
        for o in self.object_handles:
            if "handle" in o.fields and "rect" in o.fields:
                o_rect = o.fields["rect"]
                if o.fields["handle"].grabbed:
                    o.fields["handle"].grabbed = False
                    if play_rect.colliderect(o_rect) or "play_area_index" in o.fields:
                        print("play card", play_rect, o_rect)
                        if "play_area_index" not in o.fields:
                            card_str = repr(o.fields["model"])
                            send_ws_command(f"play_hero_card Ranger {card_str}")
                        play_area_index = o.fields.get("play_area_index", None)
                        if play_area_index is None:
                            play_area_index = o.fields["play_area_index"] = max(c.fields.get("play_area_index", -1) for c in self.object_handles) + 1
                        self.move_to_play_area_position(o, play_area_index)

    def update_mouse_pos(self):
        self.mouse_pos.update(pygame.mouse.get_pos())
        
    def step(self):
        for event in pygame.event.get():
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

        state.update_mouse_pos()
        
        for o in self.object_handles:
            if "handle" in o.fields:
                if o.fields["handle"].grabbed:
                    if "handle" in o.fields and "rect" in o.fields:
                        o_rect = o.fields["rect"]
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
    state.step()
