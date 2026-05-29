import pygame
from text import draw_text


class button:
    def __init__(self, x, y, w, h, r, text, font, col, border_col, text_col, text_shadow_col):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.rect = pygame.rect.Rect(self.x - self.w / 2, self.y - self.h / 2, self.w, self.h)
        self.text = text
        self.font = font
        self.roundness = r
        self.col = col
        self.border_col = border_col
        self.text_col = text_col
        self.text_shadow_col = text_shadow_col

    def draw(self, s, mouse_x, mouse_y, c):
        if c and self.rect.collidepoint((mouse_x, mouse_y)):
            pygame.draw.rect(s, self.col,
                             (self.rect.x, self.rect.y + self.rect.height / 10, self.rect.width, self.rect.height), 0,
                             self.roundness)
            pygame.draw.rect(s, self.border_col,
                             (self.rect.x, self.rect.y + self.rect.height / 10, self.rect.width, self.rect.height), 2,
                             self.roundness)
            draw_text(s, self.text_col, self.text_shadow_col, self.font, self.rect.centerx,
                      self.rect.centery + self.rect.height / 10, True, str(self.text), 2, True, self.w)
        else:
            pygame.draw.rect(s, self.col, self.rect, 0, self.roundness)
            pygame.draw.rect(s, self.border_col, self.rect, 2, self.roundness)
            draw_text(s, self.text_col, self.text_shadow_col, self.font, self.rect.centerx, self.rect.centery, True,
                      str(self.text), 2, True, self.w)

    def update(self, mouse_x, mouse_y, c):
        if c:
            if self.rect.collidepoint((mouse_x, mouse_y)):
                return True


def create_buttons(num_hor, num_ver, space_hor, space_ver, width, height, text, clicked, coord):
    timer = []
    buttons_list = []
    text_list = []
    color_list = []
    for i in range(num_hor):
        for o in range(num_ver):
            buttons_list.append(
                pygame.Rect(coord[0] + (width + space_hor) * i, coord[1] + (height + space_ver) * o, width, height))
            clicked.append(False)
    for i in range(num_hor * num_ver):
        text_list.append(text[i])
    for i in range(num_hor * num_ver):
        timer.append(0)
    return [buttons_list, text_list, clicked, color_list, timer]


def draw_buttons(button_rect_list, button_text_list, button_clicked_list, color_list, timer_list, screen, border_width,
                 corner_radius, font, c, mX, mY):
    for i, b in enumerate(button_rect_list):
        button_text = button_text_list[i]
        button_color = color_list[0]
        text_color = color_list[1]
        text_length, text_height = pygame.font.Font.size(font, button_text)
        text_pos = button_rect_list[i].x + button_rect_list[i].width / 2 - text_length / 2, button_rect_list[i].y + \
                   button_rect_list[i].height / 2 - text_height / 2
        if pygame.Rect.collidepoint(button_rect_list[i], (mX, mY)):
            button_color = color_list[2]
            if c:
                button_clicked_list[i] = True
                timer_list[i] = 10
        else:
            button_clicked_list[i] = False
        if timer_list[i] > 0:
            button_color = color_list[3]
            timer_list[i] -= 1
        pygame.draw.rect(screen, button_color, button_rect_list[i], border_width, corner_radius)
        screen.blit(font.render(button_text, True, text_color), text_pos)
