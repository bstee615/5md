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

offset = (0, 0)
grabbed = False
pressed_left = False

while 1:
    for event in pygame.event.get():
        if event.type == pygame.QUIT: sys.exit()
        if event.type == pygame.MOUSEBUTTONDOWN:
            left, middle, right = pygame.mouse.get_pressed()
            if left:
                pressed_left = True
                if ballrect.collidepoint((mousex, mousey)):
                    offset = (mousex - ballrect.x, mousey - ballrect.y)
                    print("mouse", (mousex, mousey), "ball", (ballrect.x, ballrect.y), "offset", offset)
                    grabbed = True
                else:
                    grabbed = False
        if event.type == pygame.MOUSEBUTTONUP:
            left, middle, right = pygame.mouse.get_pressed()
            if not left:
                pressed_left = False

    mousex, mousey = pygame.mouse.get_pos()

    new_pressed_left = pygame.mouse.get_pressed()[0]
    if pressed_left and grabbed:
        ballrect.x = mousex - offset[0]
        ballrect.y = mousey - offset[1]

    screen.fill(black)
    screen.blit(ball, ballrect)
    pygame.display.flip()
