import random
import math
import pygame
from calcs import rectRotation


class Background:
    def __init__(self, screen, screenWidth, screenHeight, lineColor1, lineColor2, squareColor1, squareColor2,
                 scaleDownFactor=5, numSquares=20, squareSizeRange=(3, 6), squareBorderWidth=(4, 14),
                 squareSpeedRange=(-0.2, -0.1), squareRotSpeed=0.01, numLines=10, lineSpeed=0.2,
                 lineThicknessRange=(10, 12), numLineScreensStored=10):
        self.homeScreen = screen
        self.scaleDownFactor = scaleDownFactor
        self.screen = pygame.Surface((screenWidth / scaleDownFactor, screenHeight / scaleDownFactor)).convert_alpha()
        self.numLineScreensStored = numLineScreensStored
        self.lineSpeed = lineSpeed * self.numLineScreensStored
        self.linesYOffset = 0
        self.linesScreen = pygame.Surface((screenWidth / scaleDownFactor,
                                           self.numLineScreensStored * screenHeight / scaleDownFactor + 3 * max(
                                               lineThicknessRange))).convert_alpha()
        self.screenWidth = screenWidth / scaleDownFactor
        self.screenHeight = screenHeight / scaleDownFactor
        self.lineThicknessRange = lineThicknessRange
        self.squares = []
        for _ in range(numSquares):
            size = random.randint(*squareSizeRange) ** 2
            borderWidth = min(max(random.randint(*squareBorderWidth), size - 2), int(size / 4))
            speed = random.uniform(*squareSpeedRange)
            rotSpeed = squareRotSpeed * (random.randint(0, 1) * 2 - 1)
            self.squares.append(
                BackgroundSquare(self.screenWidth, self.screenHeight, size, borderWidth, squareColor1, squareColor2,
                                 speed, rotSpeed))
        self.lines = []
        yOffset = 200
        spacing = (self.screenHeight + yOffset) / numLines
        for i in range(numLines * self.numLineScreensStored):
            initY = i * spacing
            thickness = random.randint(*lineThicknessRange)
            self.lines.append(
                BackgroundLine(self.screenWidth, self.screenHeight, initY - yOffset, thickness, lineColor1, lineColor2,
                               yOffset, scaleDownFactor))

        self.linesScreen.fill((0, 0, 0, 0))
        for line in self.lines:
            line.draw(self.linesScreen)
        self.scaledSurfaceLines = pygame.transform.scale(self.linesScreen,
                                                         (int(self.screenWidth * self.scaleDownFactor),
                                                          int(self.numLineScreensStored * self.screenHeight * self.scaleDownFactor + 3 * max(
                                                              self.lineThicknessRange))))

    def update(self, deltaT):
        for square in self.squares:
            square.update(deltaT)
        self.linesYOffset += self.lineSpeed * deltaT
        if self.linesYOffset > 0:
            self.linesYOffset = -self.linesScreen.get_height()

    def draw(self):
        self.screen.fill((0, 0, 0, 0))
        for square in self.squares:
            square.draw(self.screen)
        scaledSurface = pygame.transform.scale(self.screen, (int(self.screenWidth * self.scaleDownFactor),
                                                             int(self.screenHeight * self.scaleDownFactor)))
        self.homeScreen.blit(scaledSurface, (0, 0))
        self.homeScreen.blit(self.scaledSurfaceLines, (0, -3 * max(self.lineThicknessRange) + self.linesYOffset))


class BackgroundSquare:
    def __init__(self, screenWidth, screenHeight, size, borderWidth, color1, color2, speed, rotSpeed):
        self.screenWidth = screenWidth
        self.screenHeight = screenHeight
        self.x = random.randint(0, int(screenWidth))
        self.y = random.randint(0, int(screenHeight))
        self.angle = random.uniform(0, math.pi)
        self.color1 = color1
        self.color2 = color2
        self.size = size
        self.borderWidth = borderWidth
        self.speed = speed
        self.rotSpeed = rotSpeed
        self.poly = rectRotation((self.x, self.y), self.size, self.size, self.angle)

    def update(self, deltaT):
        self.angle += self.rotSpeed * deltaT
        self.y += self.speed * deltaT
        if self.y + self.size < 0:
            self.y = self.screenHeight + self.size
            self.x = random.randint(0, self.screenWidth)
        self.poly = rectRotation((self.x, self.y), self.size, self.size, self.angle)

    def draw(self, surface):
        pygame.draw.polygon(surface, self.color1, self.poly)
        pygame.draw.polygon(surface, (0, 0, 0, 0),
                            rectRotation((self.x, self.y), self.size - self.borderWidth, self.size - self.borderWidth,
                                         self.angle))
        pygame.draw.polygon(surface, self.color2, rectRotation((self.x, self.y), self.size, self.size, self.angle), 1)
        pygame.draw.polygon(surface, self.color2,
                            rectRotation((self.x, self.y), self.size - self.borderWidth, self.size - self.borderWidth,
                                         self.angle), 1)


class BackgroundLine:
    def __init__(self, screenWidth, screenHeight, initY, thickness, color1, color2, yOffset, scaleDownFactor):
        self.screenWidth = screenWidth
        self.screenHeight = screenHeight
        self.y = initY
        self.thickness = thickness  # Now used as the polygon height.
        self.color1 = color1
        self.color2 = color2
        self.yOffset = yOffset
        self.scaleDownFactor = scaleDownFactor

    def draw(self, surface):
        # Define the top edge using an offset for extra width.
        extraOffset = 3 * self.thickness
        topLeft = (-extraOffset, self.y)
        topRight = (self.screenWidth + extraOffset, self.y + self.yOffset)
        # Bottom edge is the top edge shifted down vertically by 'height' (here, self.thickness).
        bottomRight = (topRight[0], topRight[1] + self.thickness)
        bottomLeft = (topLeft[0], topLeft[1] + self.thickness)
        pygame.draw.polygon(surface, self.color1, [topLeft, topRight, bottomRight, bottomLeft])
        pygame.draw.polygon(surface, self.color2, [topLeft, topRight, bottomRight, bottomLeft], 1)
