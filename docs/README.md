# Approach deck → PDF

The challenge asks for "a deck/PPT converted into a PDF." Two ready-made sources
are here; both produce the same 12-slide deck.

## Option A — fastest, no tools (recommended)

1. Open **`deck.html`** in any browser (double-click it).
2. Press **Ctrl+P** (Windows) / **Cmd+P** (Mac).
3. Set:
   - **Destination:** *Save as PDF*
   - **Layout:** *Landscape*
   - **Margins:** *None*
   - **Background graphics:** *ON* (so colours/cards print)
4. Save as `docs/RecruiterAI_deck.pdf`.

The HTML is self-contained (no internet needed) and already paginates one slide
per page.

## Option B — Markdown / Marp (editable source)

`PRESENTATION.md` is a [Marp](https://marp.app/) deck. With the Marp CLI:

```bash
npm install -g @marp-team/marp-cli
marp docs/PRESENTATION.md --pdf --allow-local-files -o docs/RecruiterAI_deck.pdf
```

Or use the **Marp for VS Code** extension → "Export slide deck" → PDF.

## What's in the deck

1. Title · 2. The problem · 3. Reading the constraints · 4. Our approach ·
5. Architecture · 6. Data flow · 7. The fit score · 8. Beating the traps ·
9. Signal integration · 10. Technologies used · 11. Results · 12. Thank you.
