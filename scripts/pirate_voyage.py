#!/usr/bin/env python3
"""Aiden & Elliott sail a static pirate world: islands, a sunless sea trap,
enemy pirates, and an ancient temple hiding treasure.

Run: /usr/bin/python3 pirate_voyage.py   (needs a python3 build with curses)
Press 'q' to quit.
"""
import curses
import math
import random
import time

W = 88   # world width  (cols)
H = 26   # world height (rows)

# ---- color pair ids -------------------------------------------------
OCEAN, SUNLESS, SAND, GREEN, ROCK, GOLD, HULL, SAIL, ENEMY, TEXT, BORDER, \
    TREASURE, WHIRL, DANGER = range(1, 15)


def init_colors():
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(OCEAN, curses.COLOR_CYAN, -1)
    curses.init_pair(SUNLESS, curses.COLOR_BLUE, -1)
    curses.init_pair(SAND, curses.COLOR_YELLOW, -1)
    curses.init_pair(GREEN, curses.COLOR_GREEN, -1)
    curses.init_pair(ROCK, curses.COLOR_WHITE, -1)
    curses.init_pair(GOLD, curses.COLOR_YELLOW, -1)
    curses.init_pair(HULL, curses.COLOR_YELLOW, -1)
    curses.init_pair(SAIL, curses.COLOR_WHITE, -1)
    curses.init_pair(ENEMY, curses.COLOR_RED, -1)
    curses.init_pair(TEXT, curses.COLOR_WHITE, -1)
    curses.init_pair(BORDER, curses.COLOR_CYAN, -1)
    curses.init_pair(TREASURE, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    curses.init_pair(WHIRL, curses.COLOR_BLUE, -1)
    curses.init_pair(DANGER, curses.COLOR_RED, -1)


# ---- static-art helpers ----------------------------------------------
def new_grid(fill=' '):
    return [[fill] * W for _ in range(H)]


def stamp_ellipse(chars, colors, terrain, cy, cx, ry, rx, fill_chars, color, rng, mark="land"):
    for r in range(max(0, cy - ry), min(H, cy + ry + 1)):
        for c in range(max(0, cx - rx), min(W, cx + rx + 1)):
            dy = (r - cy) / ry if ry else 0
            dx = (c - cx) / rx if rx else 0
            if dy * dy + dx * dx <= 1.0:
                chars[r][c] = rng.choice(fill_chars)
                colors[r][c] = color
                terrain[r][c] = mark


def stamp_template(chars, colors, terrain, top, left, lines, color, mark="land", transparent=' '):
    for i, line in enumerate(lines):
        r = top + i
        if not (0 <= r < H):
            continue
        for j, ch in enumerate(line):
            c = left + j
            if not (0 <= c < W):
                continue
            if ch != transparent:
                chars[r][c] = ch
                colors[r][c] = color
                terrain[r][c] = mark


def stamp_text(chars, colors, terrain, row, col_center, text, color):
    left = col_center - len(text) // 2
    for j, ch in enumerate(text):
        c = left + j
        if 0 <= row < H and 0 <= c < W:
            chars[row][c] = ch
            colors[row][c] = color
            terrain[row][c] = "land"


PALM_TREE = [
    "  ,@@,  ",
    " @@@@@@ ",
    "   ||   ",
    "   ||   ",
]

SKULL = [
    "  .-\"\"-.  ",
    " / o  o \\ ",
    "|    ^   |",
    " \\ vvvv / ",
    "  '----'  ",
]

TEMPLE = [
    "        /\\        ",
    "       /  \\       ",
    "      /    \\      ",
    "     /  []  \\     ",
    "    /________\\    ",
    "   /   __     \\   ",
    "  /   |  |     \\  ",
    " /____|__|______\\ ",
]

SHIP_FRAMES = [
    ["   |>   ",
     "  /||\\  ",
     " [____] "],
    ["   |<   ",
     "  /||\\  ",
     " [____] "],
]

ENEMY_SHIP = [
    "  X|    ",
    " /||\\   ",
    "[____]  ",
]

CHEST_CLOSED = [
    " .------. ",
    " |[XXXX]| ",
    " '------' ",
]

CHEST_OPEN = [
    "  .----.   *",
    " *|$ $ $|  ",
    "  '----'  *",
]


class World:
    def __init__(self):
        rng = random.Random(1234)  # fixed seed -> stable background art
        self.chars = new_grid(' ')
        self.colors = new_grid(OCEAN)
        self.terrain = [["water"] * W for _ in range(H)]

        # Palm Cove
        pc_cy, pc_cx = 5, 14
        stamp_ellipse(self.chars, self.colors, self.terrain, pc_cy, pc_cx, 5, 9,
                       ".,:", SAND, rng)
        stamp_ellipse(self.chars, self.colors, self.terrain, pc_cy, pc_cx, 4, 7,
                       "\"^,", GREEN, rng)
        stamp_template(self.chars, self.colors, self.terrain, pc_cy - 3, pc_cx - 7, PALM_TREE, GREEN)
        stamp_template(self.chars, self.colors, self.terrain, pc_cy - 2, pc_cx + 2, PALM_TREE, GREEN)
        stamp_text(self.chars, self.colors, self.terrain, pc_cy + 6, pc_cx, "Palm Cove", SAND)

        # Skull Rock
        sr_cy, sr_cx = 5, 72
        stamp_ellipse(self.chars, self.colors, self.terrain, sr_cy, sr_cx, 5, 9,
                       ".", ROCK, rng)
        stamp_ellipse(self.chars, self.colors, self.terrain, sr_cy, sr_cx, 4, 7,
                       "^#%", ROCK, rng)
        stamp_template(self.chars, self.colors, self.terrain, sr_cy - 3, sr_cx - 5, SKULL, ROCK)
        stamp_text(self.chars, self.colors, self.terrain, sr_cy + 6, sr_cx, "Skull Rock", ROCK)

        # Ancient Temple / treasure island
        tp_cy, tp_cx = 19, 72
        stamp_ellipse(self.chars, self.colors, self.terrain, tp_cy, tp_cx, 5, 10,
                       ".,:", SAND, rng)
        stamp_ellipse(self.chars, self.colors, self.terrain, tp_cy, tp_cx, 4, 8,
                       ",.", SAND, rng)
        stamp_template(self.chars, self.colors, self.terrain, tp_cy - 6, tp_cx - 9, TEMPLE, GOLD)
        stamp_text(self.chars, self.colors, self.terrain, tp_cy + 6, tp_cx, "Ancient Temple", GOLD)
        self.chest_row, self.chest_col = tp_cy + 2, tp_cx - 5

        # Sunless Sea trap zone (rows 11-20, cols 28-57), water only
        for r in range(11, 21):
            for c in range(28, 58):
                if 0 <= r < H and 0 <= c < W and self.terrain[r][c] == "water":
                    self.terrain[r][c] = "sunless"
        self.whirl_center = (15, 42)

        self.enemy_ships = [(sr_cy + 3, sr_cx - 14), (sr_cy - 4, sr_cx - 17)]


WATER_GLYPHS = " ~-.~ "
SUNLESS_GLYPHS = "  ~. "
WHIRL_RING = [(0, -2), (-1, -1), (-1, 1), (0, 2), (1, 1), (1, -1)]

PATH = [
    (24, 3),   # 0 open sea / start
    (11, 14),  # 1 Palm Cove
    (11, 72),  # 2 Skull Rock
    (15, 42),  # 3 Sunless Sea / whirlpool
    (19, 60),  # 4 Ancient Temple approach
]

TRAVEL_CAPTIONS = {
    1: "Sailing out from port...",
    2: "Leaving Palm Cove behind...",
    3: "Rounding Skull Rock...",
    4: "Escaping the Sunless Sea...",
}

MESSAGES = {
    1: [("Aiden", "Land ho! Palm Cove dead ahead."),
        ("Elliott", "Let's search the shore for clues.")],
    2: [("Elliott", "Pirate ships! Stay low, Aiden."),
        ("Aiden", "They haven't spotted us... yet.")],
    3: [("Aiden", "The sea's gone dark - a whirlpool!"),
        ("Elliott", "Hard to starboard! Don't look down!")],
    4: [("Elliott", "The ancient temple... just like the map!"),
        ("Aiden", "The treasure must be inside!")],
}

SPEED = 0.22
HOLD_FRAMES = 45      # ~3.6s of dialogue per stop
TREASURE_FRAMES = 65  # ~5.2s of treasure reveal


def draw_row_run(stdscr, row, col0, text, color, attr=0):
    try:
        stdscr.addstr(row, col0, text, curses.color_pair(color) | attr)
    except curses.error:
        pass


def render_world(stdscr, world, frame, ship_pos, ship_frame, in_danger, top=1, left=0):
    rng_frame = frame // 3
    for r in range(H):
        row_chunks = []
        cur_color = None
        cur_str = []

        def flush(col_start):
            if cur_str:
                draw_row_run(stdscr, top + r, left + col_start, "".join(cur_str), cur_color)

        col_start = 0
        for c in range(W):
            terr = world.terrain[r][c]
            if terr == "land":
                ch = world.chars[r][c]
                col = world.colors[r][c]
            elif terr == "sunless":
                rng = random.Random((r * 977 + c * 131 + rng_frame) & 0xFFFF)
                ch = rng.choice(SUNLESS_GLYPHS)
                col = SUNLESS
            else:
                rng = random.Random((r * 733 + c * 17 + rng_frame) & 0xFFFF)
                ch = rng.choice(WATER_GLYPHS)
                col = OCEAN
            if col != cur_color:
                flush(col_start)
                cur_color = col
                cur_str = [ch]
                col_start = c
            else:
                cur_str.append(ch)
        flush(col_start)

    # whirlpool swirl overlay
    wr, wc = world.whirl_center
    k = frame % len(WHIRL_RING)
    for i, (dr, dc) in enumerate(WHIRL_RING):
        rr, cc = wr + dr, wc + dc
        if 0 <= rr < H and 0 <= cc < W:
            glyph = "@" if i == k else ("o" if i == (k - 1) % len(WHIRL_RING) else None)
            if glyph:
                draw_row_run(stdscr, top + rr, left + cc, glyph, WHIRL, curses.A_BOLD)
    draw_row_run(stdscr, top + wr, left + wc, "O", WHIRL, curses.A_BOLD)

    # enemy ships (gentle bob)
    bob = int(math.sin(frame * 0.15) * 1)
    for (er, ec) in world.enemy_ships:
        for i, line in enumerate(ENEMY_SHIP):
            draw_row_run(stdscr, top + er + bob + i, left + ec, line, ENEMY, curses.A_BOLD)

    # player ship
    sr, sc = ship_pos
    sbob = int(math.sin(frame * 0.2) * 1)
    color = DANGER if in_danger else HULL
    for i, line in enumerate(SHIP_FRAMES[ship_frame % 2]):
        draw_row_run(stdscr, top + int(sr) + sbob + i, left + int(sc) - 4, line, color, curses.A_BOLD)


def render_box(stdscr, top, width, lines, color=TEXT, title=None):
    border = "+" + "-" * (width - 2) + "+"
    draw_row_run(stdscr, top, 0, border, BORDER)
    body_h = len(lines) + 2
    for i in range(1, body_h - 1):
        text = lines[i - 1] if i - 1 < len(lines) else ""
        text = text[:width - 4]
        padded = "| " + text.ljust(width - 4) + " |"
        draw_row_run(stdscr, top + i, 0, padded, color)
    draw_row_run(stdscr, top + body_h - 1, 0, border, BORDER)
    return body_h


def render_chest(stdscr, world, top, left, opened):
    art = CHEST_OPEN if opened else CHEST_CLOSED
    for i, line in enumerate(art):
        draw_row_run(stdscr, top + world.chest_row + i, left + world.chest_col, line,
                     TREASURE if opened else GOLD, curses.A_BOLD)


def main(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)
    init_colors()
    world = World()

    ship_pos = list(PATH[0])
    target_idx = 1
    mode = "TRAVEL"
    hold_timer = 0
    frame = 0
    ship_frame = 0

    while True:
        ch = stdscr.getch()
        if ch in (ord('q'), ord('Q')):
            break

        h, w = stdscr.getmaxyx()
        left = max(0, (w - W) // 2)

        stdscr.erase()
        title = "~ Aiden & Elliott: Voyage of the Sunless Sea ~"
        draw_row_run(stdscr, 0, max(0, (w - len(title)) // 2), title, GOLD, curses.A_BOLD)

        tr, tc = ship_pos
        in_danger = world.terrain[min(H - 1, int(tr))][min(W - 1, int(tc))] == "sunless"

        render_world(stdscr, world, frame, ship_pos, ship_frame, in_danger, top=1, left=left)

        box_top = 1 + H + 1
        box_width = min(W, w - 2 * left if left else W)

        if mode == "TRAVEL":
            caption = TRAVEL_CAPTIONS.get(target_idx, "Sailing onward...")
            render_box(stdscr, box_top, box_width, [caption])
        elif mode == "DIALOGUE":
            lines = [f"{who}: {text}" for who, text in MESSAGES.get(target_idx, [])]
            render_box(stdscr, box_top, box_width, lines)
        elif mode == "TREASURE":
            opened = hold_timer < TREASURE_FRAMES - 10
            render_chest(stdscr, world, 1, left, opened)
            lines = ["*** TREASURE FOUND! ***", "Aiden & Elliott strike gold at last!"]
            render_box(stdscr, box_top, box_width, lines, color=TREASURE)

        stdscr.refresh()

        # ---- state machine ----
        if mode == "TRAVEL":
            gy, gx = PATH[target_idx]
            dy, dx = gy - ship_pos[0], gx - ship_pos[1]
            dist = math.hypot(dy, dx)
            if dist < 0.6:
                ship_pos[0], ship_pos[1] = gy, gx
                mode = "DIALOGUE"
                hold_timer = HOLD_FRAMES
            else:
                ship_pos[0] += dy / dist * SPEED
                ship_pos[1] += dx / dist * SPEED
        elif mode == "DIALOGUE":
            hold_timer -= 1
            if hold_timer <= 0:
                if target_idx == len(PATH) - 1:
                    mode = "TREASURE"
                    hold_timer = TREASURE_FRAMES
                else:
                    target_idx += 1
                    mode = "TRAVEL"
        elif mode == "TREASURE":
            hold_timer -= 1
            if hold_timer <= 0:
                ship_pos = list(PATH[0])
                target_idx = 1
                mode = "TRAVEL"

        frame += 1
        if frame % 6 == 0:
            ship_frame += 1
        time.sleep(0.08)


if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass
