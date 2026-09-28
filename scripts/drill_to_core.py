#!/usr/bin/env python3
"""Kid with a drill digs straight down to the center of the Earth.

Run in a narrow tmux pane: python3 drill_to_core.py
Press 'q' to quit.
"""
import curses
import random
import time
import math

TOTAL_DEPTH = 320          # abstract "depth units" from surface to center
DEPTH_PER_FRAME = 0.35     # how fast the kid digs
FRAME_DELAY = 0.07

# (max_depth, name, temp_color_pair, band_color_pair, chars)
BANDS = [
    (10,  "SURFACE",     1, 1, " ,\"'^,."),
    (35,  "TOPSOIL",     2, 2, ".:oO."),
    (90,  "CRUST",       3, 3, "#%X#="),
    (160, "DEEP CRUST",  3, 4, "#&%$#"),
    (230, "MANTLE",      5, 5, "~^*#~^"),
    (285, "OUTER CORE",  6, 6, "@*^~@"),
    (10**9, "INNER CORE", 7, 7, "@#*%@"),
]


def band_for(depth):
    for max_d, name, tcol, bcol, chars in BANDS:
        if depth < max_d:
            return name, tcol, bcol, chars
    return BANDS[-1][1:]


def temp_for(depth):
    d = max(0.0, depth)
    return 15 + (d ** 1.6) * 0.9


def temp_color(temp):
    if temp < 40:
        return 1
    if temp < 150:
        return 2
    if temp < 700:
        return 3
    if temp < 2000:
        return 5
    if temp < 4000:
        return 6
    return 7


def init_colors():
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_GREEN, -1)
    curses.init_pair(2, curses.COLOR_YELLOW, -1)
    curses.init_pair(3, curses.COLOR_WHITE, -1)
    curses.init_pair(4, curses.COLOR_RED, -1)
    curses.init_pair(5, curses.COLOR_RED, curses.COLOR_BLACK)
    curses.init_pair(6, curses.COLOR_YELLOW, curses.COLOR_RED)
    curses.init_pair(7, curses.COLOR_WHITE, curses.COLOR_MAGENTA)
    curses.init_pair(8, curses.COLOR_CYAN, -1)


def row_texture(win_width, row_depth, chars):
    rng = random.Random(int(row_depth * 7) ^ 0x9E3779B9)
    return "".join(rng.choice(chars) for _ in range(win_width))


KID_FRAMES = [
    ["  o  ",
     " /|\\ ",
     " / \\ ",
     "  ||  "],
    ["  o  ",
     " \\|/ ",
     " / \\ ",
     "  ||  "],
]

SPARKS = "*+.'`"


def draw(stdscr, depth, frame_i):
    h, w = stdscr.getmaxyx()
    stdscr.erase()

    name, tcol, bcol, chars = band_for(depth)
    temp = temp_for(depth)
    tc = temp_color(temp)

    # HUD
    pct = min(100, depth / TOTAL_DEPTH * 100)
    bar_w = max(10, w - 40)
    filled = int(bar_w * pct / 100)
    bar = "#" * filled + "-" * (bar_w - filled)
    hud1 = f" Depth: {depth:6.1f}/{TOTAL_DEPTH} [{bar}] {pct:5.1f}%"
    hud2 = f" Layer: {name:<12}  Temp: {temp:8.1f} C"

    try:
        stdscr.addstr(0, 0, hud1[:w - 1], curses.color_pair(8) | curses.A_BOLD)
        stdscr.addstr(1, 0, hud2[:w - 1], curses.color_pair(tc) | curses.A_BOLD)
    except curses.error:
        pass

    shaft_top = 3
    kid_row = shaft_top + 3
    shaft_h = h - shaft_top - 1
    if shaft_h < 6:
        return

    center_col = w // 2

    # scrolling rock texture, each screen row maps to an absolute depth
    for r in range(shaft_h):
        screen_row = shaft_top + r
        row_depth = depth + (r - 3)
        if row_depth < 0:
            continue
        _, _, row_bcol, row_chars = band_for(row_depth)
        text = row_texture(w, row_depth, row_chars)
        try:
            stdscr.addstr(screen_row, 0, text, curses.color_pair(row_bcol))
        except curses.error:
            pass

    # tunnel walls already drilled: blank vertical shaft behind the kid
    tunnel_w = 7
    for r in range(0, 4):
        screen_row = shaft_top + r
        if 0 <= screen_row < h:
            try:
                stdscr.addstr(screen_row, max(0, center_col - tunnel_w // 2),
                              " " * tunnel_w, curses.color_pair(0))
            except curses.error:
                pass

    # kid + drill
    kid = KID_FRAMES[frame_i % 2]
    kx = max(0, center_col - 2)
    for i, line in enumerate(kid):
        ry = shaft_top + i
        if 0 <= ry < h:
            try:
                stdscr.addstr(ry, kx, line, curses.color_pair(tc) | curses.A_BOLD)
            except curses.error:
                pass

    # sparks/debris at the drill face
    spark_row = shaft_top + 4
    rng = random.Random(frame_i)
    spark_line = "".join(
        rng.choice(SPARKS) if rng.random() < 0.6 else " " for _ in range(7)
    )
    if 0 <= spark_row < h:
        try:
            stdscr.addstr(spark_row, kx, spark_line, curses.color_pair(6) | curses.A_BOLD)
        except curses.error:
            pass

    if depth >= TOTAL_DEPTH:
        msg = "*** REACHED THE CENTER OF THE EARTH ***"
        my = h // 2
        mx = max(0, (w - len(msg)) // 2)
        try:
            stdscr.addstr(my, mx, msg, curses.color_pair(7) | curses.A_BOLD | curses.A_BLINK)
        except curses.error:
            pass

    stdscr.refresh()


def main(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)
    init_colors()

    depth = 0.0
    frame_i = 0
    pause_until = None

    while True:
        ch = stdscr.getch()
        if ch in (ord('q'), ord('Q')):
            break

        draw(stdscr, depth, frame_i)

        if pause_until is not None:
            if time.time() > pause_until:
                depth = 0.0
                pause_until = None
        else:
            depth += DEPTH_PER_FRAME
            if depth >= TOTAL_DEPTH:
                depth = TOTAL_DEPTH
                pause_until = time.time() + 3.0

        frame_i += 1
        time.sleep(FRAME_DELAY)


if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass
