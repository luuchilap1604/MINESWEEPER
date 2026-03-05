"""
Minesweeper - Pygame Implementation
=====================================
Features:
  - Three difficulty presets: Easy (5x5), Medium (9x9), Hard (16x16)
  - Left-click to reveal a cell, right-click to toggle flag
  - DFS flood-fill to open blank (zero-neighbour) regions
  - Mine counter, elapsed-time timer, smiley reset button
  - Win / Lose detection with full board reveal
  - Image-based assets with colorful procedural fallbacks
"""

import sys
import os
import math
import array
import random
import time
import pygame

# ============================== constants ==============================

CELL_SIZE = 40
HEADER_HEIGHT = 60
BORDER = 12
IMAGE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images")
SOUND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sounds")

# Modern colour palette
COL_BG           = (45, 52, 64)       # dark slate background
COL_BORDER_LT    = (136, 192, 208)    # frost blue highlight
COL_BORDER_DK    = (59, 66, 82)       # dark border
COL_REVEALED     = (216, 222, 233)    # light revealed cell
COL_GRID_LINE    = (76, 86, 106)      # subtle grid
COL_MINE         = (46, 52, 64)       # mine body colour
COL_FLAG_RED     = (191, 97, 106)     # nord red
COL_FLAG_POLE    = (76, 86, 106)      # pole grey
COL_EXPLODED     = (191, 97, 106)     # red exploded bg
COL_COUNTER_BG   = (36, 40, 50)       # dark counter bg
COL_COUNTER_FG   = (163, 190, 140)    # green counter text
COL_HEADER_BG    = (59, 66, 82)       # header bar
COL_BUTTON_FACE  = (76, 86, 106)      # button face
COL_CELL_UNREV   = (94, 129, 172)     # blue unrevealed cell

# Vibrant number colours
NUMBER_COLOURS = {
    1: (94, 129, 172),     # blue
    2: (163, 190, 140),    # green
    3: (191, 97, 106),     # red
    4: (180, 142, 173),    # purple
    5: (208, 135, 112),    # orange
    6: (136, 192, 208),    # cyan
    7: (229, 233, 240),    # white
    8: (76, 86, 106),      # grey
}

# Menu colours
COL_MENU_BG_TOP    = (46, 52, 64)
COL_MENU_BG_BOT    = (59, 66, 82)
COL_MENU_TITLE     = (136, 192, 208)
COL_MENU_SUBTITLE  = (216, 222, 233)
COL_MENU_BTN       = (76, 86, 106)
COL_MENU_BTN_HOVER = (94, 129, 172)
COL_MENU_BTN_TEXT  = (229, 233, 240)
COL_MENU_DETAIL    = (143, 150, 163)

# Difficulty presets: (rows, cols, mines)
DIFFICULTIES = {
    "Easy (5x5)":    (5, 5, 4),
    "Medium (9x9)":  (9, 9, 10),
    "Hard (16x16)":  (16, 16, 40),
}


# ============================== asset loader ==============================

class Assets:
    """
    Tries to load image files from the images/ folder.
    If an image is missing, generates a colourful placeholder surface.

    Expected image files (all CELL_SIZE x CELL_SIZE unless noted):
      images/cell_unrevealed.png   - hidden cell
      images/cell_revealed.png     - opened cell background
      images/mine.png              - mine icon
      images/flag.png              - flag icon
      images/exploded.png          - exploded mine cell background
      images/num_1.png ... num_8.png - number overlays
      images/face_normal.png       - 36x36 normal smiley
      images/face_win.png          - 36x36 win smiley
      images/face_lose.png         - 36x36 lose smiley
      images/wrong_flag.png        - wrong flag overlay
      images/logo.png              - menu title image (optional)
    """

    def __init__(self, cell_size: int = CELL_SIZE):
        self.cs = cell_size
        self.cell_unrevealed = self._load("cell_unrevealed.png", (cell_size, cell_size)) \
                               or self._gen_cell_unrevealed()
        self.cell_revealed   = self._load("cell_revealed.png", (cell_size, cell_size)) \
                               or self._gen_cell_revealed()
        self.mine            = self._load("mine.png", (cell_size, cell_size)) \
                               or self._gen_mine()
        self.flag            = self._load("flag.png", (cell_size, cell_size)) \
                               or self._gen_flag()
        self.exploded        = self._load("exploded.png", (cell_size, cell_size)) \
                               or self._gen_exploded()
        self.wrong_flag      = self._load("wrong_flag.png", (cell_size, cell_size)) \
                               or self._gen_wrong_flag()

        self.numbers = {}
        for n in range(1, 9):
            img = self._load(f"num_{n}.png", (cell_size, cell_size))
            self.numbers[n] = img or self._gen_number(n)

        self.face_normal = self._load("face_normal.png", (36, 36)) \
                           or self._gen_face("normal")
        self.face_win    = self._load("face_win.png", (36, 36)) \
                           or self._gen_face("win")
        self.face_lose   = self._load("face_lose.png", (36, 36)) \
                           or self._gen_face("lose")

        self.logo = self._load("logo.png", None)  # optional, no fallback size

    # -- loader --

    @staticmethod
    def _load(filename: str, size: tuple[int, int] | None) -> pygame.Surface | None:
        path = os.path.join(IMAGE_DIR, filename)
        if not os.path.isfile(path):
            return None
        try:
            img = pygame.image.load(path).convert_alpha()
            if size:
                img = pygame.transform.smoothscale(img, size)
            return img
        except pygame.error:
            return None

    # -- placeholder generators --

    def _gradient_rect(self, w: int, h: int, top_col, bot_col) -> pygame.Surface:
        """Vertical linear gradient."""
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        for y in range(h):
            t = y / max(h - 1, 1)
            r = int(top_col[0] + (bot_col[0] - top_col[0]) * t)
            g = int(top_col[1] + (bot_col[1] - top_col[1]) * t)
            b = int(top_col[2] + (bot_col[2] - top_col[2]) * t)
            pygame.draw.line(surf, (r, g, b), (0, y), (w - 1, y))
        return surf

    def _gen_cell_unrevealed(self) -> pygame.Surface:
        cs = self.cs
        surf = self._gradient_rect(cs, cs, (94, 129, 172), (76, 106, 150))
        # raised edges
        pygame.draw.line(surf, (136, 192, 208), (0, 0), (cs - 1, 0), 2)
        pygame.draw.line(surf, (136, 192, 208), (0, 0), (0, cs - 1), 2)
        pygame.draw.line(surf, (59, 66, 82), (0, cs - 1), (cs - 1, cs - 1), 2)
        pygame.draw.line(surf, (59, 66, 82), (cs - 1, 0), (cs - 1, cs - 1), 2)
        # subtle inner highlight
        pygame.draw.rect(surf, (110, 145, 185), (3, 3, cs - 6, cs - 6), 1)
        return surf

    def _gen_cell_revealed(self) -> pygame.Surface:
        cs = self.cs
        surf = self._gradient_rect(cs, cs, (216, 222, 233), (200, 208, 220))
        pygame.draw.rect(surf, (180, 188, 200), (0, 0, cs, cs), 1)
        return surf

    def _gen_mine(self) -> pygame.Surface:
        cs = self.cs
        surf = pygame.Surface((cs, cs), pygame.SRCALPHA)
        cx, cy = cs // 2, cs // 2
        r = cs // 5
        # body
        pygame.draw.circle(surf, (46, 52, 64), (cx, cy), r)
        # outer glow
        pygame.draw.circle(surf, (60, 68, 82), (cx, cy), r + 2, 2)
        # spikes
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1),
                        (-1, -1), (1, 1), (-1, 1), (1, -1)]:
            sx = cx + int(dx * r * 1.6)
            sy = cy + int(dy * r * 1.6)
            pygame.draw.line(surf, (46, 52, 64), (cx, cy), (sx, sy), 2)
        # glint
        pygame.draw.circle(surf, (229, 233, 240),
                           (cx - r // 3, cy - r // 3), r // 4)
        return surf

    def _gen_flag(self) -> pygame.Surface:
        cs = self.cs
        surf = pygame.Surface((cs, cs), pygame.SRCALPHA)
        cx, cy = cs // 2, cs // 2
        # pole
        pygame.draw.line(surf, (76, 86, 106),
                         (cx, cy - cs // 4), (cx, cy + cs // 4), 2)
        # flag triangle
        pts = [(cx, cy - cs // 4),
               (cx - cs // 4, cy - cs // 8),
               (cx, cy)]
        pygame.draw.polygon(surf, (191, 97, 106), pts)
        pygame.draw.polygon(surf, (210, 120, 128), pts, 1)
        # base
        pygame.draw.line(surf, (76, 86, 106),
                         (cx - cs // 5, cy + cs // 4),
                         (cx + cs // 5, cy + cs // 4), 2)
        return surf

    def _gen_exploded(self) -> pygame.Surface:
        cs = self.cs
        surf = self._gradient_rect(cs, cs, (220, 80, 80), (180, 50, 50))
        pygame.draw.rect(surf, (240, 100, 100), (0, 0, cs, cs), 1)
        return surf

    def _gen_wrong_flag(self) -> pygame.Surface:
        cs = self.cs
        surf = pygame.Surface((cs, cs), pygame.SRCALPHA)
        # X mark
        pygame.draw.line(surf, (220, 50, 50), (6, 6), (cs - 6, cs - 6), 3)
        pygame.draw.line(surf, (220, 50, 50), (cs - 6, 6), (6, cs - 6), 3)
        return surf

    def _gen_number(self, n: int) -> pygame.Surface:
        cs = self.cs
        surf = pygame.Surface((cs, cs), pygame.SRCALPHA)
        font = pygame.font.SysFont("Arial", cs * 3 // 5, bold=True)
        col = NUMBER_COLOURS.get(n, (229, 233, 240))
        txt = font.render(str(n), True, col)
        # slight shadow
        shadow = font.render(str(n), True, (30, 30, 40))
        surf.blit(shadow, shadow.get_rect(center=(cs // 2 + 1, cs // 2 + 1)))
        surf.blit(txt, txt.get_rect(center=(cs // 2, cs // 2)))
        return surf

    def _gen_face(self, mode: str) -> pygame.Surface:
        sz = 36
        surf = pygame.Surface((sz, sz), pygame.SRCALPHA)
        cx, cy = sz // 2, sz // 2
        # face circle
        if mode == "win":
            face_col = (163, 190, 140)   # green
        elif mode == "lose":
            face_col = (191, 97, 106)    # red
        else:
            face_col = (235, 203, 139)   # warm yellow
        pygame.draw.circle(surf, face_col, (cx, cy), sz // 2 - 2)
        pygame.draw.circle(surf, (46, 52, 64), (cx, cy), sz // 2 - 2, 2)
        # eyes
        pygame.draw.circle(surf, (46, 52, 64), (cx - 5, cy - 4), 2)
        pygame.draw.circle(surf, (46, 52, 64), (cx + 5, cy - 4), 2)
        # mouth
        if mode == "win":
            pygame.draw.arc(surf, (46, 52, 64),
                            (cx - 7, cy - 2, 14, 12), 3.14, 6.28, 2)
        elif mode == "lose":
            pygame.draw.arc(surf, (46, 52, 64),
                            (cx - 7, cy + 4, 14, 8), 0, 3.14, 2)
            # X eyes
            for ex in (cx - 5, cx + 5):
                pygame.draw.line(surf, (46, 52, 64),
                                 (ex - 2, cy - 6), (ex + 2, cy - 2), 2)
                pygame.draw.line(surf, (46, 52, 64),
                                 (ex + 2, cy - 6), (ex - 2, cy - 2), 2)
        else:
            pygame.draw.arc(surf, (46, 52, 64),
                            (cx - 6, cy, 12, 8), 3.14, 6.28, 2)
        return surf


# ============================== sound effects ==============================

class SoundFX:
    """
    Tries to load WAV files from the sounds/ folder.
    If a file is missing, synthesises a short sound procedurally.

    Expected sound files (all WAV, mono, 44100 Hz):
      sounds/click.wav       - cell reveal
      sounds/flag.wav        - flag toggle
      sounds/explode.wav     - mine hit
      sounds/win.wav         - victory
      sounds/flood.wav       - flood fill (blank region)
      sounds/menu_click.wav  - menu button
    """

    SAMPLE_RATE = 44100

    def __init__(self):
        try:
            pygame.mixer.init(frequency=self.SAMPLE_RATE, size=-16, channels=1, buffer=512)
        except pygame.error:
            pass
        self.click      = self._load("click.wav")      or self._gen_click()
        self.flag        = self._load("flag.wav")       or self._gen_flag()
        self.explode     = self._load("explode.wav")    or self._gen_explode()
        self.win         = self._load("win.wav")        or self._gen_win()
        self.flood       = self._load("flood.wav")      or self._gen_flood()
        self.menu_click  = self._load("menu_click.wav") or self._gen_menu_click()

    @staticmethod
    def _load(filename: str) -> pygame.mixer.Sound | None:
        path = os.path.join(SOUND_DIR, filename)
        if not os.path.isfile(path):
            return None
        try:
            return pygame.mixer.Sound(path)
        except pygame.error:
            return None

    # -- synthesis helpers --

    @classmethod
    def _make_sound(cls, samples: list[int]) -> pygame.mixer.Sound:
        """Create a Sound from a list of 16-bit signed samples."""
        buf = array.array("h", samples)
        return pygame.mixer.Sound(buffer=buf)

    @classmethod
    def _tone(cls, freq: float, duration: float, volume: float = 0.3,
              fade_out: float = 0.5) -> list[int]:
        """Generate a sine-wave tone with linear fade-out."""
        n = int(cls.SAMPLE_RATE * duration)
        samples = []
        for i in range(n):
            t = i / cls.SAMPLE_RATE
            env = max(0.0, 1.0 - (i / n) * (1.0 / max(fade_out, 0.01)))
            val = math.sin(2.0 * math.pi * freq * t) * volume * env
            samples.append(int(val * 32767))
        return samples

    @classmethod
    def _noise(cls, duration: float, volume: float = 0.15,
               fade_out: float = 0.8) -> list[int]:
        """Generate white noise with fade-out."""
        n = int(cls.SAMPLE_RATE * duration)
        samples = []
        for i in range(n):
            env = max(0.0, 1.0 - (i / n) * (1.0 / max(fade_out, 0.01)))
            val = (random.random() * 2 - 1) * volume * env
            samples.append(int(val * 32767))
        return samples

    # -- individual sound generators --

    @classmethod
    def _gen_click(cls) -> pygame.mixer.Sound:
        """Short pop/click for cell reveal."""
        s = cls._tone(800, 0.06, volume=0.25, fade_out=0.9)
        s += cls._tone(600, 0.03, volume=0.15, fade_out=0.9)
        return cls._make_sound(s)

    @classmethod
    def _gen_flag(cls) -> pygame.mixer.Sound:
        """Two-tone blip for flag toggle."""
        s = cls._tone(523, 0.05, volume=0.2, fade_out=0.8)
        s += cls._tone(659, 0.07, volume=0.25, fade_out=0.8)
        return cls._make_sound(s)

    @classmethod
    def _gen_explode(cls) -> pygame.mixer.Sound:
        """Low boom + noise for mine hit."""
        boom = cls._tone(80, 0.3, volume=0.5, fade_out=0.7)
        noise = cls._noise(0.4, volume=0.3, fade_out=0.6)
        # mix boom and noise (pad shorter to match)
        length = max(len(boom), len(noise))
        boom += [0] * (length - len(boom))
        noise += [0] * (length - len(noise))
        mixed = [max(-32767, min(32767, boom[i] + noise[i])) for i in range(length)]
        return cls._make_sound(mixed)

    @classmethod
    def _gen_win(cls) -> pygame.mixer.Sound:
        """Ascending arpeggio for victory."""
        notes = [523, 659, 784, 1047]  # C5, E5, G5, C6
        s: list[int] = []
        for freq in notes:
            s += cls._tone(freq, 0.12, volume=0.25, fade_out=0.6)
        # final sustain
        s += cls._tone(1047, 0.25, volume=0.3, fade_out=0.4)
        return cls._make_sound(s)

    @classmethod
    def _gen_flood(cls) -> pygame.mixer.Sound:
        """Soft swoosh for flood-fill reveal."""
        n = int(cls.SAMPLE_RATE * 0.15)
        samples = []
        for i in range(n):
            t = i / cls.SAMPLE_RATE
            freq = 400 + 600 * (i / n)  # rising sweep
            env = math.sin(math.pi * i / n) * 0.2  # bell envelope
            val = math.sin(2.0 * math.pi * freq * t) * env
            samples.append(int(val * 32767))
        return cls._make_sound(samples)

    @classmethod
    def _gen_menu_click(cls) -> pygame.mixer.Sound:
        """Crisp click for menu interaction."""
        s = cls._tone(1000, 0.04, volume=0.2, fade_out=0.9)
        return cls._make_sound(s)

    # -- play helpers (safe to call even if mixer failed) --

    @staticmethod
    def play(sound: pygame.mixer.Sound | None):
        """Play a sound if it exists and mixer is available."""
        if sound is None:
            return
        try:
            sound.play()
        except pygame.error:
            pass


# ============================== board logic ==============================

class Board:
    """Pure game-logic layer - no rendering."""

    def __init__(self, rows: int, cols: int, num_mines: int):
        self.rows = rows
        self.cols = cols
        self.num_mines = num_mines

        # Matrices
        self.mines     = [[False] * cols for _ in range(rows)]
        self.revealed  = [[False] * cols for _ in range(rows)]
        self.flagged   = [[False] * cols for _ in range(rows)]
        self.neighbour = [[0] * cols for _ in range(rows)]

        self.first_click = True
        self.game_over   = False
        self.won         = False
        self.flags_placed = 0

    # -- mine placement (deferred until first click) --

    def _place_mines(self, safe_r: int, safe_c: int):
        """Place mines randomly, keeping a 3x3 safe zone around first click."""
        safe = set()
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                nr, nc = safe_r + dr, safe_c + dc
                if 0 <= nr < self.rows and 0 <= nc < self.cols:
                    safe.add((nr, nc))

        candidates = [
            (r, c)
            for r in range(self.rows)
            for c in range(self.cols)
            if (r, c) not in safe
        ]
        # If there are fewer candidates than mines needed, allow safe zone cells
        if len(candidates) < self.num_mines:
            candidates = [
                (r, c)
                for r in range(self.rows)
                for c in range(self.cols)
                if (r, c) != (safe_r, safe_c)
            ]

        chosen = random.sample(candidates, min(self.num_mines, len(candidates)))
        for r, c in chosen:
            self.mines[r][c] = True

        # pre-compute neighbour counts
        for r in range(self.rows):
            for c in range(self.cols):
                if self.mines[r][c]:
                    self.neighbour[r][c] = -1
                    continue
                count = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < self.rows and 0 <= nc < self.cols and self.mines[nr][nc]:
                            count += 1
                self.neighbour[r][c] = count

    # -- DFS flood-fill --

    def _dfs_reveal(self, r: int, c: int):
        """Depth-First Search to reveal contiguous blank cells."""
        stack = [(r, c)]
        while stack:
            cr, cc = stack.pop()
            if self.revealed[cr][cc]:
                continue
            if self.flagged[cr][cc]:
                continue
            self.revealed[cr][cc] = True
            if self.neighbour[cr][cc] == 0:
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        nr, nc = cr + dr, cc + dc
                        if 0 <= nr < self.rows and 0 <= nc < self.cols:
                            if not self.revealed[nr][nc] and not self.mines[nr][nc]:
                                stack.append((nr, nc))

    # -- public actions --

    def reveal(self, r: int, c: int):
        """Left-click action. Returns True if the game continues."""
        if self.game_over or self.won:
            return False
        if self.flagged[r][c] or self.revealed[r][c]:
            return True

        if self.first_click:
            self._place_mines(r, c)
            self.first_click = False

        if self.mines[r][c]:
            self.revealed[r][c] = True
            self.game_over = True
            return False

        self._dfs_reveal(r, c)
        self._check_win()
        return True

    def toggle_flag(self, r: int, c: int):
        """Right-click action."""
        if self.game_over or self.won:
            return
        if self.revealed[r][c]:
            return
        self.flagged[r][c] = not self.flagged[r][c]
        self.flags_placed += 1 if self.flagged[r][c] else -1

    def chord(self, r: int, c: int):
        """Middle-click / double-click on revealed numbered cell.
        If the number of surrounding flags equals the cell number,
        reveal all non-flagged neighbours."""
        if self.game_over or self.won:
            return
        if not self.revealed[r][c]:
            return
        n = self.neighbour[r][c]
        if n <= 0:
            return
        flag_count = 0
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = r + dr, c + dc
                if 0 <= nr < self.rows and 0 <= nc < self.cols and self.flagged[nr][nc]:
                    flag_count += 1
        if flag_count == n:
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < self.rows and 0 <= nc < self.cols:
                        if not self.flagged[nr][nc] and not self.revealed[nr][nc]:
                            self.reveal(nr, nc)

    def _check_win(self):
        for r in range(self.rows):
            for c in range(self.cols):
                if not self.mines[r][c] and not self.revealed[r][c]:
                    return
        self.won = True

    def remaining_mines(self) -> int:
        return self.num_mines - self.flags_placed


# ============================== renderer ==============================

class Renderer:
    """Handles all Pygame drawing using image assets."""

    def __init__(self, surface: pygame.Surface, board: Board,
                 offset_x: int, offset_y: int, assets: Assets,
                 cell_size: int = CELL_SIZE):
        self.surface = surface
        self.board = board
        self.ox = offset_x
        self.oy = offset_y
        self.cell = cell_size
        self.assets = assets
        self.counter_font = pygame.font.SysFont("Consolas", 28, bold=True)
        self.msg_font = pygame.font.SysFont("Arial", 20, bold=True)

    # -- helper --

    def _rect_for(self, r: int, c: int) -> pygame.Rect:
        return pygame.Rect(self.ox + c * self.cell,
                           self.oy + r * self.cell,
                           self.cell, self.cell)

    # -- main draw --

    def draw_board(self):
        b = self.board
        a = self.assets
        for r in range(b.rows):
            for c in range(b.cols):
                rect = self._rect_for(r, c)
                if b.revealed[r][c]:
                    # opened cell background
                    self.surface.blit(a.cell_revealed, rect.topleft)
                    if b.mines[r][c]:
                        # exploded mine
                        self.surface.blit(a.exploded, rect.topleft)
                        self.surface.blit(a.mine, rect.topleft)
                    elif b.neighbour[r][c] > 0:
                        self.surface.blit(a.numbers[b.neighbour[r][c]], rect.topleft)
                else:
                    # unrevealed
                    if b.game_over:
                        if b.mines[r][c] and not b.flagged[r][c]:
                            self.surface.blit(a.cell_revealed, rect.topleft)
                            self.surface.blit(a.mine, rect.topleft)
                        elif b.flagged[r][c] and not b.mines[r][c]:
                            self.surface.blit(a.cell_revealed, rect.topleft)
                            self.surface.blit(a.flag, rect.topleft)
                            self.surface.blit(a.wrong_flag, rect.topleft)
                        elif b.flagged[r][c] and b.mines[r][c]:
                            self.surface.blit(a.cell_unrevealed, rect.topleft)
                            self.surface.blit(a.flag, rect.topleft)
                        else:
                            self.surface.blit(a.cell_unrevealed, rect.topleft)
                    else:
                        self.surface.blit(a.cell_unrevealed, rect.topleft)
                        if b.flagged[r][c]:
                            self.surface.blit(a.flag, rect.topleft)

    def draw_header(self, remaining: int, elapsed: int,
                    smiley_rect: pygame.Rect, game_over: bool, won: bool):
        # header background with subtle gradient
        hdr_w = self.surface.get_width()
        for y in range(HEADER_HEIGHT):
            t = y / max(HEADER_HEIGHT - 1, 1)
            r = int(59 + (46 - 59) * t)
            g = int(66 + (52 - 66) * t)
            b = int(82 + (64 - 82) * t)
            pygame.draw.line(self.surface, (r, g, b), (0, y), (hdr_w - 1, y))

        # mine counter (left) - rounded rectangle
        counter_text = f"{remaining:03d}"
        ctr_bg = pygame.Rect(BORDER, (HEADER_HEIGHT - 34) // 2, 68, 34)
        pygame.draw.rect(self.surface, COL_COUNTER_BG, ctr_bg, border_radius=5)
        pygame.draw.rect(self.surface, (94, 129, 172), ctr_bg, 1, border_radius=5)
        ctr_surf = self.counter_font.render(counter_text, True, COL_COUNTER_FG)
        self.surface.blit(ctr_surf, ctr_surf.get_rect(center=ctr_bg.center))

        # timer (right) - rounded rectangle
        time_text = f"{min(elapsed, 999):03d}"
        tm_bg = pygame.Rect(hdr_w - BORDER - 68,
                            (HEADER_HEIGHT - 34) // 2, 68, 34)
        pygame.draw.rect(self.surface, COL_COUNTER_BG, tm_bg, border_radius=5)
        pygame.draw.rect(self.surface, (94, 129, 172), tm_bg, 1, border_radius=5)
        tm_surf = self.counter_font.render(time_text, True, COL_COUNTER_FG)
        self.surface.blit(tm_surf, tm_surf.get_rect(center=tm_bg.center))

        # smiley button (centre)
        pygame.draw.rect(self.surface, COL_BUTTON_FACE, smiley_rect,
                         border_radius=8)
        pygame.draw.rect(self.surface, (136, 192, 208), smiley_rect, 2,
                         border_radius=8)
        if won:
            face_img = self.assets.face_win
        elif game_over:
            face_img = self.assets.face_lose
        else:
            face_img = self.assets.face_normal
        self.surface.blit(face_img,
                          face_img.get_rect(center=smiley_rect.center))

    def draw_buttons(self, restart_rect: pygame.Rect, menu_rect: pygame.Rect):
        """Draw Restart and Menu buttons in the header area."""
        btn_font = pygame.font.SysFont("Arial", 13, bold=True)
        mx, my = pygame.mouse.get_pos()
        for rect, label in [(restart_rect, "Restart"), (menu_rect, "Menu")]:
            hovered = rect.collidepoint(mx, my)
            col = (94, 129, 172) if hovered else (76, 86, 106)
            pygame.draw.rect(self.surface, col, rect, border_radius=6)
            border_col = (136, 192, 208) if hovered else (94, 129, 172)
            pygame.draw.rect(self.surface, border_col, rect, 1, border_radius=6)
            lbl = btn_font.render(label, True, (229, 233, 240))
            self.surface.blit(lbl, lbl.get_rect(center=rect.center))


# ============================== helpers ==============================

def _draw_gradient_bg(surface: pygame.Surface, top_col, bot_col):
    """Fill the whole surface with a vertical gradient."""
    w, h = surface.get_size()
    for y in range(h):
        t = y / max(h - 1, 1)
        r = int(top_col[0] + (bot_col[0] - top_col[0]) * t)
        g = int(top_col[1] + (bot_col[1] - top_col[1]) * t)
        b = int(top_col[2] + (bot_col[2] - top_col[2]) * t)
        pygame.draw.line(surface, (r, g, b), (0, y), (w - 1, y))


def confirm_dialog(screen: pygame.Surface, message: str,
                   sfx: "SoundFX | None" = None) -> bool:
    """Show a modal confirmation dialog. Returns True if user confirms."""
    overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 140))

    dlg_w, dlg_h = 340, 160
    sw, sh = screen.get_size()
    dlg_x = (sw - dlg_w) // 2
    dlg_y = (sh - dlg_h) // 2
    dlg_rect = pygame.Rect(dlg_x, dlg_y, dlg_w, dlg_h)

    title_font = pygame.font.SysFont("Arial", 20, bold=True)
    btn_font = pygame.font.SysFont("Arial", 18, bold=True)

    yes_rect = pygame.Rect(dlg_x + 40, dlg_y + dlg_h - 54, 110, 38)
    no_rect = pygame.Rect(dlg_x + dlg_w - 150, dlg_y + dlg_h - 54, 110, 38)

    clock = pygame.time.Clock()
    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return False
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_y:
                    return True
                if ev.key in (pygame.K_n, pygame.K_ESCAPE):
                    return False
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if yes_rect.collidepoint(ev.pos):
                    if sfx:
                        SoundFX.play(sfx.menu_click)
                    return True
                if no_rect.collidepoint(ev.pos):
                    if sfx:
                        SoundFX.play(sfx.menu_click)
                    return False

        # Draw the existing screen content underneath
        screen.blit(overlay, (0, 0))

        # Dialog box
        pygame.draw.rect(screen, (46, 52, 64), dlg_rect, border_radius=12)
        pygame.draw.rect(screen, (136, 192, 208), dlg_rect, 2, border_radius=12)

        # Message
        msg_surf = title_font.render(message, True, (229, 233, 240))
        screen.blit(msg_surf, msg_surf.get_rect(centerx=sw // 2,
                                                 y=dlg_y + 28))

        # Subtitle
        sub_font = pygame.font.SysFont("Arial", 14)
        sub_surf = sub_font.render("(Y to confirm, N / Esc to cancel)", True,
                                   (143, 150, 163))
        screen.blit(sub_surf, sub_surf.get_rect(centerx=sw // 2,
                                                 y=dlg_y + 58))

        # Buttons
        mx, my = pygame.mouse.get_pos()
        for rect, label, base_col, hover_col in [
            (yes_rect, "Yes", (163, 190, 140), (183, 210, 160)),
            (no_rect, "No", (191, 97, 106), (211, 117, 126)),
        ]:
            hovered = rect.collidepoint(mx, my)
            col = hover_col if hovered else base_col
            pygame.draw.rect(screen, col, rect, border_radius=8)
            pygame.draw.rect(screen, (229, 233, 240), rect, 1, border_radius=8)
            lbl = btn_font.render(label, True, (46, 52, 64))
            screen.blit(lbl, lbl.get_rect(center=rect.center))

        pygame.display.flip()
        clock.tick(30)


# ============================== menu screen ==============================

def difficulty_menu(screen: pygame.Surface, assets: Assets,
                    sfx: SoundFX | None = None) -> tuple[int, int, int] | None:
    """Stylish difficulty selection screen. Returns (rows, cols, mines) or None."""
    menu_w, menu_h = 400, 440
    screen = pygame.display.set_mode((menu_w, menu_h))
    pygame.display.set_caption("Minesweeper - Select Difficulty")

    title_font = pygame.font.SysFont("Arial", 36, bold=True)
    btn_font   = pygame.font.SysFont("Arial", 22, bold=True)
    small_font = pygame.font.SysFont("Arial", 15)

    diff_colours = [
        (163, 190, 140),  # green for Easy
        (235, 203, 139),  # yellow for Medium
        (191, 97, 106),   # red for Hard
    ]

    buttons: list[tuple[pygame.Rect, str, tuple[int, int, int], tuple[int, int, int]]] = []
    y = 140
    for i, (name, (rows, cols, mines)) in enumerate(DIFFICULTIES.items()):
        rect = pygame.Rect((menu_w - 280) // 2, y, 280, 52)
        buttons.append((rect, name, (rows, cols, mines), diff_colours[i]))
        y += 74

    clock = pygame.time.Clock()

    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return None
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                for rect, _, params, _ in buttons:
                    if rect.collidepoint(ev.pos):
                        if sfx:
                            SoundFX.play(sfx.menu_click)
                        return params

        # gradient background
        _draw_gradient_bg(screen, COL_MENU_BG_TOP, COL_MENU_BG_BOT)

        # decorative top bar
        pygame.draw.rect(screen, (136, 192, 208), (0, 0, menu_w, 4))

        # logo or title
        if assets.logo:
            logo_rect = assets.logo.get_rect(centerx=menu_w // 2, y=20)
            screen.blit(assets.logo, logo_rect)
        else:
            title = title_font.render("MINESWEEPER", True, COL_MENU_TITLE)
            screen.blit(title, title.get_rect(centerx=menu_w // 2, y=28))
            # underline accent
            tw = title.get_width()
            pygame.draw.rect(screen, (163, 190, 140),
                             (menu_w // 2 - tw // 2, 72, tw, 3),
                             border_radius=2)

        sub = small_font.render("Select difficulty to begin", True, COL_MENU_SUBTITLE)
        screen.blit(sub, sub.get_rect(centerx=menu_w // 2, y=88))

        # buttons
        mx, my = pygame.mouse.get_pos()
        for rect, name, (rows, cols, mines), dot_col in buttons:
            hovered = rect.collidepoint(mx, my)
            col = COL_MENU_BTN_HOVER if hovered else COL_MENU_BTN
            # button shadow
            shadow_rect = rect.move(3, 3)
            pygame.draw.rect(screen, (30, 34, 42), shadow_rect, border_radius=10)
            # button body
            pygame.draw.rect(screen, col, rect, border_radius=10)
            border_col = (136, 192, 208) if hovered else (94, 129, 172)
            pygame.draw.rect(screen, border_col, rect, 2, border_radius=10)

            # coloured dot + label
            pygame.draw.circle(screen, dot_col, (rect.x + 20, rect.centery), 6)
            label = btn_font.render(name, True, COL_MENU_BTN_TEXT)
            screen.blit(label,
                        label.get_rect(centerx=rect.centerx + 8,
                                       centery=rect.centery))

            # detail text below each button
            detail = small_font.render(
                f"{rows}x{cols} grid  |  {mines} mines", True, COL_MENU_DETAIL)
            screen.blit(detail,
                        detail.get_rect(centerx=rect.centerx,
                                        top=rect.bottom + 6))

        # bottom credits line
        cred = small_font.render("BTL AI  |  DFS Minesweeper", True, (76, 86, 106))
        screen.blit(cred, cred.get_rect(centerx=menu_w // 2, y=menu_h - 28))

        pygame.display.flip()
        clock.tick(30)


# ============================== main game loop ==============================

def game_loop(rows: int, cols: int, num_mines: int, assets: Assets,
              sfx: SoundFX | None = None) -> bool:
    """Run one game. Returns True to restart, False to quit, 'menu' for menu."""
    board = Board(rows, cols, num_mines)
    end_sound_played = False

    # Fixed window size (always matches Hard 16x16)
    ref_rows, ref_cols = 16, 16
    board_w = ref_cols * CELL_SIZE
    board_h = ref_rows * CELL_SIZE
    win_w = 2 * BORDER + board_w
    win_h = HEADER_HEIGHT + BORDER + board_h + BORDER

    # Effective cell size: scale tiles up for smaller boards
    cell_eff = min(board_w // cols, board_h // rows)
    actual_w = cols * cell_eff
    actual_h = rows * cell_eff

    # Centre the board in the fixed area
    offset_x = BORDER + (board_w - actual_w) // 2
    offset_y = HEADER_HEIGHT + BORDER + (board_h - actual_h) // 2

    # Build assets at the effective cell size
    game_assets = Assets(cell_size=cell_eff)

    screen = pygame.display.set_mode((win_w, win_h))
    pygame.display.set_caption("Minesweeper")

    renderer = Renderer(screen, board, offset_x, offset_y, game_assets,
                        cell_size=cell_eff)

    smiley_rect = pygame.Rect((win_w - 36) // 2,
                               (HEADER_HEIGHT - 36) // 2, 36, 36)

    # Restart / Menu buttons (right of timer)
    btn_w, btn_h = 58, 26
    btn_y = (HEADER_HEIGHT - btn_h) // 2
    # Place after the timer: timer ends at (win_w - BORDER), put buttons just left of timer
    restart_rect = pygame.Rect(BORDER + 76, btn_y, btn_w, btn_h)
    menu_rect    = pygame.Rect(BORDER + 76 + btn_w + 6, btn_y, btn_w, btn_h)

    clock = pygame.time.Clock()
    start_time: float | None = None
    elapsed = 0

    running = True
    while running:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return False

            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_r:
                    # If game is still ongoing, ask for confirmation
                    if not board.game_over and not board.won and not board.first_click:
                        if confirm_dialog(screen, "Restart this game?", sfx):
                            return True
                    else:
                        return True
                if ev.key == pygame.K_m:
                    if not board.game_over and not board.won and not board.first_click:
                        if confirm_dialog(screen, "Return to menu?", sfx):
                            return "menu"        # type: ignore[return-value]
                    else:
                        return "menu"            # type: ignore[return-value]
                if ev.key == pygame.K_q:
                    return False

            if ev.type == pygame.MOUSEBUTTONDOWN:
                mx, my = ev.pos

                # Smiley button -> restart
                if smiley_rect.collidepoint(mx, my):
                    return True

                # Restart button
                if restart_rect.collidepoint(mx, my) and ev.button == 1:
                    if sfx:
                        SoundFX.play(sfx.menu_click)
                    if not board.game_over and not board.won and not board.first_click:
                        if confirm_dialog(screen, "Restart this game?", sfx):
                            return True
                    else:
                        return True
                    continue

                # Menu button
                if menu_rect.collidepoint(mx, my) and ev.button == 1:
                    if sfx:
                        SoundFX.play(sfx.menu_click)
                    if not board.game_over and not board.won and not board.first_click:
                        if confirm_dialog(screen, "Return to menu?", sfx):
                            return "menu"    # type: ignore[return-value]
                    else:
                        return "menu"        # type: ignore[return-value]
                    continue

                # Map click to grid cell
                c = (mx - offset_x) // cell_eff
                r = (my - offset_y) // cell_eff
                if 0 <= r < rows and 0 <= c < cols:
                    if ev.button == 1:  # left click
                        if not board.game_over and not board.won:
                            if start_time is None and board.first_click:
                                start_time = time.time()
                            # count revealed cells before to detect flood
                            prev_revealed = sum(
                                board.revealed[rr][cc]
                                for rr in range(rows) for cc in range(cols)
                            )
                            board.reveal(r, c)
                            new_revealed = sum(
                                board.revealed[rr][cc]
                                for rr in range(rows) for cc in range(cols)
                            )
                            # choose sound based on outcome
                            if sfx:
                                if board.game_over:
                                    SoundFX.play(sfx.explode)
                                    end_sound_played = True
                                elif board.won:
                                    SoundFX.play(sfx.win)
                                    end_sound_played = True
                                elif new_revealed - prev_revealed > 1:
                                    SoundFX.play(sfx.flood)
                                else:
                                    SoundFX.play(sfx.click)
                    elif ev.button == 3:  # right click
                        board.toggle_flag(r, c)
                        if sfx:
                            SoundFX.play(sfx.flag)
                    elif ev.button == 2:  # middle click (chord)
                        board.chord(r, c)
                        if sfx:
                            if board.game_over and not end_sound_played:
                                SoundFX.play(sfx.explode)
                                end_sound_played = True
                            elif board.won and not end_sound_played:
                                SoundFX.play(sfx.win)
                                end_sound_played = True
                            else:
                                SoundFX.play(sfx.click)

        # Timer
        if start_time and not board.game_over and not board.won:
            elapsed = int(time.time() - start_time)
        remaining = board.remaining_mines()

        # Draw - dark background
        screen.fill(COL_BG)
        renderer.draw_header(remaining, elapsed, smiley_rect,
                             board.game_over, board.won)
        renderer.draw_buttons(restart_rect, menu_rect)
        renderer.draw_board()

        # Win / Lose banner
        if board.game_over or board.won:
            # semi-transparent overlay bar
            banner_h = 32
            banner_y = win_h - BORDER - banner_h + 2
            banner_surf = pygame.Surface((win_w, banner_h), pygame.SRCALPHA)
            banner_surf.fill((36, 40, 50, 200))
            screen.blit(banner_surf, (0, banner_y))

            if board.game_over:
                msg = "GAME OVER  |  Click smiley or press R"
                msg_col = (191, 97, 106)
            else:
                msg = "YOU WIN!  |  Click smiley or press R"
                msg_col = (163, 190, 140)
            overlay = renderer.msg_font.render(msg, True, msg_col)
            screen.blit(overlay,
                        overlay.get_rect(centerx=win_w // 2,
                                         centery=banner_y + banner_h // 2))

        pygame.display.flip()
        clock.tick(60)

    return False


# ============================== entry point ==============================

def main():
    os.environ["SDL_VIDEO_CENTERED"] = "1"
    pygame.init()
    screen = pygame.display.set_mode((400, 440))

    # Load assets and sounds once (shared across all games)
    assets = Assets()
    sfx = SoundFX()

    while True:
        params = difficulty_menu(screen, assets, sfx)
        if params is None:
            break
        rows, cols, mines = params

        while True:
            result = game_loop(rows, cols, mines, assets, sfx)
            if result is True:
                continue               # restart same difficulty
            elif result == "menu":
                break                   # back to menu
            else:
                pygame.quit()
                sys.exit()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
