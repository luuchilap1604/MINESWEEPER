"""
Minesweeper – Pygame Implementation
=====================================
Features:
  • Three difficulty presets: Easy (5×5), Medium (9×9), Hard (16×16)
  • Left-click to reveal a cell, right-click to toggle flag
  • DFS flood-fill to open blank (zero-neighbour) regions
  • Mine counter, elapsed-time timer, smiley reset button
  • Win / Lose detection with full board reveal
"""

import sys
import random
import time
import pygame

# ─────────────────────────── constants ────────────────────────────

CELL_SIZE = 40
HEADER_HEIGHT = 60
BORDER = 12

# Colours (R, G, B)
COL_BG          = (192, 192, 192)
COL_BORDER_LT   = (255, 255, 255)
COL_BORDER_DK   = (128, 128, 128)
COL_REVEALED    = (189, 189, 189)
COL_GRID_LINE   = (128, 128, 128)
COL_MINE        = (0, 0, 0)
COL_FLAG_RED    = (255, 0, 0)
COL_FLAG_POLE   = (0, 0, 0)
COL_EXPLODED    = (255, 0, 0)
COL_COUNTER_BG  = (0, 0, 0)
COL_COUNTER_FG  = (255, 0, 0)
COL_HEADER_BG   = (192, 192, 192)
COL_BUTTON_FACE = (192, 192, 192)

NUMBER_COLOURS = {
    1: (0, 0, 255),
    2: (0, 128, 0),
    3: (255, 0, 0),
    4: (0, 0, 128),
    5: (128, 0, 0),
    6: (0, 128, 128),
    7: (0, 0, 0),
    8: (128, 128, 128),
}

# Difficulty presets: (rows, cols, mines)
DIFFICULTIES = {
    "Easy (5×5)":    (5, 5, 4),
    "Medium (9×9)":  (9, 9, 10),
    "Hard (16×16)":  (16, 16, 40),
}

# ─────────────────────────── board logic ──────────────────────────

class Board:
    """Pure game-logic layer – no rendering."""

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

    # ── mine placement (deferred until first click) ──

    def _place_mines(self, safe_r: int, safe_c: int):
        """Place mines randomly, keeping a 3×3 safe zone around first click."""
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

    # ── DFS flood-fill ──

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

    # ── public actions ──

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


# ─────────────────────────── renderer ─────────────────────────────

class Renderer:
    """Handles all Pygame drawing."""

    def __init__(self, surface: pygame.Surface, board: Board,
                 offset_x: int, offset_y: int):
        self.surface = surface
        self.board = board
        self.ox = offset_x
        self.oy = offset_y
        self.cell = CELL_SIZE
        self.num_font = pygame.font.SysFont("Arial", CELL_SIZE * 3 // 5, bold=True)
        self.counter_font = pygame.font.SysFont("Consolas", 28, bold=True)
        self.smiley_font = pygame.font.SysFont("Segoe UI Emoji", 26)
        self.msg_font = pygame.font.SysFont("Arial", 20, bold=True)

    # ── helper drawers ──

    def _rect_for(self, r: int, c: int) -> pygame.Rect:
        return pygame.Rect(self.ox + c * self.cell,
                           self.oy + r * self.cell,
                           self.cell, self.cell)

    def _draw_raised(self, rect: pygame.Rect):
        """3-D raised button look."""
        pygame.draw.rect(self.surface, COL_BG, rect)
        # top + left highlight
        pygame.draw.line(self.surface, COL_BORDER_LT,
                         rect.topleft, rect.topright, 2)
        pygame.draw.line(self.surface, COL_BORDER_LT,
                         rect.topleft, rect.bottomleft, 2)
        # bottom + right shadow
        pygame.draw.line(self.surface, COL_BORDER_DK,
                         rect.bottomleft, rect.bottomright, 2)
        pygame.draw.line(self.surface, COL_BORDER_DK,
                         rect.topright, rect.bottomright, 2)

    def _draw_flag(self, rect: pygame.Rect):
        cx, cy = rect.center
        # pole
        pygame.draw.line(self.surface, COL_FLAG_POLE,
                         (cx, cy - self.cell // 4),
                         (cx, cy + self.cell // 4), 2)
        # triangle flag
        pts = [
            (cx, cy - self.cell // 4),
            (cx - self.cell // 4, cy - self.cell // 8),
            (cx, cy),
        ]
        pygame.draw.polygon(self.surface, COL_FLAG_RED, pts)
        # base
        pygame.draw.line(self.surface, COL_FLAG_POLE,
                         (cx - self.cell // 5, cy + self.cell // 4),
                         (cx + self.cell // 5, cy + self.cell // 4), 2)

    def _draw_mine(self, rect: pygame.Rect, exploded: bool = False):
        if exploded:
            pygame.draw.rect(self.surface, COL_EXPLODED, rect)
        cx, cy = rect.center
        radius = self.cell // 5
        pygame.draw.circle(self.surface, COL_MINE, (cx, cy), radius)
        # spikes
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1),
                        (-1, -1), (1, 1), (-1, 1), (1, -1)]:
            sx = cx + int(dx * radius * 1.5)
            sy = cy + int(dy * radius * 1.5)
            pygame.draw.line(self.surface, COL_MINE, (cx, cy), (sx, sy), 2)
        # glint
        pygame.draw.circle(self.surface, (255, 255, 255),
                           (cx - radius // 3, cy - radius // 3),
                           radius // 4)

    def _draw_wrong_flag(self, rect: pygame.Rect):
        """Draw an X over a wrongly flagged cell (game over)."""
        self._draw_flag(rect)
        pygame.draw.line(self.surface, (255, 0, 0),
                         rect.topleft, rect.bottomright, 3)
        pygame.draw.line(self.surface, (255, 0, 0),
                         rect.topright, rect.bottomleft, 3)

    # ── main draw ──

    def draw_board(self):
        b = self.board
        for r in range(b.rows):
            for c in range(b.cols):
                rect = self._rect_for(r, c)
                if b.revealed[r][c]:
                    pygame.draw.rect(self.surface, COL_REVEALED, rect)
                    pygame.draw.rect(self.surface, COL_GRID_LINE, rect, 1)
                    if b.mines[r][c]:
                        self._draw_mine(rect, exploded=True)
                    elif b.neighbour[r][c] > 0:
                        txt = self.num_font.render(
                            str(b.neighbour[r][c]), True,
                            NUMBER_COLOURS.get(b.neighbour[r][c], (0, 0, 0)))
                        self.surface.blit(
                            txt, txt.get_rect(center=rect.center))
                else:
                    # unrevealed
                    if b.game_over:
                        # reveal mines / show wrong flags
                        if b.mines[r][c] and not b.flagged[r][c]:
                            pygame.draw.rect(self.surface, COL_REVEALED, rect)
                            pygame.draw.rect(self.surface, COL_GRID_LINE, rect, 1)
                            self._draw_mine(rect)
                        elif b.flagged[r][c] and not b.mines[r][c]:
                            pygame.draw.rect(self.surface, COL_REVEALED, rect)
                            pygame.draw.rect(self.surface, COL_GRID_LINE, rect, 1)
                            self._draw_wrong_flag(rect)
                        elif b.flagged[r][c] and b.mines[r][c]:
                            self._draw_raised(rect)
                            self._draw_flag(rect)
                        else:
                            self._draw_raised(rect)
                    else:
                        self._draw_raised(rect)
                        if b.flagged[r][c]:
                            self._draw_flag(rect)

    def draw_header(self, remaining: int, elapsed: int,
                    smiley_rect: pygame.Rect, game_over: bool, won: bool):
        header_rect = pygame.Rect(0, 0, self.surface.get_width(), HEADER_HEIGHT)
        pygame.draw.rect(self.surface, COL_HEADER_BG, header_rect)

        # mine counter (left)
        counter_text = f"{remaining:03d}"
        ctr_surf = self.counter_font.render(counter_text, True, COL_COUNTER_FG)
        ctr_bg = pygame.Rect(BORDER, (HEADER_HEIGHT - 32) // 2, 64, 32)
        pygame.draw.rect(self.surface, COL_COUNTER_BG, ctr_bg)
        self.surface.blit(ctr_surf, ctr_surf.get_rect(center=ctr_bg.center))

        # timer (right)
        time_text = f"{min(elapsed, 999):03d}"
        tm_surf = self.counter_font.render(time_text, True, COL_COUNTER_FG)
        tm_bg = pygame.Rect(self.surface.get_width() - BORDER - 64,
                            (HEADER_HEIGHT - 32) // 2, 64, 32)
        pygame.draw.rect(self.surface, COL_COUNTER_BG, tm_bg)
        self.surface.blit(tm_surf, tm_surf.get_rect(center=tm_bg.center))

        # smiley button (centre)
        pygame.draw.rect(self.surface, COL_BUTTON_FACE, smiley_rect)
        pygame.draw.rect(self.surface, COL_BORDER_DK, smiley_rect, 2)
        if won:
            face = "😎"
        elif game_over:
            face = "😵"
        else:
            face = "🙂"
        face_surf = self.smiley_font.render(face, True, (0, 0, 0))
        self.surface.blit(face_surf,
                          face_surf.get_rect(center=smiley_rect.center))


# ─────────────────────────── menu screen ──────────────────────────

def difficulty_menu(screen: pygame.Surface) -> tuple[int, int, int] | None:
    """Simple difficulty selection screen. Returns (rows, cols, mines) or None to quit."""
    menu_w, menu_h = 360, 380
    screen = pygame.display.set_mode((menu_w, menu_h))
    pygame.display.set_caption("Minesweeper – Select Difficulty")

    title_font = pygame.font.SysFont("Arial", 32, bold=True)
    btn_font = pygame.font.SysFont("Arial", 22)
    small_font = pygame.font.SysFont("Arial", 15)

    buttons: list[tuple[pygame.Rect, str, tuple[int, int, int]]] = []
    y = 100
    for name, (rows, cols, mines) in DIFFICULTIES.items():
        rect = pygame.Rect((menu_w - 260) // 2, y, 260, 48)
        buttons.append((rect, name, (rows, cols, mines)))
        y += 68

    clock = pygame.time.Clock()

    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return None
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                for rect, _, params in buttons:
                    if rect.collidepoint(ev.pos):
                        return params

        screen.fill(COL_BG)

        # title
        title = title_font.render("MINESWEEPER", True, (0, 0, 128))
        screen.blit(title, title.get_rect(centerx=menu_w // 2, y=24))

        sub = small_font.render("Select difficulty to begin", True, (60, 60, 60))
        screen.blit(sub, sub.get_rect(centerx=menu_w // 2, y=64))

        # buttons
        mx, my = pygame.mouse.get_pos()
        for rect, name, (rows, cols, mines) in buttons:
            hovered = rect.collidepoint(mx, my)
            col = (220, 220, 255) if hovered else (200, 200, 200)
            pygame.draw.rect(screen, col, rect, border_radius=6)
            pygame.draw.rect(screen, (80, 80, 80), rect, 2, border_radius=6)
            label = btn_font.render(name, True, (0, 0, 0))
            screen.blit(label, label.get_rect(center=rect.center))

            detail = small_font.render(
                f"{rows}×{cols}  –  {mines} mines", True, (90, 90, 90))
            screen.blit(detail,
                        detail.get_rect(centerx=rect.centerx,
                                        top=rect.bottom + 4))

        pygame.display.flip()
        clock.tick(30)


# ─────────────────────────── main game loop ───────────────────────

def game_loop(rows: int, cols: int, num_mines: int) -> bool:
    """Run one game. Returns True to restart, False to quit."""
    board = Board(rows, cols, num_mines)

    win_w = 2 * BORDER + cols * CELL_SIZE
    win_h = HEADER_HEIGHT + BORDER + rows * CELL_SIZE + BORDER
    screen = pygame.display.set_mode((win_w, win_h))
    pygame.display.set_caption("Minesweeper")

    offset_x = BORDER
    offset_y = HEADER_HEIGHT + BORDER

    renderer = Renderer(screen, board, offset_x, offset_y)

    smiley_rect = pygame.Rect((win_w - 36) // 2,
                               (HEADER_HEIGHT - 36) // 2, 36, 36)

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
                    return True          # restart same difficulty
                if ev.key == pygame.K_m:
                    return "menu"        # type: ignore[return-value]
                if ev.key == pygame.K_q:
                    return False

            if ev.type == pygame.MOUSEBUTTONDOWN:
                mx, my = ev.pos

                # Smiley button → restart
                if smiley_rect.collidepoint(mx, my):
                    return True

                # Map click to grid cell
                c = (mx - offset_x) // CELL_SIZE
                r = (my - offset_y) // CELL_SIZE
                if 0 <= r < rows and 0 <= c < cols:
                    if ev.button == 1:  # left click
                        if not board.game_over and not board.won:
                            if start_time is None and board.first_click:
                                start_time = time.time()
                            board.reveal(r, c)
                    elif ev.button == 3:  # right click
                        board.toggle_flag(r, c)
                    elif ev.button == 2:  # middle click (chord)
                        board.chord(r, c)

        # Timer
        if start_time and not board.game_over and not board.won:
            elapsed = int(time.time() - start_time)
        remaining = board.remaining_mines()

        # Draw
        screen.fill(COL_BG)
        renderer.draw_header(remaining, elapsed, smiley_rect,
                             board.game_over, board.won)
        renderer.draw_board()

        # Win / Lose overlay text
        if board.game_over:
            overlay = renderer.msg_font.render(
                "GAME OVER – Click 🙂 or press R to restart",
                True, (200, 0, 0))
            screen.blit(overlay,
                        overlay.get_rect(centerx=win_w // 2,
                                         y=win_h - BORDER + 2 - 20))
        elif board.won:
            overlay = renderer.msg_font.render(
                "YOU WIN! – Click 🙂 or press R to restart",
                True, (0, 128, 0))
            screen.blit(overlay,
                        overlay.get_rect(centerx=win_w // 2,
                                         y=win_h - BORDER + 2 - 20))

        pygame.display.flip()
        clock.tick(60)

    return False


# ─────────────────────────── entry point ──────────────────────────

def main():
    pygame.init()
    screen = pygame.display.set_mode((360, 380))

    while True:
        params = difficulty_menu(screen)
        if params is None:
            break
        rows, cols, mines = params

        while True:
            result = game_loop(rows, cols, mines)
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
