"""Hungarian two-player Cassino. Pure, immutable game transitions."""
from dataclasses import dataclass
from itertools import combinations

RANKS = ('A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K')
CARDS = tuple(r + s for s in 'SHDC' for r in RANKS)


def value(card):
    if card not in CARDS:
        raise ValueError('Unknown card')
    return RANKS.index(card[:-1]) + 1


@dataclass(frozen=True)
class Move:
    hand: frozenset
    table: frozenset


@dataclass(frozen=True)
class State:
    hands: tuple
    table: tuple
    talon: tuple
    piles: tuple = ((), ())
    sweeps: tuple = (0, 0)
    player: int = 0
    last_capturer: int | None = None
    first: int = 0


def new_deal(deck, first=0):
    deck = tuple(deck)
    if len(deck) != 52 or set(deck) != set(CARDS) or first not in (0, 1):
        raise ValueError('A deal needs all 52 distinct cards and player 0 or 1')
    hands = [(), ()]
    hands[first], hands[1-first] = deck[:3], deck[3:6]
    return State(tuple(hands), deck[6:10], deck[10:], player=first, first=first)


def deal_over(state):
    return not any(state.hands) and not state.talon and not state.table


def legal_moves(state):
    if deal_over(state):
        return []
    hand = state.hands[state.player]
    moves = [Move(frozenset((c,)), frozenset()) for c in hand]
    subsets = []
    for n in range(1, len(hand)+1):
        for cards in combinations(hand, n):
            subsets.append((frozenset(cards), sum(map(value, cards))))
    if not subsets:
        return moves
    # Positive values allow pruning; avoid enumerating the full table powerset.
    targets = {total for _, total in subsets}
    by_total = {t: [] for t in targets}
    table = state.table
    def visit(start, total, chosen):
        if total in targets:
            by_total[total].append(frozenset(chosen))
        for i in range(start, len(table)):
            following = total + value(table[i])
            if following <= max(targets):
                visit(i+1, following, chosen + (table[i],))
    visit(0, 0, ())
    for cards, total in subsets:
        moves.extend(Move(cards, capture) for capture in by_total[total])
    return moves


def play(state, move):
    p = state.player
    if deal_over(state) or not move.hand or not move.hand <= set(state.hands[p]) or not move.table <= set(state.table):
        raise ValueError('These cards cannot be played')
    if move.table:
        if sum(map(value, move.hand)) != sum(map(value, move.table)):
            raise ValueError('The selected card totals must match')
    elif len(move.hand) != 1:
        raise ValueError('Place exactly one card')
    hands = list(state.hands)
    played = tuple(c for c in hands[p] if c in move.hand)
    hands[p] = tuple(c for c in hands[p] if c not in move.hand)
    piles, sweeps = list(state.piles), list(state.sweeps)
    last = state.last_capturer
    table = tuple(c for c in state.table if c not in move.table)
    if move.table:
        piles[p] += played + tuple(c for c in state.table if c in move.table)
        last = p
        if not table:
            sweeps[p] += 1
    else:
        table += played
    # On an empty table the opening placement is followed by another move.
    following = p if not state.table else 1-p
    talon = state.talon
    if not any(hands):
        if talon:
            following = last if last is not None else state.first
            hands[following], hands[1-following] = talon[:3], talon[3:6]
            talon = talon[6:]
        else:
            recipient = last if last is not None else state.first
            piles[recipient] += table
            table = ()
    elif not hands[following]:
        following = 1-following
    return State(tuple(hands), table, talon, tuple(piles), tuple(sweeps), following, last, state.first)


def score(state):
    return tuple((3 if len(pile) >= 27 else 0)
                 + (2 if sum(c.endswith('S') for c in pile) >= 7 else 0)
                 + sum(c.startswith('A') for c in pile)
                 + (2 if '10D' in pile else 0) + (1 if '2S' in pile else 0)
                 + state.sweeps[p] for p, pile in enumerate(state.piles))
