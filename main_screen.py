import math
import time
import os
import io
import threading
import random
import pygame
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC
from PIL import Image

try:
    from pydub import AudioSegment

    HAS_PYDUB = True
except ImportError:
    HAS_PYDUB = False
    print("Warning: pydub not installed. Volume normalization will be skipped.")

from calcs import brightness
from text import drawText
from fontDict import fonts
from background import Background, get_sorted_colors
from button import Button

# ----------------- Palette & Color Logic -----------------
flat_colors = [[146, 133, 160], [111, 94, 144], [221, 198, 174], [205, 92, 105], [86, 70, 69], [57, 42, 75],
               [186, 77, 93], [48, 56, 96], [84, 120, 115], [154, 96, 121], [241, 227, 195], [230, 230, 219],
               [74, 111, 129], [58, 68, 72], [69, 31, 74], [192, 79, 77], [42, 47, 70], [55, 34, 78],
               [119, 73, 99], [67, 58, 80], [75, 121, 119], [85, 95, 72], [115, 120, 150], [71, 56, 107],
               [187, 188, 204], [219, 211, 211], [79, 69, 102], [89, 31, 29], [76, 44, 80], [237, 229, 215],
               [154, 130, 127], [75, 58, 99], [226, 218, 168],[130, 139, 100], [104, 169, 169], [95, 31, 55],
               [209, 217, 176], [164, 110, 96], [115, 139, 84], [145, 179, 152], [176, 103, 90],
               [85, 73, 109], [32, 72, 94], [15, 114, 107], [33, 68, 70], [16, 72, 97]]

BG_PAIRS = [(flat_colors[i], flat_colors[i + 1]) for i in range(0, len(flat_colors), 2)]

# Dynamic Global Palette Variables
ui_bg, ui_panel, ui_accent, ui_text, ui_text_dim = (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0)


def init_palette(pair):
    """Generates cohesive UI colors based on the current background pair"""
    global ui_bg, ui_panel, ui_accent, ui_text, ui_text_dim
    base_bg, fg_base = get_sorted_colors(pair[0], pair[1])
    ui_bg = brightness(base_bg, 0.35)  # Very dark background for text legibility
    ui_panel = brightness(base_bg, 0.6)  # Slightly lighter for panels/sliders
    ui_accent = fg_base  # Full saturation accent color
    ui_text = (245, 245, 245)  # Crisp off-white text
    ui_text_dim = (180, 180, 180)  # Dimmed text for artists/timestamps


# Initialize with a random palette for the Startup/Menu screen
init_palette(random.choice(BG_PAIRS))

pygame.init()
pygame.mixer.init()

# ----------------- Safe Hotkey Bindings -----------------
PLAY_KEYS = [pygame.K_SPACE, pygame.K_k]
NEXT_KEYS = [pygame.K_RIGHT, pygame.K_DOWN]
PREV_KEYS = [pygame.K_LEFT, pygame.K_UP]

for attr in ["K_AUDIOPLAY", "K_AUDIO_PLAY", "K_MEDIA_PLAY_PAUSE", "K_AUDIOPAUSE"]:
    if hasattr(pygame, attr): PLAY_KEYS.append(getattr(pygame, attr))
for attr in ["K_AUDIONEXT", "K_AUDIO_NEXT", "K_MEDIA_NEXT_TRACK"]:
    if hasattr(pygame, attr): NEXT_KEYS.append(getattr(pygame, attr))
for attr in ["K_AUDIOPREV", "K_AUDIO_PREV", "K_MEDIA_PREV_TRACK"]:
    if hasattr(pygame, attr): PREV_KEYS.append(getattr(pygame, attr))

# ----------------- Configuration & Globals -----------------
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
native_w, native_h = screen.get_width(), screen.get_height()
clock = pygame.time.Clock()
fps = 60

# Background renders rougher (Scale 3)
scaleDownFactorBG = 2
screenWidthBG = native_w // scaleDownFactorBG
screenHeightBG = native_h // scaleDownFactorBG

# UI renders sharper (Scale 2)
scaleDownFactorUI = 1
screenWidthUI = native_w // scaleDownFactorUI
screenHeightUI = native_h // scaleDownFactorUI

screenUI = pygame.Surface((screenWidthUI, screenHeightUI), pygame.SRCALPHA)

# Manually optimized text sizes for the Sharper UI layer
titleFont = fonts["bold30"]
artistFont = fonts["regular20"]
queueTitleFont = fonts["bold18"]
queueArtistFont = fonts["thin14"]


class AppState:
    MENU = 0
    LOADING = 1
    PLAYER = 2


current_state = AppState.MENU
loading_progress = 0
loading_status = ""

songs_data = []
system_queue = []
user_queue = []
history_stack = []

current_song_idx = -1
current_song_origin = "system"
current_bg = None
is_playing = False
is_repeat = False
is_muted = False
current_playback_time = 0.0

incognitoToggle = False

basePath = "../../../pranavgupta/Desktop/TimbreUpl/"
folders = [basePath + ["Part 1", "Part 2"][i] for i in range(2)]


# ----------------- Utilities -----------------
def create_circular_mask(image_surface, size):
    scaled = pygame.transform.smoothscale(image_surface, (size, size))
    mask = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(mask, (255, 255, 255, 255), (size // 2, size // 2), size // 2)
    mask.blit(scaled, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    return mask


def get_dominant_color(pil_img):
    img = pil_img.copy().convert("RGB")
    img.thumbnail((50, 50))
    colors = img.getcolors(2500)
    if colors:
        sorted_colors = sorted(colors, key=lambda t: t[0], reverse=True)
        return sorted_colors[0][1]
    return (255, 255, 255)


def format_time(seconds):
    seconds = int(max(0, seconds))
    m = seconds // 60
    s = seconds % 60
    return f"{m}:{s:02d}"


def truncate_text(font, text, max_width):
    text = str(text)
    if font.size(text)[0] <= max_width: return text
    for i in range(len(text), 0, -1):
        if font.size(text[:i] + "...")[0] <= max_width:
            return text[:i] + "..."
    return "..."


# ----------------- Background Thread -----------------
def load_songs_thread():
    global loading_progress, loading_status, current_state, songs_data, system_queue

    raw_paths = []
    for folder in folders:
        if os.path.exists(folder):
            for file in os.listdir(folder):
                if file.lower().endswith(".mp3") and not file.startswith("."):
                    raw_paths.append(os.path.join(folder, file))
    raw_paths.sort()

    total = len(raw_paths)
    for i, path in enumerate(raw_paths):
        loading_status = f"Loading: {os.path.basename(path)[:20]}..."
        try:
            audio = MP3(path)
            duration = audio.info.length

            title = os.path.basename(path).replace(".mp3", "")
            artist = "Unknown Artist"
            image_surface = pygame.Surface((300, 300))
            image_surface.fill(ui_panel)
            ring_col = ui_accent

            if audio.tags:
                if 'TIT2' in audio.tags: title = str(audio.tags['TIT2'].text[0])
                if 'TPE1' in audio.tags: artist = str(audio.tags['TPE1'].text[0])

                for tag in audio.tags.values():
                    if isinstance(tag, APIC):
                        pil_img = Image.open(io.BytesIO(tag.data)).convert("RGBA")
                        data = pil_img.tobytes()
                        image_surface = pygame.image.fromstring(data, pil_img.size, "RGBA")
                        ring_col = get_dominant_color(pil_img)
                        break

            norm_vol = 1.0
            if HAS_PYDUB:
                try:
                    seg = AudioSegment.from_mp3(path)[:15000]
                    change_in_dbfs = -16.0 - seg.dBFS
                    norm_vol = 10 ** (change_in_dbfs / 20)
                except Exception:
                    pass

            circled_art = create_circular_mask(image_surface, 400)
            thumbnail = create_circular_mask(image_surface, 40)
            color_pair = BG_PAIRS[i % len(BG_PAIRS)]

            songs_data.append({
                "path": path,
                "title": title,
                "artist": artist,
                "duration": duration,
                "vol": min(norm_vol, 1.5),
                "art": circled_art,
                "thumb": thumbnail,
                "ring_color": ring_col,
                "color_pair": color_pair
            })

        except Exception as e:
            print(f"Error loading {path}: {e}")

        loading_progress = (i + 1) / total

    system_queue = list(range(len(songs_data)))
    random.shuffle(system_queue)
    loading_status = "Done!"
    current_state = AppState.PLAYER

    first_idx, first_origin = get_next_song()
    play_song(first_idx, first_origin)


# ----------------- Playback Logic -----------------
def get_next_song():
    global system_queue
    if len(user_queue) > 0:
        return user_queue.pop(0), "user"
    if len(system_queue) == 0:
        system_queue = list(range(len(songs_data)))
        random.shuffle(system_queue)
    return system_queue.pop(0), "system"


def play_song(index, origin="system"):
    global current_song_idx, current_song_origin, current_bg, current_playback_time, is_playing
    if index < 0 or index >= len(songs_data): return

    current_song_idx = index
    current_song_origin = origin
    song = songs_data[index]

    # Update UI global palette specifically for this song!
    init_palette(song["color_pair"])

    pygame.mixer.music.load(song["path"])
    pygame.mixer.music.set_volume(song["vol"] if not is_muted else 0.0)
    pygame.mixer.music.play()

    current_playback_time = 0.0
    is_playing = True

    current_bg = Background(screen, native_w, native_h,
                            colorPair=song["color_pair"], scaleDownFactor=scaleDownFactorBG)


def toggle_play_pause():
    global is_playing
    if is_playing:
        pygame.mixer.music.pause()
    else:
        pygame.mixer.music.unpause()
    is_playing = not is_playing


def seek_to(percentage):
    global current_playback_time
    if current_song_idx == -1: return
    dur = songs_data[current_song_idx]["duration"]
    target = dur * percentage
    pygame.mixer.music.set_pos(target)
    current_playback_time = target


def micro_seek(seconds):
    global current_playback_time
    if current_song_idx == -1: return
    dur = songs_data[current_song_idx]["duration"]
    target = max(0.0, min(dur, current_playback_time + seconds))
    pygame.mixer.music.set_pos(target)
    current_playback_time = target


def play_next():
    global current_song_idx, current_song_origin, history_stack
    if current_song_idx != -1:
        history_stack.append((current_song_idx, current_song_origin))
    if is_repeat:
        play_song(current_song_idx, current_song_origin)
    else:
        next_idx, next_origin = get_next_song()
        play_song(next_idx, next_origin)


def play_prev():
    global current_song_idx, current_song_origin
    if current_playback_time > 2.0 or len(history_stack) == 0:
        seek_to(0.0)
    else:
        prev_idx, prev_origin = history_stack.pop()
        if current_song_origin == "user":
            user_queue.insert(0, current_song_idx)
        else:
            system_queue.insert(0, current_song_idx)
        play_song(prev_idx, prev_origin)


# ----------------- Main Loop -----------------
scroll_y = 0.0
target_scroll_y = 0.0

load_button = Button(
    x=screenWidthUI // 2, y=screenHeightUI // 2,
    w=560, h=140, r=24,
    text="LOAD SONGS", font=titleFont,
    col=ui_panel, border_col=ui_accent,
    text_col=ui_text, text_shadow_col=ui_bg
)

running = True
last_time = time.time()

while running:
    dt = time.time() - last_time
    last_time = time.time()

    if is_playing and current_song_idx != -1:
        current_playback_time += dt
        if current_playback_time >= songs_data[current_song_idx]["duration"]:
            play_next()

    mx, my = pygame.mouse.get_pos()
    scaled_mx, scaled_my = mx / scaleDownFactorUI, my / scaleDownFactorUI

    click = False
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1: click = True

            if current_state == AppState.PLAYER:
                if scaled_mx > screenWidthUI * 0.6:
                    if event.button == 4: target_scroll_y -= 50
                    if event.button == 5: target_scroll_y += 50

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE: running = False

            if current_state == AppState.PLAYER:
                if event.key in PLAY_KEYS:
                    toggle_play_pause()
                elif event.key in NEXT_KEYS:
                    play_next()
                elif event.key in PREV_KEYS:
                    play_prev()
                elif event.key == pygame.K_m:
                    is_muted = not is_muted
                    pygame.mixer.music.set_volume(0.0 if is_muted else songs_data[current_song_idx]["vol"])
                elif event.key == pygame.K_i:
                    incognitoToggle = not incognitoToggle
                elif event.key == pygame.K_j:
                    micro_seek(-10)
                elif event.key == pygame.K_l:
                    micro_seek(10)
                elif pygame.K_0 <= event.key <= pygame.K_9:
                    percentage = (event.key - pygame.K_0) / 10.0
                    seek_to(percentage)

    pygame.mouse.set_visible(False)
    # ---------------- Rendering States ----------------
    if current_state == AppState.MENU:
        screen.fill(ui_bg)
        screenUI.fill((0, 0, 0, 0))

        is_btn_hovered = load_button.rect.collidepoint((scaled_mx, scaled_my))
        load_button.col = brightness(ui_panel, 1.2) if is_btn_hovered else ui_panel
        load_button.draw(screenUI, scaled_mx, scaled_my, click)

        if load_button.update(scaled_mx, scaled_my, click):
            current_state = AppState.LOADING
            threading.Thread(target=load_songs_thread, daemon=True).start()

        pygame.draw.circle(screenUI, (215, 210, 220), (mx, my), 5, 2)
        screen.blit(pygame.transform.scale(screenUI, (native_w, native_h)), (0, 0))

    elif current_state == AppState.LOADING:
        screen.fill(ui_bg)
        screenUI.fill((0, 0, 0, 0))

        drawText(screenUI, ui_text, titleFont, screenWidthUI // 2, screenHeightUI // 2 - 20, "INITIALIZING ASSETS",
                 justify="center")
        drawText(screenUI, ui_text_dim, artistFont, screenWidthUI // 2, screenHeightUI // 2 + 20, loading_status,
                 justify="center")

        bar_w = 300
        pygame.draw.rect(screenUI, ui_panel, (screenWidthUI // 2 - bar_w // 2, screenHeightUI // 2 + 60, bar_w, 14),
                         border_radius=7)
        pygame.draw.rect(screenUI, ui_accent,
                         (screenWidthUI // 2 - bar_w // 2, screenHeightUI // 2 + 60, int(bar_w * loading_progress), 14),
                         border_radius=7)

        pygame.draw.circle(screenUI, (215, 210, 220), (mx, my), 5, 2)
        screen.blit(pygame.transform.scale(screenUI, (native_w, native_h)), (0, 0))

    elif current_state == AppState.PLAYER:
        # Failsafe: Ensures background Thread has completed the transition safely.
        if current_bg is None:
            continue

        current_bg.update(dt)
        current_bg.draw()

        screenUI.fill((0, 0, 0, 0))

        left_w = int(screenWidthUI * 0.6)
        center_x = left_w // 2

        if current_song_idx != -1:
            song = songs_data[current_song_idx]

            if incognitoToggle:
                # ==========================================
                #             INCOGNITO UI
                # ==========================================

                # Dim the background
                dim_surf = pygame.Surface((screenWidthUI, screenHeightUI), pygame.SRCALPHA)
                dim_surf.fill((0, 0, 0, 190))  # Heavy dimming overlay
                screenUI.blit(dim_surf, (0, 0))

                progress = current_playback_time / song["duration"] if song["duration"] > 0 else 0
                progress = max(0, min(progress, 1))

                # Large Centered Slider parameters
                slider_w = screenWidthUI * 0.7
                slider_padding = (screenWidthUI - slider_w) // 2
                slider_y = screenHeightUI // 2

                playerTimeFont = fonts["bold25"]

                # Draw Large Slider
                pygame.draw.rect(screenUI, ui_panel, (slider_padding, slider_y - 6, slider_w, 12), border_radius=6)
                fill_w = max(0, int(slider_w * progress))
                pygame.draw.rect(screenUI, ui_accent, (slider_padding, slider_y - 6, fill_w, 12), border_radius=6)
                pygame.draw.circle(screenUI, ui_text, (slider_padding + fill_w, slider_y), 16)

                # Interactive Seek Rect for Incognito
                slider_rect = pygame.Rect(slider_padding - 20, slider_y - 30, slider_w + 40, 60)
                if click and slider_rect.collidepoint(scaled_mx, scaled_my):
                    seek_perc = min(1.0, max(0.0, (scaled_mx - slider_padding) / slider_w))
                    seek_to(seek_perc)

                # Large Timestamps
                drawText(screenUI, ui_text_dim, playerTimeFont, slider_padding - 70, slider_y - 12,
                         format_time(current_playback_time))
                drawText(screenUI, ui_text_dim, playerTimeFont, slider_padding + slider_w + 20, slider_y - 12,
                         format_time(song["duration"]))

            else:
                # ==========================================
                #             STANDARD UI
                # ==========================================

                art_size = 400
                art_y = screenHeightUI // 2 - art_size // 2 - 40

                # Circular Ring + Progress
                ring_thickness = 16
                padding = -1
                art_center = (center_x, art_y + art_size // 2)

                base_radius = (art_size // 2) + padding
                inner_circle_radius = base_radius + ring_thickness
                outer_circle_radius = inner_circle_radius + ring_thickness

                # --- DRAW OUTER RING ---
                ring_surf = pygame.Surface((screenWidthBG, screenHeightBG), pygame.SRCALPHA)
                c_x_BG = (art_center[0] * scaleDownFactorUI) / scaleDownFactorBG
                c_y_BG = (art_center[1] * scaleDownFactorUI) / scaleDownFactorBG
                rad_BG = (outer_circle_radius * scaleDownFactorUI) / scaleDownFactorBG
                width_BG = max(1, int(ring_thickness * scaleDownFactorUI / scaleDownFactorBG))

                pygame.draw.circle(ring_surf, song["ring_color"],
                                   (int(c_x_BG), int(c_y_BG)),
                                   int(rad_BG),
                                   width=width_BG)

                screen.blit(pygame.transform.scale(ring_surf, (native_w, native_h)), (0, 0))

                # --- DRAW INNER RING TRACK ---
                pygame.draw.circle(screenUI, ui_panel, art_center, inner_circle_radius, ring_thickness)

                # --- DRAW PROGRESS ARC ---
                progress = current_playback_time / song["duration"] if song["duration"] > 0 else 0
                progress = max(0, min(progress, 1))
                end_angle = (math.pi / 2) - (progress * 2 * math.pi)

                arc_rect = (art_center[0] - base_radius,
                            art_center[1] - base_radius,
                            base_radius * 2,
                            base_radius * 2)

                for i in range(ring_thickness):
                    expanded_rect = (
                        arc_rect[0] - i,
                        arc_rect[1] - i,
                        arc_rect[2] + (i * 2),
                        arc_rect[3] + (i * 2)
                    )
                    pygame.draw.arc(
                        screenUI,
                        ui_accent,
                        expanded_rect,
                        end_angle,
                        math.pi / 2,
                        2
                    )

                # High Res Album Art
                screenUI.blit(song["art"], (center_x - art_size // 2, art_y))

                playerTitleFont = fonts["bold45"]
                playerArtistFont = fonts["bold25"]
                playerTimeFont = fonts["bold16"]

                # Timeline Slider parameters
                slider_y = screenHeightUI - 50
                slider_padding = 140
                slider_w = left_w - (slider_padding * 2)

                artist_y = slider_y - 50
                title_y = artist_y - 65

                t_title = truncate_text(playerTitleFont, song["title"], left_w - 60)
                t_artist = truncate_text(playerArtistFont, song["artist"], left_w - 60)

                drawText(screenUI, ui_text, playerTitleFont, center_x, title_y, t_title,
                         color2=brightness(ui_text, 0.2), shadowSize=4, justify="center")
                drawText(screenUI, ui_text_dim, playerArtistFont, center_x, artist_y, t_artist,
                         color2=brightness(ui_text_dim, 0.2), shadowSize=3, justify="center")

                # Draw Slider
                pygame.draw.rect(screenUI, ui_panel, (slider_padding, slider_y, slider_w, 6), border_radius=3)
                fill_w = max(0, int(slider_w * progress))
                pygame.draw.rect(screenUI, ui_accent, (slider_padding, slider_y, fill_w, 6), border_radius=3)
                pygame.draw.circle(screenUI, ui_text, (slider_padding + fill_w, slider_y + 3), 8)

                slider_rect = pygame.Rect(slider_padding - 20, slider_y - 15, slider_w + 40, 36)
                if click and slider_rect.collidepoint(scaled_mx, scaled_my):
                    seek_perc = min(1.0, max(0.0, (scaled_mx - slider_padding) / slider_w))
                    seek_to(seek_perc)

                # Timestamps
                drawText(screenUI, ui_text_dim, playerTimeFont, slider_padding - 55, slider_y - 7,
                         format_time(current_playback_time))
                drawText(screenUI, ui_text_dim, playerTimeFont, slider_padding + slider_w + 15, slider_y - 7,
                         format_time(song["duration"]))

                # ---- Top Left Info Hover ----
                info_rect = pygame.Rect(20, 20, 30, 30)
                pygame.draw.rect(screenUI, ui_panel, info_rect, border_radius=6)
                drawText(screenUI, ui_text, queueTitleFont, 35, 35, "?", justify="center", centeredVertically=True)
                if info_rect.collidepoint(scaled_mx, scaled_my):
                    card_rect = pygame.Rect(20, 60, 260, 188)  # Taller to fit new hotkey
                    pygame.draw.rect(screenUI, (*ui_bg, 240), card_rect, border_radius=8)
                    pygame.draw.rect(screenUI, ui_accent, card_rect, width=2, border_radius=8)

                    # Included 'I' inside hotkeys
                    hotkeys = ["Space / K : Play/Pause", "Arrows : Skip / Prev", "J / L : Seek -/+ 10s",
                               "0 - 9 : Seek %", "M : Mute", "I : Incognito Mode"]
                    for i, text in enumerate(hotkeys):
                        drawText(screenUI, ui_text_dim, queueArtistFont, 35, 75 + i * 28, text)

                # ---- Right Focus (The Queue) ----
                queue_x = left_w
                queue_w = screenWidthUI - left_w

                panel_surf = pygame.Surface((queue_w, screenHeightUI), pygame.SRCALPHA)
                panel_surf.fill((*ui_bg, 210))
                screenUI.blit(panel_surf, (queue_x, 0))

                render_list = []
                if len(user_queue) > 0:
                    render_list.append({"type": "header", "text": "User Queue"})
                    for idx in user_queue: render_list.append({"type": "song", "idx": idx})
                render_list.append({"type": "header", "text": "Up Next"})
                for idx in system_queue: render_list.append({"type": "song", "idx": idx})

                item_h = 60
                max_scroll = max(0.0, float(len(render_list) * item_h - screenHeightUI))

                if target_scroll_y < 0:
                    target_scroll_y += (0 - target_scroll_y) * 0.3
                elif target_scroll_y > max_scroll:
                    target_scroll_y += (max_scroll - target_scroll_y) * 0.3
                scroll_y += (target_scroll_y - scroll_y) * 0.15

                viewport = pygame.Surface((queue_w, screenHeightUI), pygame.SRCALPHA)

                start_idx = max(0, int(scroll_y // item_h))
                end_idx = min(len(render_list), start_idx + int(screenHeightUI // item_h) + 2)

                for i in range(start_idx, end_idx):
                    item = render_list[i]
                    y_pos = int(i * item_h - scroll_y)

                    if item["type"] == "header":
                        drawText(viewport, ui_text, queueTitleFont, 15, y_pos + 20, item["text"])
                        pygame.draw.line(viewport, ui_panel, (15, y_pos + 45), (queue_w - 20, y_pos + 45))

                    elif item["type"] == "song":
                        song_idx = item["idx"]
                        s = songs_data[song_idx]
                        row_rect = pygame.Rect(0, y_pos, queue_w, item_h)

                        is_hovered = False
                        rel_mx = scaled_mx - queue_x
                        if 0 <= rel_mx <= queue_w and row_rect.collidepoint(rel_mx, y_pos + item_h // 2):
                            is_hovered = True
                            pygame.draw.rect(viewport, brightness(ui_bg, 1.5), row_rect, border_radius=6)

                            plus_rect = pygame.Rect(queue_w - 50, y_pos + 15, 30, 30)
                            btn_hover = plus_rect.collidepoint(rel_mx, scaled_my)
                            pygame.draw.rect(viewport, ui_accent if btn_hover else ui_panel, plus_rect, border_radius=6)
                            drawText(viewport, ui_text, titleFont, plus_rect.centerx, plus_rect.centery - 2, "+",
                                     justify="center", centeredVertically=True)

                            if click and btn_hover:
                                if song_idx not in user_queue:
                                    user_queue.append(song_idx)
                                    if song_idx in system_queue:
                                        system_queue.remove(song_idx)

                        viewport.blit(s["thumb"], (15, y_pos + 10))
                        trunc_title = truncate_text(queueTitleFont, s["title"], queue_w - 120)
                        trunc_artist = truncate_text(queueArtistFont, s["artist"], queue_w - 120)
                        drawText(viewport, ui_text, queueTitleFont, 70, y_pos + 12, trunc_title)
                        drawText(viewport, ui_text_dim, queueArtistFont, 70, y_pos + 32, trunc_artist)

                screenUI.blit(viewport, (queue_x, 0))

        # Always draw the mouse and blit the screen (This replaces your broken `if incognitoToggle:`)
        pygame.draw.circle(screenUI, (215, 210, 220), (mx, my), 5, 2)
        screen.blit(pygame.transform.scale(screenUI, (native_w, native_h)), (0, 0))

    pygame.display.flip()
    clock.tick(fps)

pygame.quit()
