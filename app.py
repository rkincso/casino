"""Local browser table; run with uv run python app.py."""
import json
import random
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from casino import CARDS, Move, new_deal, legal_moves, play, score, deal_over, value

state = None
history = []
difficulty = 'medium'
lock = threading.Lock()


def record(move, actor):
    action = 'captured: ' + ', '.join(sorted(move.table)) if move.table else 'placed a card'
    history.append(f'{actor}: {", ".join(sorted(move.hand))} → {action}.')


def choose_computer_move(current, level):
    moves = legal_moves(current)
    if level == 'easy':
        return random.choice(moves)
    if level == 'medium':
        return max(moves, key=lambda m: (
            bool(m.table), len(m.table) == len(current.table) and bool(m.table),
            sum(2 if c == '10D' else 1 if c.startswith('A') or c == '2S' else 0 for c in m.table),
            len(m.table), -len(m.hand)))

    # Evaluate rewards and exposure using only the computer's cards and public
    # information. Never inspect the human hand or the order of the stock.
    p = current.player
    visible = set(current.hands[p] + current.table + current.piles[0] + current.piles[1])
    unseen = set(CARDS) - visible
    def worth(card):
        return (0.25 + (0.35 if card.endswith('S') else 0)
                + (1 if card.startswith('A') or card == '2S' else 0)
                + (2 if card == '10D' else 0))

    def evaluate(move):
        remaining = set(current.table) - move.table
        if not move.table:
            remaining |= move.hand
        reward = sum(worth(c) for c in move.hand | move.table) if move.table else 0
        if move.table and not remaining:
            reward += 1.5
        # For each possible unseen single card, estimate the best capture
        # it could make from the resulting table (sums up to a king).
        best = {0: 0.0}
        for card in sorted(remaining):
            for total, points in list(best.items()):
                target = total + value(card)
                if target <= 13:
                    best[target] = max(best.get(target, 0), points + worth(card))
        exposure = sum(best.get(value(c), 0) for c in unseen) / max(1, len(unseen))
        total = sum(map(value, remaining))
        sweep_risk = sum(value(c) == total for c in unseen) / max(1, len(unseen)) if remaining else 0
        return reward - 1.8 * exposure - 2 * sweep_risk - 0.12 * len(move.hand)
    return max(moves, key=evaluate)


def computer():
    global state
    while state.player == 1 and not deal_over(state):
        move = choose_computer_move(state, difficulty)
        record(move, 'Computer')
        state = play(state, move)


def snapshot():
    done = deal_over(state)
    return dict(hand=state.hands[0], opponent=len(state.hands[1]), table=state.table,
                stock=len(state.talon), piles=[len(p) for p in state.piles],
                sweeps=state.sweeps, points=score(state), over=done,
                player=state.player, history=history[-10:], difficulty=difficulty,
                moves=[dict(hand=sorted(m.hand), table=sorted(m.table)) for m in legal_moves(state)] if not done else [])


class Handler(BaseHTTPRequestHandler):
    def reply(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == '/api/state':
            with lock:
                self.reply(snapshot())
        elif self.path == '/':
            body = Path(__file__).with_name('index.html').read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_error(404)

    def do_POST(self):
        global state, difficulty
        # Accept browser requests only from this local table.
        origin = self.headers.get('Origin')
        if origin and origin != 'http://' + self.headers.get('Host', ''):
            self.reply({'error': 'Request from another site rejected.'}, 403)
            return
        with lock:
            try:
                if self.path == '/api/new':
                    cards = list(CARDS)
                    random.shuffle(cards)
                    state = new_deal(cards)
                    history.clear()
                elif self.path in ('/api/play', '/api/difficulty'):
                    length = int(self.headers.get('Content-Length', '0'))
                    if not 0 < length < 4096:
                        raise ValueError('Invalid request.')
                    data = json.loads(self.rfile.read(length))
                    if self.path == '/api/difficulty':
                        level = data.get('difficulty')
                        if level not in ('easy', 'medium', 'hard'):
                            raise ValueError('Unknown difficulty level.')
                        difficulty = level
                        self.reply(snapshot())
                        return
                    if state.player != 0:
                        raise ValueError('Please wait for your turn.')
                    move = Move(frozenset(data['hand']), frozenset(data['table']))
                    following = play(state, move)
                    record(move, 'You')
                    state = following
                    computer()
                else:
                    self.reply({'error': 'Unknown request.'}, 404)
                    return
                self.reply(snapshot())
            except (ValueError, KeyError, TypeError) as exc:
                self.reply({'error': str(exc)}, 400)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--no-browser', action='store_true')
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()
    cards = list(CARDS)
    random.shuffle(cards)
    state = new_deal(cards)
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    address = f'http://127.0.0.1:{args.port}'
    print(f'Cassino: {address} (stop: Ctrl+C)', flush=True)
    if not args.no_browser:
        threading.Timer(0.8, lambda: webbrowser.open(address)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
