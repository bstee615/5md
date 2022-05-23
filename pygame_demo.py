import sys
import pygame
pygame.init()

size = width, height = 320, 240
speed = [2, 2]
black = 0, 0, 0

screen = pygame.display.set_mode(size)

class Handle:
    def __init__(self, obj):
        self.obj = obj
        self.grabbed = False
        self.grab_offset = pygame.Vector2()

    def __repr__(self):
        return repr(self.obj)


ball = pygame.image.load("intro_ball.gif")
ballrect = Handle(ball.get_rect())

class GameState:
    def __init__(self):
        self.mouse_pos = pygame.Vector2(pygame.mouse.get_pos())

    def try_pickup(self, ballrect):
        if ballrect.obj.collidepoint(self.mouse_pos):
            ballrect.grab_offset = pygame.Vector2(self.mouse_pos.x - ballrect.obj.x, self.mouse_pos.y - ballrect.obj.y)
            print("mouse", self.mouse_pos, "ball", ballrect, "offset", ballrect.grab_offset)
            ballrect.grabbed = True
        else:
            ballrect.grabbed = False

    def update_mouse_pos(self):
        self.mouse_pos.update(pygame.mouse.get_pos())
        
    def step(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT: sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                left, middle, right = pygame.mouse.get_pressed()
                if left:
                    self.try_pickup(ballrect)
            if event.type == pygame.MOUSEBUTTONUP:
                left, middle, right = pygame.mouse.get_pressed()
                if not left:
                    ballrect.grabbed = False

        state.update_mouse_pos()

        if ballrect.grabbed:
            ballrect.obj.x = self.mouse_pos.x - ballrect.grab_offset[0]
            ballrect.obj.y = self.mouse_pos.y - ballrect.grab_offset[1]

        screen.fill(black)
        screen.blit(ball, ballrect.obj)
        pygame.display.flip()

state = GameState()
while 1:
    state.step()
