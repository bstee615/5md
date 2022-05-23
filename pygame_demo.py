import sys
import pygame
pygame.init()

size = width, height = 800, 600
black = 0, 0, 0

screen = pygame.display.set_mode(size)

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

class GameState:
    """Global game state"""
    def __init__(self):
        self.mouse_pos = pygame.Vector2(pygame.mouse.get_pos())
        self.object_handles = []
        self.named_objects = {}

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
        enemy_rect = enemy_board_playzone.fields["rect"]
        for o in self.object_handles:
            if "handle" in o.fields and "rect" in o.fields:
                o_rect = o.fields["rect"]
                if o.fields["handle"].grabbed:
                    o.fields["handle"].grabbed = False
                    if enemy_rect.colliderect(o_rect):
                        print("played card", enemy_rect, o_rect)

    def update_mouse_pos(self):
        self.mouse_pos.update(pygame.mouse.get_pos())
        
    def step(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT: sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                left, middle, right = pygame.mouse.get_pressed()
                if left:
                    self.try_pickup()
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

        screen.fill(black)
        for o in self.object_handles:
            if isinstance(o.fields["object"], pygame.Surface):
                screen.blit(o.fields["object"], o.fields["rect"])
            elif isinstance(o.fields["object"], pygame.Rect):
                pygame.draw.rect(screen, "red", o.fields["rect"], width=5)
        pygame.display.flip()

state = GameState()
enemy_board = state.add_object(pygame.transform.scale(pygame.image.load("playing_board.jpg"), (400, 200)))
king_card = state.add_object(pygame.transform.scale(pygame.image.load("card_king_hearts.jpg"), (100, 200)), draggable=True)
king_card.add_child(state.add_object(pygame.transform.scale(pygame.image.load("ranger_playing_board.jpg"), (200, 100)), draggable=True), pygame.Vector2())

enemy_board.set_pos(pygame.Vector2(300, 300))
enemy_board_playzone = state.add_object(pygame.Rect(0, 0, 100, 100))
enemy_board.add_child(enemy_board_playzone, pygame.Vector2(250, 50))

while 1:
    state.step()
