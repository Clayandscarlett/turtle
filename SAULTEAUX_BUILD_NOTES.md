# Tatawaw Teachings — first playable slice

This is the first offline Saulteaux prototype. Serve this folder over a local
HTTP server so the service worker can cache the build:

```sh
python3 -m http.server 8080
```

Then open `http://localhost:8080/index.html`.

The prototype includes the original loading screen, dedication scroll, seven
unlocked worlds, Turtle Island canvas, Makwa movement, eagle guidance, visual
rounds, touch controls, and the 300-entry source roster. Language entries are
read from `saulteaux-300-word-roster.csv`; no network runtime dependency is
required after the service worker has cached the files.

## Artwork-first playable shell

`index.html` is now the complete self-contained playable game entry point. It
embeds the same shell, approved artwork, wave frames, and 300-row roster so the
ChatGPT single-file preview cannot get stuck waiting for a sibling asset folder.
`saulteaux-game-shell.html` is also self-contained so opening that file directly
in a single-file preview is playable. `saulteaux-game-shell-folder.html` keeps
the smaller folder-based source build for local development. The shell uses the approved
GBA Turtle Island master map, exact seven camera crops, chroma-keyed Makwa and
eagle sheets, the turquoise/teal wave frames, and the first four 20-cell object
atlases. It keeps all seven worlds open from the start, uses the dedication
scroll, and implements find rounds followed by a visual Saulteaux quiz round.

The control deck is safe-area aware: the D-pad sits in the lower-left corner,
the diagonal B-lower-left/A-upper-right cluster sits in the lower-right corner,
and the prompt panel is lifted above the control dock so the controls never
cover the reading prompt. Touch, pointer, keyboard arrows, and WASD are
supported without iPhone long-press selection or copy/paste callouts.

The folder-based shell loads its art from `saulteaux-preview/assets/`; the
self-contained root entry does not need that folder at runtime. Both are cached
by the updated root `sw.js` service worker. Open the self-contained game through
a local static server:

```sh
python3 -m http.server 8080
```

Then visit `http://localhost:8080/index.html`.
