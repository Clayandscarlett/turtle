# Tatawaw Teachings — first playable slice

This is the first offline Saulteaux prototype. Serve this folder over a local
HTTP server so the service worker and roster CSV can load:

```sh
python3 -m http.server 8080
```

Then open `http://localhost:8080/saulteaux-game.html`.

The prototype includes the original loading screen, dedication scroll, seven
unlocked worlds, Turtle Island canvas, Makwa movement, eagle guidance, visual
rounds, touch controls, and the 300-entry source roster. Language entries are
read from `saulteaux-300-word-roster.csv`; no network runtime dependency is
required after the service worker has cached the files.

## Artwork-first playable shell

`saulteaux-game-shell.html` is the next build checkpoint. It uses the approved
GBA Turtle Island master map, exact seven camera crops, chroma-keyed Makwa and
eagle sheets, the turquoise/teal wave frames, and the first four 20-cell object
atlases. It keeps all seven worlds open from the start, uses the dedication
scroll, and implements find rounds followed by a visual Saulteaux quiz round.

The shell loads its art from `saulteaux-preview/assets/` and is cached by the
updated root `sw.js` service worker. Open it through a local static server:

```sh
python3 -m http.server 8080
```

Then visit `http://localhost:8080/saulteaux-game-shell.html`.
