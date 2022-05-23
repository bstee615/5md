import sys
import pygame
pygame.init()

size = width, height = 320, 240
speed = [2, 2]
black = 0, 0, 0

screen = pygame.display.set_mode(size)

class Handle:
    """Grabbable handle on object"""
    def __init__(self):
        self.grabbed = False
        self.grab_offset = pygame.Vector2()

class MyObject:
    def __init__(self, obj):
        self.fields = {}
        self.fields["object"] = obj
        self.fields["rect"] = obj.get_rect()
        self.fields["handle"] = Handle()

class GameState:
    """Global game state"""
    def __init__(self):
        self.mouse_pos = pygame.Vector2(pygame.mouse.get_pos())
        self.object_handles = []
        self.grabbed = []

    def add_object(self, obj):
        self.object_handles.append(MyObject(obj))

    def try_pickup(self):
        for obj in self.object_handles:
            obj_rect = obj.fields["rect"]
            obj_handle = obj.fields["handle"]
            if obj_rect.collidepoint(self.mouse_pos):
                obj_handle.grab_offset = pygame.Vector2(self.mouse_pos.x - obj_rect.x, self.mouse_pos.y - obj_rect.y)
                print("mouse", self.mouse_pos, "ball", obj_rect, "offset", obj_handle.grab_offset)
                self.grabbed.append(obj)

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
                    self.grabbed = []

        state.update_mouse_pos()
        
        for o in self.grabbed:
            o_rect = o.fields["rect"]
            o_handle = o.fields["handle"]
            o_rect.x = self.mouse_pos.x - o_handle.grab_offset[0]
            o_rect.y = self.mouse_pos.y - o_handle.grab_offset[1]

        screen.fill(black)
        for o in self.object_handles:
            screen.blit(o.fields["object"], o.fields["rect"])
        pygame.display.flip()

state = GameState()
state.add_object(pygame.image.load("intro_ball.gif"))
while 1:
    state.step()
