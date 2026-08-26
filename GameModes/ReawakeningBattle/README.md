# Reawakening Battle — a game mode that ships a loader *and* data

Casual mode. Every character who owns a Reawakening **starts the match already
in it**, and they all field **10 Konpaku**:

| | | `rev_soul_num` |
|---|---|---|
| pl001 | Ichigo Kurosaki (Bankai) — Full Hollowfication | already 10 |
| pl003 | Uryu Ishida — Quincy: Letzt Stil | 9 → **10** |
| pl020 | Sosuke Aizen — Complete Hogyoku Fusion | already 10 |
| pl036 | Ulquiorra Shifar — Resurreccion Segunda Etapa | 9 → **10** |
| pl052 | Yhwach — the Kaiser-level Reawakening | 8 → **10** |

Everyone else plays exactly as before, on their usual 9.

## Two halves, and why

**`dinput8.dll` — the starting form.** Which trigger a Reawakening uses *is*
data (the `ura_transform_mothod` column), but the starting form is not: it is an
argument the engine passes to the fighter's init, and only Training ever sets it
to "Reawakened". So that half is an exe hook.

`setup_matchmaking()` in the launcher installs `GameModes/<mode>/dinput8.dll`
when the selected mode has one, falling back to `Files/Matchmaking/dinput8.dll`
otherwise. It runs last in `launch()`, so the mode's loader wins cleanly rather
than racing the normal one. Any future loader-based mode works the same way —
drop a `dinput8.dll` in its folder, nothing else to wire.

The loader is built from **this repo's** `Files/Matchmaking/dinput8_proxy.c`
with `-DENABLE_REAWAKEN_BATTLE=1`, so it carries exactly the patches the normal
loader here carries — matchmaking, the stage-id gate, the room-match result
menu, the Yamamoto self-cost, Byakuya's evo icon — and PART 13 on top. Nothing
else differs. The roster lives in `g_reaw_ids` there.

It is built with MSVC rather than the mingw recipe in `build_dinput8.bat`, which
is why it is smaller and imports **KERNEL32 only**: `/LD` links the CRT
statically, so unlike the mingw loader it needs no UCRT redistributable.

    cl /nologo /O2 /DNDEBUG /DENABLE_REAWAKEN_BATTLE=1 /W3 /LD dinput8_proxy.c ^
       /Fe:dinput8.dll /link kernel32.lib user32.lib

**`Script/CharaStatus.fsv` — the Konpaku count.** The per-form maximum is plain
data, so this half is an ordinary overlay like every other mode: the same file
the Community Patch ships **in this repo**, with `rev_soul_num` raised to 10 on
the three characters that were below it. Verified by round-trip — 103 of 106
rows are byte-identical to `GameVersions/Bleach Rebirth of Souls Community
Patch/Script/CharaStatus.fsv`, and the three that differ are pl003, pl036 and
pl052.

★ It is built from **this** repo's file on purpose. The dev environment's copy
of the same overlay carries `pl018 evo_fighting_param 3`, where the patch
shipping here has **3.75** — dropping that file in would have silently reverted
a live balance value for anyone playing the mode.

⚠ **Keep the two halves in step.** `g_reaw_ids` and the rows edited here are the
same roster written twice. Adding a character means editing both, or they field
a Reawakening on the wrong Konpaku count.

⚠ **This overlay replaces CharaStatus wholesale**, so it goes stale when the
Community Patch retunes anything in that file. Rebuild it from the current
`GameVersions/Bleach Rebirth of Souls Community Patch/Script/CharaStatus.fsv`
after balance passes — the same caveat applies to BaseOnly, EightKonpakus and
InstantEvoAndSublimation, whose copies have already drifted apart.

## Online

The mode shifts its matchmaking issuer by `REAWAKEN_POOL_TAG` (4001), so it
lands in its **own pool**. That is not a nicety: a client in this mode simulates
a different fight from a normal patched client, and the two would desync if they
met. Everyone in the match needs the mode on.

The mode is not remembered between launcher sessions — the same as the other
game modes — so the next launch reinstalls the normal loader unless you turn it
back on.

There is no way to end up in the mode without meaning to. The game is only ever
started **through the launcher**: `launch_patched()` runs the exe directly on
Windows precisely because starting through Steam makes EasyAntiCheat block the
injected `dinput8.dll`. So every launch goes past the loader install, and
whatever the toggle says at that moment is what you play.

## Status

**The mechanic is confirmed in game**, on the dev environment's build of the
same PART 13: three sessions on 2026-08-25/26 counted fighters actually entering
the match Reawakened — 1, 2, 4, then 6 across matches — with the pool shifting
as designed.

**This repo's build of it has not been played.** It is the same patch function,
ported unchanged except for the name of the trampoline allocator
(`gauge_alloc_near` → `rr_alloc_near`, the equivalent helper that already
existed here), compiled against a different loader. Two things are still
unverified either way:

* **that the Konpaku really read 10.** `rev_soul_num` feeding the Reawakened
  form's maximum is inferred from the column's name and from the transform
  reading a per-form table at `fighter+0xCB8+form*4` — it has not been observed.
  If the count comes out wrong it is one column to move.
* **Yhwach specifically.** His Reawakening is the one the exe forces
  (`ura_transform_mothod` 3, the Kaiser level), and his Kaiser counter has its
  own start-of-match data in `pl052.tadjpkg`. Least exercised path in the mode.

The patch verifies its own anchor before hooking: if the game updates and the
six bytes at RVA 0x4639C1 move, it logs `REAWAKEN: no mov ecx,[rbp+0x670] ...
skipped` and the mode simply does not engage.
