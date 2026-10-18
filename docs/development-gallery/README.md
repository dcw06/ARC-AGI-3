# Level-1 development board gallery

Static GitHub Pages gallery of the six retained initial development observations:
ls20, s5i5, cd82, ft09, ka59 and sc25. Images are byte-identical copies of the
plain 448 x 448 PNGs used in the perception tests. `boards.json` records their
SHA256 identities. Each original 64 x 64 cell occupies a uniform 7 x 7 block.

Open `index.html`, or serve this directory with:

```sh
python -m http.server 8780 --bind 127.0.0.1
```

Click a board to enlarge it. Hover to inspect original board coordinates; tap
the enlarged board on touch devices. Arrow keys navigate the enlarged gallery,
and Escape closes it. Images and downloads work without JavaScript; enlargement
and coordinates use the local script. No external fonts, scripts or model calls
are required.

Local CPU-only Chrome verification passed 17 checks at desktop and mobile
viewports: all six images load, coordinates map to the correct cells, dialog
navigation and focus restoration work, downloads match the selected board, and
the gallery has no horizontal overflow. All six image digests match the retained
test-input manifest.

The publication branch `gh-pages` contains only this directory's contents and
is the GitHub Pages source at `/`. The research branch keeps the maintained
source in `docs/development-gallery/`. Publish updates by copying this directory
to a clean publication checkout and committing to `gh-pages`; do not publish
the repository root or private evidence folders.

Game visuals belong to the ARC-AGI-3 / ARC Prize development games. This gallery
documents research inputs; it is not an official game player. Reference answers,
annotation masks and model predictions are not part of this gallery.
