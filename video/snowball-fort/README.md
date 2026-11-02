# Snowball Fort – 3D "life-hack short" pipeline

An original 9:16 short built in the style of the reference video (a 3D-animated how-to/hack short).

## Style breakdown of the reference
- 720x1280, 29.97 fps, ~42 s, continuous male voiceover over a light music bed, ~-14 LUFS.
- Look: photoreal/Pixar-like 3D render on a seamless **teal-cyan studio backdrop** – radial glow behind
  the subject, horizon ~45% down, darker steel-blue floor. Final third moves to a real location (night street).
- Camera: almost no hard cuts; constant push-ins/orbits, whip-pans and **white bloom-flash** transitions.
- Captions: 1–3 words at a time, bold white Verdana-style sans with thin black outline + soft shadow,
  centred at ~78% of frame height, synced word-by-word to the narration.
- Story beats: hook line → build steps on the blue stage (one object per beat) → payoff in the real world → punchline.

## Pipeline
1. `tts.py <dir>` – Kokoro TTS (`am_michael`), one clip per line → `vo.wav` + `timing.json`.
   Model files: kokoro-onnx GitHub release `model-files-v1.0` (`kokoro-v1.0.onnx`, `voices-v1.0.bin`) in `<dir>/voice/`.
2. `music.py <dir> 40` – procedural pizzicato/glock music bed + whoosh SFX.
3. `scenes.py <shot> <dir>/rend anim 16 0.75` – builds each shot in Blender (`pip install bpy`) from primitives:
   stylised 3D kids, teal studio stage, snow-brick fort, noodle ramp, bungee slingshot, periscope, snowy backyard.
   `render_all.sh` renders all 15 shots (~8 s/frame on 4 CPU cores, ~1100 frames).
4. `render.py <dir> out.mp4` – Ken-Burns camera moves, flash/whip transitions, captions.
5. `sfx.py <dir>` + `mix.sh <dir> out.mp4 final.mp4` – whooshes on whip-pans, shimmer on flash cuts, splat on the hit; voice normalised to -15 LUFS over a quiet music bed.
