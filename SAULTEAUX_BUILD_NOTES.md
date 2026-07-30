# Tatawaw Teachings — Cree-parity playable build

`index.html` is the complete, self-contained game. It is not an artwork
preview: the Turtle Island artwork, Makwa and eagle sprite sheets, animated
water, four object atlases, and all 300 roster entries are embedded directly in
that file.

The gameplay structure now follows the Cree game:

- opening/loading flow and local Continue save;
- every world and arena open from the beginning;
- 7 Saulteaux Turtle Island worlds, 50 arenas, and 6 entries per arena;
- an English-supported visual find pass followed by a Saulteaux-only quiz pass;
- Makwa movement, A interaction, B pause, START map, and SELECT journal;
- eagle prompting, wrong-choice guidance, and help after 7 seconds;
- arena completion, replay/next-arena flow, progress tracking, and a 300-entry
  found/mastered word journal;
- touch, keyboard, and gamepad controls in a full-screen, non-stretched layout;
- offline PWA caching through `manifest.webmanifest` and `sw.js`.

The seven camera views are crops of the approved master Turtle Island image, so
changing worlds pans to the corresponding land on the turtle's back rather than
switching to an unrelated background.

## Run

For the installed/offline PWA path, serve the folder over HTTP:

```sh
python3 -m http.server 8080
```

Then open `http://localhost:8080/index.html`.

The self-contained `index.html` also opens without sibling art or roster files.
Because those resources are embedded, the service worker only needs to cache
the standalone entry, manifest, and home-screen icons. The service worker
requires HTTP or HTTPS, as all browsers do.

## Development

- `saulteaux-cree-parity-source.html` is the readable folder-based source.
- `build-saulteaux-parity.mjs` embeds the roster and 16 art assets into
  `index.html` and `saulteaux-game-shell.html`.
- `validate-saulteaux-parity.mjs` checks the campaign, scripts, embedded files,
  and parity-critical controls.
