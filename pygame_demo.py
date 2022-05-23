import sys
import pygame
pygame.init()

size = width, height = 320, 240
speed = [2, 2]
black = 0, 0, 0

screen = pygame.display.set_mode(size)

ball = pygame.image.load("intro_ball.gif")
ballrect = ball.get_rect()

mousex = 10
mousey = 10

while 1:
    for event in pygame.event.get():
        if event.type == pygame.QUIT: sys.exit()

    mousex, mousey = pygame.mouse.get_pos()
    ballrect.x = mousex
    ballrect.y = mousey

    screen.fill(black)
    screen.blit(ball, ballrect)
    pygame.display.flip()
