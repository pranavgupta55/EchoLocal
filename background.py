import random
import math
import pygame
import colorsys
from calcs import rectRotation, brightness, shift_hue


def get_sorted_colors(c1, c2):
    """Sorts two RGB colors based on saturation. Returns (bg_color, fg_base_color)"""
    hsv1 = colorsys.rgb_to_hsv(c1[0] / 255, c1[1] / 255, c1[2] / 255)
    hsv2 = colorsys.rgb_to_hsv(c2[0] / 255, c2[1] / 255, c2[2] / 255)
    if hsv1[1] < hsv2[1]:
        return c1, c2
    return c2, c1


class Background:
    def __init__(self, screen, screenWidth, screenHeight, colorPair,
                 scaleDownFactor=2, numSquares=30, squareSizeRange=(6, 12), squareBorderWidth=(8, 18),
                 squareSpeedRange=(-4.5, -3.2), squareRotSpeed=0.20, numLines=10, lineSpeed=0.2,
                 lineThicknessRange=(20, 45), numLineScreensStored=5):

        self.homeScreen = screen
        self.scaleDownFactor = int(scaleDownFactor)

        # Color processing: bg is less saturated, foreground is more saturated
        base_bg, fgColor = get_sorted_colors(colorPair[0], colorPair[1])
        self.bgColor = brightness(base_bg, 0.35)

        lineColor1 = brightness(fgColor, 0.8)
        lineColor2 = shift_hue(fgColor, 0.05)
        squareColor1 = brightness(fgColor, 1.1)
        squareColor2 = shift_hue(fgColor, -0.05)

        self.screenWidth = int(screenWidth / scaleDownFactor)
        self.screenHeight = int(screenHeight / scaleDownFactor)

        # We process speed scaling identically to the user's preferred previous speed
        # lineSpeed of 1.5 mapping to roughly 750 pixels/sec
        self.lineSpeed = -float(abs(lineSpeed) * 500)

        self.screen = pygame.Surface((self.screenWidth, self.screenHeight)).convert_alpha()

        # Generate Squares
        self.squares = []
        for _ in range(numSquares):
            size = random.randint(*squareSizeRange) ** 2
            borderWidth = min(max(random.randint(*squareBorderWidth), size - 2), int(size / 4))
            speed = random.uniform(*squareSpeedRange)
            rotSpeed = squareRotSpeed * (random.randint(0, 1) * 2 - 1)
            self.squares.append(
                BackgroundSquare(self.screenWidth, self.screenHeight, size, borderWidth, squareColor1, squareColor2,
                                 speed, rotSpeed))

        # --- SEAMLESS LINE SCROLLING SETUP ---
        yOffset = 200
        self.spacing = (self.screenHeight + yOffset) / numLines

        self.lines_per_screen = numLines
        # A unique pattern consisting of the first 2 screens worth of lines
        self.pattern_length = 2 * self.lines_per_screen
        pattern_thicknesses = [random.randint(*lineThicknessRange) for _ in range(self.pattern_length)]

        # We generate exactly 5 screens worth of lines vertically stacked
        total_screens = 5
        self.total_lines = total_screens * self.lines_per_screen

        self.lines = []
        for i in range(self.total_lines):
            initY = i * self.spacing
            # Modulo applies the duplicated thickness pattern exactly
            thickness = pattern_thicknesses[i % self.pattern_length]
            self.lines.append(
                BackgroundLine(self.screenWidth, self.screenHeight, initY - yOffset, thickness, lineColor1, lineColor2,
                               yOffset, scaleDownFactor)
            )

        # Allocate base surface height to fit all 5 screens
        surface_height = int(self.total_lines * self.spacing + yOffset + max(lineThicknessRange))
        self.linesScreen = pygame.Surface((self.screenWidth, surface_height)).convert_alpha()
        self.linesScreen.fill((0, 0, 0, 0))
        for line in self.lines:
            line.draw(self.linesScreen)

        # Upscale the massive 5-screen surface once
        self.scaledSurfaceLines = pygame.transform.scale(self.linesScreen,
                                                         (int(self.screenWidth * self.scaleDownFactor),
                                                          int(surface_height * self.scaleDownFactor)))

        # Calculate exact pixel threshold for a mathematically perfect 4-screen loop jump
        self.looping_distance_downscaled = 4 * self.lines_per_screen * self.spacing
        self.looping_distance_upscaled = self.looping_distance_downscaled * self.scaleDownFactor
        self.exact_y_offset = 0.0

    def update(self, deltaT):
        for square in self.squares:
            square.update(deltaT)

        # Scroll upwards (offset moves into negative bounds)
        self.exact_y_offset += self.lineSpeed * deltaT

        # When we scroll up by exactly 4 screens, reset to 0.
        # Because Screen 5 visually matches Screen 1, this jump is completely invisible.
        self.exact_y_offset = -(abs(self.exact_y_offset) % self.looping_distance_upscaled)

    def draw(self):
        # 1. Background Fill
        self.homeScreen.fill(self.bgColor)

        # 2. Draw 5-Screen Seamless Loop Surface
        pixel_perfect_offset = int(self.exact_y_offset)
        self.homeScreen.blit(self.scaledSurfaceLines, (0, pixel_perfect_offset))

        # 3. Draw Squares
        self.screen.fill((0, 0, 0, 0))
        for square in self.squares:
            square.draw(self.screen)
        scaledSurface = pygame.transform.scale(self.screen, (int(self.screenWidth * self.scaleDownFactor),
                                                             int(self.screenHeight * self.scaleDownFactor)))
        self.homeScreen.blit(scaledSurface, (0, 0))


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
        self.thickness = thickness
        self.color1 = color1
        self.color2 = color2
        self.yOffset = yOffset
        self.scaleDownFactor = scaleDownFactor

    def draw(self, surface):
        extraOffset = 3 * self.thickness
        topLeft = (-extraOffset, self.y)
        topRight = (self.screenWidth + extraOffset, self.y + self.yOffset)
        bottomRight = (topRight[0], topRight[1] + self.thickness)
        bottomLeft = (topLeft[0], topLeft[1] + self.thickness)

        pygame.draw.polygon(surface, self.color1, [topLeft, topRight, bottomRight, bottomLeft])
        pygame.draw.polygon(surface, self.color2, [topLeft, topRight, bottomRight, bottomLeft], 1)
