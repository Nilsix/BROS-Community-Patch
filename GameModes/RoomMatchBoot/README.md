# RoomMatchBoot — boot straight into the online room-match menu

Start it with **`Quick Launch Room Match.py`**. The game goes logos → Room Match
(Create room / Find room).

**Getting in works.** See the known bug below for getting back out.

## What it patches

Same handoff as `TrainingBoot` (RVA `0x750C72`), aimed at
`JUMP_RoomMatchMenu`. Where Training needs the setup singleton's mode written,
room match does not: its real issuer writes no mode, because by then the online
menu has already chosen, and the choice lives in a selector at `0x141CDF2E8`
(0 rank, 1 room match, 2 free). The loader writes **1** there and jumps.

## ⚠ KNOWN BUG: Return does not land on the ONLINE menu

Pressing Return from the room-match menu lands on the Story screen, which then
ignores Return until Confirm is pressed once. Story text can also bleed over the
Online menu afterwards.

**Cause, and it is understood.** The flow's transitions are *events*, and the
prefix says what they do: `MOVE_PUSH_*` **stacks** the current state so `BACK_*`
can unwind it, while `JUMP_*` **replaces** it. Every menu navigates with
`MOVE_PUSH_ROOMMATCH`; this shortcut sends `JUMP_RoomMatchMenu`, so it arrives
at the right screen with nothing underneath, and Return unwinds an empty stack.

The fix is to drive the flow's own events instead of jumping — leave the boot
handoff alone and send `MOVE_PUSH_ONLINE` then `MOVE_PUSH_ROOMMATCH` from the
live state handlers. Not done yet.

Everything else about the shortcut works, which is why it ships as-is.

## The loader

Built from this repo's `Files/Matchmaking/dinput8_proxy.c` with `-DENABLE_BOOT_ROOMMATCH=1`, so it is
the normal patch loader plus this one shortcut — same matchmaking, same patches,
same balance data. It is **not** a game mode: there is no `Script/`, and it does
not appear in the launcher's game-mode list.

`setup_matchmaking()` installs `GameModes/<name>/dinput8.dll` when the selected
name has one, so nothing else is wired.

⚠ **Rebuild it whenever the default loader is rebuilt**, or the two drift.

## No pool tag

It changes which scene the boot flow hands off to and nothing else, so a player
using the shortcut simulates identically to one launching normally and lands in
the same matchmaking pool. That is deliberate.
