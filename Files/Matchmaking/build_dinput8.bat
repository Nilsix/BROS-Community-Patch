@echo off
rem =====================================================================
rem  Rebuild dinput8.dll from dinput8_proxy.c
rem
rem  The shipped DLL is a Mingw-w64 build (its .rdata carries the
rem  "Mingw-w64 runtime failure:" string and it has a .buildid section),
rem  so use the same toolchain -- an MSVC build would still work but would
rem  change the binary's shape for no reason.
rem
rem  Get the toolchain from https://www.msys2.org  then, in an MSYS2 shell:
rem      pacman -S mingw-w64-x86_64-gcc
rem  or install w64devkit and put its bin/ on PATH.
rem
rem  Run this from this folder. Output lands here, next to the source, and
rem  the installer copies it to the game dir from "Files\Matchmaking".
rem =====================================================================
setlocal
cd /d "%~dp0"

where x86_64-w64-mingw32-gcc >nul 2>nul
if errorlevel 1 (
    echo.
    echo   x86_64-w64-mingw32-gcc is not on PATH.
    echo.
    echo   Install MSYS2 ^(https://www.msys2.org^) then:
    echo       pacman -S mingw-w64-x86_64-gcc
    echo   and add C:\msys64\mingw64\bin to PATH.
    echo.
    exit /b 1
)

echo Building dinput8.dll ...
x86_64-w64-mingw32-gcc ^
    -shared -O2 -municode -DNDEBUG ^
    -o dinput8.dll dinput8_proxy.c ^
    -Wl,--out-implib,dinput8_proxy.lib ^
    -static-libgcc ^
    -lkernel32 -luser32

if errorlevel 1 (
    echo.
    echo   BUILD FAILED -- dinput8.dll was NOT replaced.
    exit /b 1
)

echo.
echo   Built dinput8.dll
echo.
echo   Sanity check before shipping: launch the game with it in place and
echo   read patch_ranked.log next to the game exe. You should see a line
echo   for every patch, e.g.
echo.
echo       AIZEN_COUNTER: Pl20-only -- Kikon Counter now costs 5 flames only
echo.
echo   If a line instead says "(game updated?) -- skipped", the game build
echo   moved and that patch's RVAs need re-finding. The DLL verifies a byte
echo   signature at every site first, so a mismatch is a clean skip, never
echo   a crash.
echo.
endlocal
