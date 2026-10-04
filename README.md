# LiteLDev/.github

Org profile for [github.com/LiteLDev](https://github.com/LiteLDev).

- `profile/README.md` — the page GitHub shows on the org's overview tab.
- `profile/levimc-portfolio-{dark,light}.svg` — 48 s looping banner (pure SVG + SMIL, no JS), one per colour scheme;
  the README picks one with `<picture>` + `prefers-color-scheme`, so it follows the viewer's GitHub/system theme.
- `tools/gen_portfolio.py` — generates the banner. All 3D (voxel island, particle block, devices, repo constellation,
  leaf vortex) is projected in Python and baked into keyframes. Edit the numbers/scenes there, then rebuild both themes
  (or one, with `THEME=dark|light`):

```bash
python3 tools/gen_portfolio.py
```
