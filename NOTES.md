# Cassino — playtesting notes

## Initial request

Build the Hungarian two-player version of Cassino described in the assignment: pass the supplied tests, create a browser table for a complete deal against the computer, and document one startup command. Do not modify the supplied tests.

## Player feedback and requested changes

1. After trying the game, I reported that it went well once I understood the rules. I asked for selectable difficulty levels.
   - The agent added Easy (random legal moves), Medium (prioritizes captures), and Hard (weighs points and opportunities left on the table).
   - Difficulty can change during a deal and applies to the next computer move.
2. I asked for the game and these notes to be in English because this is an English-language course. I also requested graphics for dealing cards.
   - The agent translated the interface, rules, feedback messages, and move history into English.
   - The table now has a visible draw pile and a short card-dealing animation when starting a deal or drawing new hands. Reduced-motion preferences are respected.

## Agent verification

- All 14 original tests passed; tests/test_casino.py remains unchanged.
- Before the translation, automated Edge checks completed a full deal at each difficulty and verified that all 52 cards were collected.
- Difficulty switching preserved the current deal and survived a page refresh. Invalid difficulty values were rejected.
- Selection, clearing, hints, restarting, and the 390-pixel mobile layout were checked without JavaScript errors.
- After translation, an automated Edge test completed another full deal (18 human turns), checked English move history and results, and verified the dealing animation, reduced-motion mode, and mobile width. All 14 original tests still passed.

## Follow-up playtest

After the changes, I tried the game myself. It was easy to understand, and I successfully played through a complete deal against the computer. I reported no further problems or requests for changes in this feedback.
