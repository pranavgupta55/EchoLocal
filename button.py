import pygame
from text import drawText


class Button:
    def __init__(self, x, y, w, h, r, text, font, col, border_col, text_col, text_shadow_col=None):
        # x and y represent the center of the button
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.rect = pygame.Rect(self.x - self.w / 2, self.y - self.h / 2, self.w, self.h)
        self.text = str(text)
        self.font = font
        self.roundness = r
        self.col = col
        self.border_col = border_col
        self.text_col = text_col
        self.text_shadow_col = text_shadow_col

    def draw(self, surface, mouse_x, mouse_y, clicked):
        is_hovered = self.rect.collidepoint((mouse_x, mouse_y))

        # Physical push down effect
        y_offset = self.rect.height / 10 if (is_hovered and clicked) else 0

        # Calculate visual rect for this frame
        current_rect = pygame.Rect(self.rect.x, self.rect.y + y_offset, self.rect.width, self.rect.height)

        # Draw Background
        pygame.draw.rect(surface, self.col, current_rect, 0, self.roundness)

        # Draw Border
        if self.border_col:
            pygame.draw.rect(surface, self.border_col, current_rect, 2, self.roundness)

        # Draw Text (Centered Vertically and Horizontally, with optional Wrap and Shadow)
        drawText(surface, self.text_col, self.font, current_rect.centerx, current_rect.centery,
                 self.text, color2=self.text_shadow_col, shadowSize=2 if self.text_shadow_col else 0,
                 wrap=True, maxLen=self.w - 10, justify="center", centeredVertically=True)

    def update(self, mouse_x, mouse_y, clicked):
        """Returns True if the button is successfully clicked."""
        if clicked and self.rect.collidepoint((mouse_x, mouse_y)):
            return True
        return False


def create_buttons(num_hor, num_ver, space_hor, space_ver, width, height, text_list, coord):
    """Refactored helper for generating a grid of buttons."""
    buttons_list = []
    texts = []
    clicked = []
    timers = []

    for i in range(num_hor):
        for j in range(num_ver):
            # coord represents the top-left of the grid
            x = coord[0] + (width + space_hor) * i
            y = coord[1] + (height + space_ver) * j
            buttons_list.append(pygame.Rect(x, y, width, height))

            # Safe index handling for texts
            idx = i * num_ver + j
            texts.append(text_list[idx] if idx < len(text_list) else "")
            clicked.append(False)
            timers.append(0)

    return buttons_list, texts, clicked, timers


def draw_buttons(button_rect_list, button_text_list, button_clicked_list, color_list, timer_list,
                 screen, border_width, corner_radius, font, c, mX, mY):
    """Refactored grid drawer if needed elsewhere in your code."""
    for i, rect in enumerate(button_rect_list):
        button_text = button_text_list[i]

        # Color unpacking: [base, text, hover, active]
        button_color = color_list[0]
        text_color = color_list[1]

        is_hovered = rect.collidepoint((mX, mY))

        if is_hovered:
            button_color = color_list[2] if len(color_list) > 2 else button_color
            if c:
                button_clicked_list[i] = True
                timer_list[i] = 10
        else:
            button_clicked_list[i] = False

        if timer_list[i] > 0:
            button_color = color_list[3] if len(color_list) > 3 else button_color
            timer_list[i] -= 1

        pygame.draw.rect(screen, button_color, rect, border_width, corner_radius)
        drawText(screen, text_color, font, rect.centerx, rect.centery, button_text,
                 justify="center", centeredVertically=True)
