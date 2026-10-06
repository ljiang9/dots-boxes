#!/usr/bin/env python3
"""点格棋 (Dots and Boxes): 画线圈地小游戏,纯标准库实现."""

import argparse
import copy
import random
import sys

EMPTY = " "
H_EDGE = "-"
V_EDGE = "|"
DOT = "+"


class DotsBoxes:
    """rows x cols 个点, (rows-1) x (cols-1) 个格子."""

    def __init__(self, rows=6, cols=6):
        if rows < 2 or cols < 2:
            raise ValueError("棋盘至少需要 2x2 个点")
        self.rows = rows
        self.cols = cols
        # 横边: rows 行 x (cols-1) 列; 竖边: (rows-1) 行 x cols 列
        self.h = [[False] * (cols - 1) for _ in range(rows)]
        self.v = [[False] * cols for _ in range(rows - 1)]
        # 格子归属: (rows-1) x (cols-1), None / 0 / 1
        self.owner = [[None] * (cols - 1) for _ in range(rows - 1)]
        self.scores = [0, 0]
        self.n_moves = 0

    @property
    def n_boxes(self):
        return (self.rows - 1) * (self.cols - 1)

    def total_edges(self):
        return self.rows * (self.cols - 1) + (self.rows - 1) * self.cols

    # ---- 走法 ----

    def _check_move(self, move):
        kind, r, c = move
        if kind == "h":
            if not (0 <= r < self.rows and 0 <= c < self.cols - 1):
                raise ValueError(f"横边越界: {move}")
            if self.h[r][c]:
                raise ValueError(f"横边已画过: {move}")
        elif kind == "v":
            if not (0 <= r < self.rows - 1 and 0 <= c < self.cols):
                raise ValueError(f"竖边越界: {move}")
            if self.v[r][c]:
                raise ValueError(f"竖边已画过: {move}")
        else:
            raise ValueError(f"走法类型必须是 h/v: {move}")

    def legal_moves(self):
        moves = []
        for r in range(self.rows):
            for c in range(self.cols - 1):
                if not self.h[r][c]:
                    moves.append(("h", r, c))
        for r in range(self.rows - 1):
            for c in range(self.cols):
                if not self.v[r][c]:
                    moves.append(("v", r, c))
        return moves

    def box_edge_count(self, br, bc):
        """格子 (br,bc) 已画的边数."""
        return (
            self.h[br][bc] + self.h[br + 1][bc]
            + self.v[br][bc] + self.v[br][bc + 1]
        )

    def apply_move(self, player, move):
        """画一条边,返回本次圈到的格子数(0/1/2).非法走法抛 ValueError."""
        if player not in (0, 1):
            raise ValueError("玩家必须是 0 或 1")
        self._check_move(move)
        kind, r, c = move
        if kind == "h":
            self.h[r][c] = True
        else:
            self.v[r][c] = True
        self.n_moves += 1
        claimed = 0
        # 一条边最多影响相邻两个格子
        boxes = []
        if kind == "h":
            if r > 0:
                boxes.append((r - 1, c))
            if r < self.rows - 1:
                boxes.append((r, c))
        else:
            if c > 0:
                boxes.append((r, c - 1))
            if c < self.cols - 1:
                boxes.append((r, c))
        for br, bc in boxes:
            if self.owner[br][bc] is None and self.box_edge_count(br, bc) == 4:
                self.owner[br][bc] = player
                self.scores[player] += 1
                claimed += 1
        return claimed

    def is_over(self):
        return self.n_moves >= self.total_edges()

    def winner(self):
        """返回 0/1/None(平局)."""
        if not self.is_over():
            return None
        if self.scores[0] > self.scores[1]:
            return 0
        if self.scores[1] > self.scores[0]:
            return 1
        return None

    # ---- 渲染 ----

    def render(self, cur=None):
        lines = []
        label = ["甲", "乙"]
        for r in range(self.rows):
            row = []
            for c in range(self.cols):
                row.append(DOT)
                if c < self.cols - 1:
                    row.append(H_EDGE if self.h[r][c] else EMPTY)
            lines.append("".join(row))
            if r < self.rows - 1:
                row2 = []
                for c in range(self.cols):
                    row2.append(V_EDGE if self.v[r][c] else EMPTY)
                    if c < self.cols - 1:
                        o = self.owner[r][c]
                        row2.append(label[o] if o is not None else EMPTY)
                lines.append("".join(row2))
        head = f"甲:{self.scores[0]}  乙:{self.scores[1]}  已画 {self.n_moves}/{self.total_edges()}"
        if cur is not None:
            head += f"  轮到:{label[cur]}"
        return head + "\n" + "\n".join(lines)


# ---- AI ----

def _chain_size_after(game, move, player):
    """假设 player 走 move 后,会送给对手的"链"有多大.

    把走完后所有恰好 3 条边的格子连成图(四邻接),返回其中
    包含 move 相邻格子的那一团的大小;若 move 本人圈了格子则返回 0.
    """
    g = copy.deepcopy(game)
    claimed = g.apply_move(player, move)
    if claimed:
        return 0
    R, C = g.rows - 1, g.cols - 1
    # 找受影响格
    kind, r, c = move
    seeds = set()
    if kind == "h":
        if r > 0:
            seeds.add((r - 1, c))
        if r < g.rows - 1:
            seeds.add((r, c))
    else:
        if c > 0:
            seeds.add((r, c - 1))
        if c < g.cols - 1:
            seeds.add((r, c))
    # 在"3 边格"子图上 BFS
    seen = set()
    best = 0
    for s in seeds:
        if s in seen or g.owner[s[0]][s[1]] is not None:
            continue
        if g.box_edge_count(*s) != 3:
            continue
        stack, comp = [s], set()
        while stack:
            cell = stack.pop()
            if cell in comp:
                continue
            comp.add(cell)
            br, bc = cell
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nb = (br + dr, bc + dc)
                if (0 <= nb[0] < R and 0 <= nb[1] < C
                        and g.owner[nb[0]][nb[1]] is None
                        and g.box_edge_count(*nb) == 3
                        and nb not in comp):
                    stack.append(nb)
        seen |= comp
        best = max(best, len(comp))
    return best


def ai_move(game, player, rng):
    """贪心 + 链感知:
    1) 有能圈格的走法就圈(圈得多的优先);
    2) 否则挑"送链最小"的走法,尽量不送对手免费格子.
    """
    moves = game.legal_moves()
    rng.shuffle(moves)
    # 1) 圈格
    best, best_claim = None, -1
    for m in moves:
        g = copy.deepcopy(game)
        claimed = g.apply_move(player, m)
        if claimed > best_claim:
            best, best_claim = m, claimed
    if best is not None and best_claim > 0:
        return best
    # 2) 链感知:最小化送出的链
    scored = []
    for m in moves:
        scored.append((_chain_size_after(game, m, player), m))
    scored.sort(key=lambda x: x[0])
    min_chain = scored[0][0]
    cands = [m for ch, m in scored if ch == min_chain]
    return rng.choice(cands)


def play_auto(rows=6, cols=6, games=10, seed=42, verbose=False):
    rng = random.Random(seed)
    wins = [0, 0]
    draws = 0
    for gi in range(games):
        game = DotsBoxes(rows, cols)
        player = 0
        while not game.is_over():
            m = ai_move(game, player, rng)
            claimed = game.apply_move(player, m)
            if verbose:
                kind, r, c = m
                print(f"第{gi+1}局 {['甲','乙'][player]}: {kind} {r} {c} 圈{claimed}格")
            if claimed == 0:
                player = 1 - player
        w = game.winner()
        if w is None:
            draws += 1
        else:
            wins[w] += 1
        print(f"第 {gi+1}/{games} 局: 甲 {game.scores[0]} - 乙 {game.scores[1]}"
              f"  {'甲胜' if w == 0 else '乙胜' if w == 1 else '平局'}")
    print(f"总计: 甲胜 {wins[0]}, 乙胜 {wins[1]}, 平局 {draws}")
    return wins, draws


def play_interactive(rows=6, cols=6, seed=None):
    rng = random.Random(seed)
    game = DotsBoxes(rows, cols)
    player = 0  # 0=人类甲, 1=AI乙
    print("点格棋:输入如 `h 0 1`(横边) 或 `v 2 3`(竖边),q 退出。圈到格子可再走一步。")
    while not game.is_over():
        print()
        print(game.render(cur=player))
        if player == 0:
            try:
                s = input("你走: ").strip().lower()
            except EOFError:
                print("\n结束。")
                return
            if s in ("q", "quit", "exit"):
                print("已退出。")
                return
            parts = s.split()
            if len(parts) != 3 or parts[0] not in ("h", "v"):
                print("格式不对,示例: h 0 1")
                continue
            try:
                move = (parts[0], int(parts[1]), int(parts[2]))
                claimed = game.apply_move(0, move)
            except (ValueError, IndexError) as e:
                print(f"非法走法: {e}")
                continue
            print(f"你圈了 {claimed} 格。" if claimed else "没圈到。")
            if claimed == 0:
                player = 1
        else:
            m = ai_move(game, 1, rng)
            claimed = game.apply_move(1, m)
            kind, r, c = m
            print(f"AI 走: {kind} {r} {c}, 圈了 {claimed} 格。")
            if claimed == 0:
                player = 0
    print()
    print(game.render())
    w = game.winner()
    print(f"终局: 甲 {game.scores[0]} - 乙 {game.scores[1]}",
          "你赢了!" if w == 0 else "AI 赢了!" if w == 1 else "平局!")


def main(argv=None):
    ap = argparse.ArgumentParser(description="点格棋 (Dots and Boxes)")
    ap.add_argument("--rows", type=int, default=6, help="点行数(默认6)")
    ap.add_argument("--cols", type=int, default=6, help="点列数(默认6)")
    ap.add_argument("--auto", action="store_true", help="AI 对 AI 自动演示")
    ap.add_argument("--games", type=int, default=10, help="自动演示局数")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--verbose", action="store_true", help="自动演示打印每步")
    args = ap.parse_args(argv)
    if args.auto:
        play_auto(rows=args.rows, cols=args.cols, games=args.games,
                  seed=args.seed, verbose=args.verbose)
    else:
        if not sys.stdin.isatty():
            print("交互模式需要终端;无头演示请用 --auto。", file=sys.stderr)
            sys.exit(2)
        play_interactive(rows=args.rows, cols=args.cols, seed=args.seed)


if __name__ == "__main__":
    main()
