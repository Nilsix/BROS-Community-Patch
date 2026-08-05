/* =====================================================================
 *  dinput8.dll  (proxy loader + patch-only matchmaking)
 *  BLEACH: Rebirth of Souls
 * ---------------------------------------------------------------------
 *  The game statically imports dinput8.dll!DirectInput8Create, so placing
 *  this file in the game folder makes the GAME load it into its own
 *  process. We forward every dinput8 export to the real system dinput8
 *  (so input works exactly as before) and, on load, install the Steam
 *  matchmaking hook so patched players only match players using the same
 *  match code.
 *
 *  Match code: read from  patch_ranked.txt  (line 1) next to the game exe.
 *  Log:        patch_ranked.log  next to the game exe.
 * ---------------------------------------------------------------------
 *  CANONICAL MERGED SOURCE -- 2026-08-05.
 *  Four divergent copies of this file existed (game dir, Patch/,
 *  Patch_Dev_Environment/, and the community-patch repo) and each was
 *  missing patches the others had. This file is the union of all four and
 *  is the ONLY one that should be edited from now on. It contains:
 *      Steam matchmaking hook   (patch-only pool + worldwide region)
 *      patch_version_string     title -> "ReBalance <ver>"
 *      patch_yamamoto_selfcost  sublimation-Kikon 2-konpaku self-cost -> 0
 *      patch_byakuya_evo_icon   Pl22 stance icon kept visible in evo
 *      patch_aizen_kikon_counter  Kikon Counter costs 5 flames only
 *      patch_aizen_flamecost    Aizen SP1 costs 1 (base) / 3 (evo) flames
 *  Rebuild with build_dinput8.bat and check patch_ranked.log for one line
 *  per patch. See the header of each patch_* function for its anchors.
 * ===================================================================== */

#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>

#define PATCH_ISSUER_DEFAULT 700001
#define ENABLE_LOG 1

/* ---------- shared helpers ------------------------------------------- */
static void exe_dir_path(const char* name, char* out, size_t n)
{
    char exe[MAX_PATH];
    DWORD len = GetModuleFileNameA(NULL, exe, MAX_PATH);
    while (len > 0 && exe[len-1] != '\\' && exe[len-1] != '/') len--;
    exe[len] = 0;
    snprintf(out, n, "%s%s", exe, name);
}
static void log_line(const char* fmt, ...)
{
#if ENABLE_LOG
    char path[MAX_PATH], buf[512];
    SYSTEMTIME t; GetLocalTime(&t);
    va_list ap; va_start(ap, fmt);
    vsnprintf(buf, sizeof(buf), fmt, ap); va_end(ap);
    exe_dir_path("patch_ranked.log", path, sizeof(path));
    FILE* f = fopen(path, "a");
    if (f) { fprintf(f, "[%02d:%02d:%02d.%03d] %s\n",
                     t.wHour,t.wMinute,t.wSecond,t.wMilliseconds, buf); fclose(f); }
#else
    (void)fmt;
#endif
}

/* ================= PART 1: dinput8 proxy (forward to real) =========== */
static HMODULE g_real_dinput8 = NULL;
static void ensure_real_dinput8(void)
{
    if (!g_real_dinput8) {
        char p[MAX_PATH];
        UINT n = GetSystemDirectoryA(p, MAX_PATH);
        snprintf(p + n, sizeof(p) - n, "\\dinput8.dll");
        g_real_dinput8 = LoadLibraryA(p);
        if (!g_real_dinput8) log_line("PROXY ERROR: could not load real dinput8 at %s", p);
    }
}
static FARPROC real_proc(const char* name)
{
    ensure_real_dinput8();
    return g_real_dinput8 ? GetProcAddress(g_real_dinput8, name) : NULL;
}

__declspec(dllexport) HRESULT WINAPI DirectInput8Create(void* hinst, DWORD ver, const void* riid, void** out, void* outer)
{
    static HRESULT (WINAPI *fn)(void*,DWORD,const void*,void**,void*) = NULL;
    if (!fn) fn = (HRESULT (WINAPI*)(void*,DWORD,const void*,void**,void*))real_proc("DirectInput8Create");
    if (!fn) return 0x80004005; /* E_FAIL */
    return fn(hinst, ver, riid, out, outer);
}
/* The game only imports DirectInput8Create; every later input call goes to the
   real dinput8 COM object this returns, so no other exports are needed. */

/* ================= PART 2: Steam matchmaking hook ===================
 *  DO NOT REMOVE OR WEAKEN THIS SECTION. It is what keeps patched players
 *  in their own matchmaking pool: an unpatched client and a patched client
 *  playing each other desync, so the "issuer" tag/filter and the join guard
 *  are a correctness requirement, not a convenience. Any future edit to this
 *  file must leave PART 2 intact. */
#define VT_REQUEST_LIST    4   /* RequestLobbyList */
#define VT_ADD_NUM_FILTER  6
#define VT_DISTANCE_FILTER 9   /* AddRequestLobbyListDistanceFilter */
#define VT_JOIN_LOBBY      14
#define VT_GET_LOBBY_DATA  19
#define VT_SET_LOBBY_DATA  20

typedef void*         (*SteamMatchmaking_v009_t)(void);
typedef void          (*AddNumFilter_t)(void* self, const char* key, int value, int cmp);
typedef unsigned char (*SetLobbyData_t)(void* self, uint64_t lobby, const char* key, const char* value);
typedef uint64_t      (*JoinLobby_t)(void* self, uint64_t lobby);
typedef const char*   (*GetLobbyData_t)(void* self, uint64_t lobby, const char* key);
typedef uint64_t      (*RequestLobbyList_t)(void* self);
typedef void          (*DistanceFilter_t)(void* self, int eLobbyDistanceFilter);

static AddNumFilter_t o_AddNumFilter = NULL;
static SetLobbyData_t o_SetLobbyData = NULL;
static JoinLobby_t    o_JoinLobby    = NULL;
static RequestLobbyList_t o_RequestLobbyList = NULL;
static void**         g_vt           = NULL;
static int            g_issuer       = PATCH_ISSUER_DEFAULT;
static int            g_block        = 1;
static LONG           g_started      = 0;

static int file_exists(const char* name){ char p[MAX_PATH]; exe_dir_path(name,p,sizeof(p)); FILE* f=fopen(p,"r"); if(f){fclose(f);return 1;} return 0; }

static void load_settings(void)
{
    char path[MAX_PATH], buf[64];
    exe_dir_path("patch_ranked.txt", path, sizeof(path));
    FILE* f = fopen(path, "r");
    if (!f) log_line("WARNING: no patch_ranked.txt; using default code %d", g_issuer);
    else {
        if (fgets(buf,sizeof(buf),f)) {
            int v = atoi(buf);
            if (v!=0 && v!=8 && v!=1 && v!=256) { g_issuer=v; log_line("match code %d loaded", v); }
            else log_line("WARNING: invalid code '%d' (0/1/8/256 reserved); using %d", v, g_issuer);
        }
        fclose(f);
    }
    g_block = file_exists("patch_ranked_logonly.txt") ? 0 : 1;
    if (!g_block) log_line("JOIN guard = LOG-ONLY");
}

static void hk_AddNumFilter(void* self, const char* key, int value, int cmp)
{
    if (key && strcmp(key,"issuer")==0) { log_line("SEARCH: filtering issuer %d -> %d", value, g_issuer); value=g_issuer; }
    o_AddNumFilter(self,key,value,cmp);
}
static unsigned char hk_SetLobbyData(void* self, uint64_t lobby, const char* key, const char* value)
{
    char b[16];
    if (key && strcmp(key,"issuer")==0) { snprintf(b,sizeof(b),"%d",g_issuer); log_line("HOST: tagging issuer %s -> %s", value?value:"(null)", b); value=b; }
    return o_SetLobbyData(self,lobby,key,value);
}
static uint64_t hk_JoinLobby(void* self, uint64_t lobby)
{
    if (g_vt) {
        GetLobbyData_t get = (GetLobbyData_t)g_vt[VT_GET_LOBBY_DATA];
        const char* v = get(self, lobby, "issuer");
        if (v && v[0]) {
            int their = atoi(v);
            int mismatch = (their != g_issuer);
            if (mismatch && g_block) { log_line("JOIN BLOCKED: lobby issuer %d != our code %d (prevents desync)", their, g_issuer); return 0; }
            log_line("JOIN %s: lobby issuer %d (our code %d)", mismatch?"MISMATCH-allowed":"OK", their, g_issuer);
        } else log_line("JOIN: issuer not readable yet -- allowing");
    }
    return o_JoinLobby(self, lobby);
}
static uint64_t hk_RequestLobbyList(void* self)
{
    /* The game never sets a distance filter, so Steam defaults to region-limited
       matching. Force WORLDWIDE (3) before every search so players match across
       regions regardless of their Steam download region. Covers ranked, free
       battle, and room-match browsing (all go through RequestLobbyList). */
    if (g_vt) {
        DistanceFilter_t df = (DistanceFilter_t)g_vt[VT_DISTANCE_FILTER];
        df(self, 3);
        log_line("REGION: forced worldwide distance filter before search");
    }
    return o_RequestLobbyList(self);
}
static int patch_slot(void** vt, int slot, void* hook, void** saved)
{
    DWORD old;
    if (vt[slot]==hook){*saved=NULL;return 1;}
    if (!VirtualProtect(&vt[slot],sizeof(void*),PAGE_READWRITE,&old)) return 0;
    *saved=vt[slot]; vt[slot]=hook; VirtualProtect(&vt[slot],sizeof(void*),old,&old); return 1;
}
static int try_install(void)
{
    HMODULE steam = GetModuleHandleA("steam_api64.dll");
    if (!steam) return 0;
    SteamMatchmaking_v009_t get = (SteamMatchmaking_v009_t)GetProcAddress(steam,"SteamAPI_SteamMatchmaking_v009");
    if (!get) { log_line("ERROR: SteamAPI_SteamMatchmaking_v009 missing"); return -1; }
    void* mm = get(); if (!mm) return 0;
    void** vt = *(void***)mm; if (!vt) return 0;
    g_vt = vt;
    if (!patch_slot(vt,VT_ADD_NUM_FILTER,(void*)&hk_AddNumFilter,(void**)&o_AddNumFilter) ||
        !patch_slot(vt,VT_SET_LOBBY_DATA,(void*)&hk_SetLobbyData,(void**)&o_SetLobbyData) ||
        !patch_slot(vt,VT_JOIN_LOBBY,(void*)&hk_JoinLobby,(void**)&o_JoinLobby) ||
        !patch_slot(vt,VT_REQUEST_LIST,(void*)&hk_RequestLobbyList,(void**)&o_RequestLobbyList)) { log_line("ERROR: vtable patch failed"); return -1; }
    log_line("HOOKS INSTALLED (in game) -- pool code %d, join-guard %s, region=worldwide", g_issuer, g_block?"ON":"log-only");
    return 1;
}
static void patch_version_string(void)
{
    /* Title-screen shows "Ver.<gameversion>". Rename the "Ver." prefix (in the
       game exe's .rdata) to "ReBalance " so patched clients clearly read
       "ReBalance <ver>". Only 12 bytes are free before the next string, so the
       marker is length-limited. This only happens while the DLL is loaded
       (patch mode); vanilla is untouched. */
    unsigned char* mod = (unsigned char*)GetModuleHandleA(NULL);
    if (!mod) return;
    unsigned char* v = mod + 0x14a031c;   /* RVA of the "Ver." title string */
    if (!(v[0]=='V' && v[1]=='e' && v[2]=='r' && v[3]=='.')) {
        log_line("VERSION: 'Ver.' not at expected location (game updated?) -- title rename skipped");
        return;
    }
    static const char repl[] = "ReBalance ";   /* 10 chars + NUL = 11 <= 12 free */
    DWORD old;
    if (VirtualProtect(v, sizeof(repl), PAGE_READWRITE, &old)) {
        memcpy(v, repl, sizeof(repl));
        VirtualProtect(v, sizeof(repl), old, &old);
        log_line("VERSION: title renamed -> 'ReBalance <ver>'");
    }
}
static void patch_yamamoto_selfcost(void)
{
    /* Sublimation-Kikon self-cost removal (exe memory patch).
       At RVA 0x5311FC the game loads xmm1 = 2.0 -- the number of the caster's
       own konpaku (Soul stocks) to spend -- immediately before the single call
       to the sublimation-Kikon self-cost routine (VA 0x1404EB980). Replacing
       that load with 'xorps xmm1,xmm1' (amount = 0) + NOPs makes the cost 0.
       The routine still runs, so the sublimation cutscene is fully preserved,
       and 0x1404EB980 has exactly one caller and sits in no vtable, so nothing
       else in the game reaches it.

         orig:  F3 0F 10 0D 5C F1 F8 00   movss xmm1,[rip+0xF8F15C]   ; =2.0
         new :  0F 57 C9 90 90 90 90 90   xorps xmm1,xmm1 ; nop*5     ; =0.0

       RVA VERIFIED 2026-08-05 against the shipping build: the 8 original bytes
       are present at 0x5311FC in the clean Steam exe (and in Clean_EXE/). The
       "bytes not at expected RVA" line people were seeing in patch_ranked.log
       was NOT a stale RVA -- it was a dev machine whose exe had the same 8
       bytes permanently baked in on disk (the V7_NOSELFCOST static exe), so the
       one-directional memcmp could never match. The guard below now recognises
       the already-patched form and says so instead of crying "game updated?".

       SCOPE CAVEAT (read before re-tuning): the patched instruction lives in
       _Do_call (RVA 0x531140) of a GLOBAL std::function<void(ComponentPtr<
       OPlayableBase>, tsd::string)> installed at static-init (RVA 0x22560).
       Its only filter is  name.find("evo_ct_sp_break02") != npos  &&
       name.find("_maxout") == npos . There is no [fighter+0xC00] character-id
       compare in the lambda or in 0x1404EB980, and 37 pl*.tadjpkg define a
       non-_maxout evo_ct_sp_break02 -- so statically this reads as roster-wide
       (every character's awakened Kikon), not Yamamoto-only. Shipped and
       playtested on Yamamoto (V7/V8); the wider effect has never been checked
       in game. If the awakened Kikon self-cost matters for other characters,
       this needs an id gate rather than an amount edit. */
    unsigned char* mod = (unsigned char*)GetModuleHandleA(NULL);
    if (!mod) return;
    unsigned char* p = mod + 0x5311FC;
    static const unsigned char orig[8] = {0xF3,0x0F,0x10,0x0D,0x5C,0xF1,0xF8,0x00};
    static const unsigned char repl[8] = {0x0F,0x57,0xC9,0x90,0x90,0x90,0x90,0x90};
    if (memcmp(p, repl, 8) == 0) {
        log_line("SELFCOST: already 0 at RVA 0x5311FC (exe pre-patched on disk) -- nothing to do");
        return;
    }
    if (memcmp(p, orig, 8) != 0) {
        log_line("SELFCOST: bytes not at expected RVA 0x5311FC (game updated?) -- skipped");
        return;
    }
    DWORD old;
    if (VirtualProtect(p, 8, PAGE_EXECUTE_READWRITE, &old)) {
        memcpy(p, repl, 8);
        VirtualProtect(p, 8, old, &old);
        FlushInstructionCache(GetCurrentProcess(), p, 8);
        log_line("SELFCOST: sublimation-Kikon self-cost -> 0 (RVA 0x5311FC)");
    } else {
        log_line("SELFCOST: VirtualProtect failed at RVA 0x5311FC");
    }
}
static void patch_byakuya_evo_icon(void)
{
    /* Byakuya (pl022) unique stance icon kept visible in evo -- Pl22-ONLY.
       CORRECTED 2026-07-22 (Aizen/Stark bugfix). The form getter at VA
       0x1402065C0 is a SHARED base-class method: vtable slot 22 of 27 UI
       classes (Pl22 Byakuya AND Pl20 Aizen, Pl33 Stark, ...). Patching its body
       in place forced form=0 for all of them, so Aizen/Stark icons flickered.
       Fix: give ONLY Byakuya's class a private copy of the getter that always
       returns form 0, and repoint just his vtable slot (VA 0x141440678 /
       RVA 0x1440678). Shared method left untouched; all other classes normal. */
    unsigned char* mod = (unsigned char*)GetModuleHandleA(NULL);
    if (!mod) return;
    void**         slot   = (void**)(mod + 0x1440678);   /* Pl22 vtable[22] */
    unsigned char* shared = mod + 0x2065C0;              /* shared getter   */
    static const unsigned char sig[8] = {0x48,0x8B,0x41,0x08,0x48,0x8B,0x88,0x10};
    if ((unsigned char*)*slot != shared || memcmp(shared, sig, 8) != 0) {
        log_line("BYAKUYA_ICON: Pl22 vt[22]/getter not as expected (game updated?) -- skipped");
        return;
    }
    static const unsigned char stub[40] = {
        0x48,0x8B,0x41,0x08, 0x48,0x8B,0x88,0x10,0x01,0x00,0x00,
        0x48,0x85,0xC9, 0x74,0x14, 0x83,0x79,0x08,0x00, 0x74,0x0E,
        0x48,0x8B,0x80,0xF0,0x00,0x00,0x00,
        0x31,0xC0,0x90,0x90,0x90,0x90, 0xC3,
        0x8B,0x40,0x44, 0xC3
    };
    void* code = VirtualAlloc(NULL, sizeof(stub),
                              MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE);
    if (!code) { log_line("BYAKUYA_ICON: VirtualAlloc failed"); return; }
    memcpy(code, stub, sizeof(stub));
    FlushInstructionCache(GetCurrentProcess(), code, sizeof(stub));
    DWORD old;
    if (VirtualProtect(slot, sizeof(void*), PAGE_READWRITE, &old)) {
        *slot = code;
        VirtualProtect(slot, sizeof(void*), old, &old);
        log_line("BYAKUYA_ICON: Pl22-only form getter repointed (icon in evo; Aizen/Stark/others unaffected)");
    } else {
        log_line("BYAKUYA_ICON: VirtualProtect(vtable slot) failed");
    }
}
static void patch_aizen_kikon_counter(void)
{
    /* Aizen (pl020) Kikon Counter now costs the 5 flames ONLY -- Pl20-ONLY.
       The engine calls this mechanic KIKON_COUNTER (string at VA 0x1414700C0,
       three bytes after "ct_reset"); it is the R3+L3 cancel of an opponent's
       Kikon. It is entirely hardcoded: pl020.tadjpkg's 1_normal_ct_ct_reset is
       four blocks of cutscene + invulnerability with no cost, and there is no
       ct_reset node in his tcmb at all.

       Shipped, it also required a FULL reverse gauge and consumed all of it.
       The gauge is two floats on the fighter -- +0x10B0 max, +0x10B4 value --
       drawn as rebirth_gauge1/2/3, i.e. the "bars" players count.

         RVA 0x4F2B6F  76 05                 jbe -> EB 05 jmp   (requirement always passes)
         RVA 0x4F3240  44 89 85 54 02 00 00  mov [rbp+0x254],r8d -> 7-byte nop
         RVA 0x4F3308  E8 43 BA CF FF        call 0x1401EED50    -> 5-byte nop

       Site 2 is the deduction. It sits inside a stack copy of
       self+0xFA0..+0x1340 that is copied straight back, and it is the only
       modification between copy-out and copy-back -- so nopping the single
       store makes the whole copy a no-op.

       Site 3 is the HUD widget, and it is NOT optional. 0x1401EED50 is
       event-driven, not a per-frame resync, so removing the deduction without
       it would empty the DISPLAYED gauge while the value stayed full.

       Left alone deliberately: the flames cost (0x1404F31C3 still zeroes
       UNIQUE_0 at fighter+0x1A34), the once-per-match flag (+0x1A5C), the
       base-form gate, and the shipped blocklist that stops the counter working
       against pl000-pl004 and pl033.

       Pl20-ONLY is proven, not assumed: all three sites are inside 0x1404F2980
       (the gate) and 0x1404F3070 (the executor), whose callers trace back
       through vtables 0x14146D748 / 0x141468C88 to constructors reachable only
       from pl020's behaviour slot at 0x1418E1130. */
    unsigned char* mod = (unsigned char*)GetModuleHandleA(NULL);
    if (!mod) return;

    unsigned char* gate = mod + 0x4F2B6F;   /* jbe  -> jmp */
    unsigned char* dedu = mod + 0x4F3240;   /* mov  -> nop */
    unsigned char* hud  = mod + 0x4F3308;   /* call -> nop */

    static const unsigned char sig_gate[2] = {0x76,0x05};
    static const unsigned char sig_dedu[7] = {0x44,0x89,0x85,0x54,0x02,0x00,0x00};
    static const unsigned char sig_hud [5] = {0xE8,0x43,0xBA,0xCF,0xFF};

    static const unsigned char rep_gate[2] = {0xEB,0x05};                          /* jmp +5        */
    static const unsigned char rep_dedu[7] = {0x0F,0x1F,0x80,0x00,0x00,0x00,0x00}; /* nop dword[rax]*/
    static const unsigned char rep_hud [5] = {0x0F,0x1F,0x44,0x00,0x00};           /* nop dword[rax+rax] */

    /* Some dev installs run an exe that already has these three sites baked in
       on disk. Recognise that instead of reporting it as a game update -- the
       mechanic is live either way and there is nothing to write. */
    if (memcmp(gate, rep_gate, sizeof(rep_gate)) == 0 &&
        memcmp(dedu, rep_dedu, sizeof(rep_dedu)) == 0 &&
        memcmp(hud,  rep_hud,  sizeof(rep_hud))  == 0) {
        log_line("AIZEN_COUNTER: already applied (exe pre-patched on disk) -- nothing to do");
        return;
    }

    /* All three or none -- a half-patched counter would deduct without paying
       back, or drain the gauge with the requirement already lifted. */
    if (memcmp(gate, sig_gate, sizeof(sig_gate)) != 0 ||
        memcmp(dedu, sig_dedu, sizeof(sig_dedu)) != 0 ||
        memcmp(hud,  sig_hud,  sizeof(sig_hud))  != 0) {
        log_line("AIZEN_COUNTER: sites not as expected (game updated?) -- skipped, cost unchanged");
        return;
    }

    struct { unsigned char* at; const unsigned char* to; SIZE_T n; } w[3] = {
        { gate, rep_gate, sizeof(rep_gate) },
        { dedu, rep_dedu, sizeof(rep_dedu) },
        { hud,  rep_hud,  sizeof(rep_hud)  },
    };
    for (int i = 0; i < 3; i++) {
        DWORD old;
        if (!VirtualProtect(w[i].at, w[i].n, PAGE_EXECUTE_READWRITE, &old)) {
            log_line("AIZEN_COUNTER: VirtualProtect failed at site %d -- PARTIAL, expect odd costs", i);
            return;
        }
        memcpy(w[i].at, w[i].to, w[i].n);
        VirtualProtect(w[i].at, w[i].n, old, &old);
    }
    FlushInstructionCache(GetCurrentProcess(), gate, 1);
    log_line("AIZEN_COUNTER: Pl20-only -- Kikon Counter now costs 5 flames only (reverse gauge free)");
}

/* ================= Aizen (pl020) SP1 flame cost ======================
 *  sp_atk01 consumes flames: 1 (base) / 3 (evo). SP2 untouched.
 *  We detour Aizen's own per-frame unique-action handler (VA 0x140148970 /
 *  RVA 0x148970). It self-filters by action name; we add an sp_atk01 branch.
 *    combat  = [rcx+0x20];  char-id [combat+0xC00]==0x14 (20=Aizen)
 *    flames  = float [combat+0x1A34]      (0..5, confirmed via CE)
 *  Handler runs every frame -> edge-detect so we subtract once per activation.
 *  The char-id test inside the hook is what makes this Pl20-only, so it is
 *  safe even if the handler is ever shared.
 *  Anchors + derivation: Patched Aizen/V6/. */
#define AIZEN_UNIQ_RVA   0x148970
#define AIZEN_CHARID_OFF 0xC00
#define AIZEN_ID         0x14
#define AIZEN_FLAME_OFF  0x1A34
#define AIZEN_COST_BASE  1.0f
#define AIZEN_COST_EVO   3.0f

typedef long long (*aizen_uniq_t)(void* rcx, void* rdx, void* r8, void* r9);
static aizen_uniq_t o_aizen_uniq = NULL;   /* -> trampoline (stolen bytes + jmp back) */
static void* g_af_obj[2] = {0,0};          /* per-instance edge state (P1/P2) */
static int   g_af_in [2] = {0,0};

static int af_action_is(void* actctx, const char* want)
{
    if (!actctx) return 0;
    unsigned long long cap = *(unsigned long long*)((char*)actctx + 24);
    const char* s = (cap >= 16) ? *(const char**)actctx : (const char*)actctx;
    if (!s) return 0;
    int i = 0;
    for (; want[i]; ++i) if (s[i] != want[i]) return 0;
    return s[i] == '\0';
}

static long long hk_aizen_uniq(void* rcx, void* rdx, void* r8, void* r9)
{
    void* combat = rcx ? *(void**)((char*)rcx + 0x20) : NULL;
    if (combat && *(int*)((char*)combat + AIZEN_CHARID_OFF) == AIZEN_ID) {
        int base = af_action_is(rdx, "sp_atk01");
        int evo  = base ? 0 : af_action_is(rdx, "evo_sp_atk01");
        int slot = (g_af_obj[0]==combat) ? 0 : (g_af_obj[1]==combat) ? 1
                 : (g_af_obj[0]==NULL)   ? 0 : 1;
        g_af_obj[slot] = combat;
        if (base || evo) {
            if (!g_af_in[slot]) {                /* rising edge = SP1 activation */
                g_af_in[slot] = 1;
                float  cost  = evo ? AIZEN_COST_EVO : AIZEN_COST_BASE;
                float* flame = (float*)((char*)combat + AIZEN_FLAME_OFF);
                float  f     = *flame - cost;
                if (f < 0.0f) f = 0.0f;           /* clamp; hard-block = phase 2 */
                *flame = f;
                log_line("AIZEN_FLAME: sp_atk01(%s) -%.0f -> %.1f flames",
                         evo ? "evo" : "base", cost, f);
            }
        } else {
            g_af_in[slot] = 0;                    /* left the move -> re-arm */
        }
    }
    return o_aizen_uniq(rcx, rdx, r8, r9);        /* always run the original */
}

static void patch_aizen_flamecost(void)
{
    unsigned char* mod = (unsigned char*)GetModuleHandleA(NULL);
    if (!mod) return;
    unsigned char* entry = mod + AIZEN_UNIQ_RVA;
    /* 13-byte position-independent prologue: mov [rsp+10],rbx / push rdi / sub rsp,0xD0 */
    static const unsigned char expect[13] = {
        0x48,0x89,0x5C,0x24,0x10, 0x57, 0x48,0x81,0xEC,0xD0,0x00,0x00,0x00
    };
    if (o_aizen_uniq) { log_line("AIZEN_FLAME: already installed -- skipped"); return; }
    if (memcmp(entry, expect, sizeof expect) != 0) {
        log_line("AIZEN_FLAME: prologue moved (game update?) -- skipped");
        return;
    }
    unsigned char* tramp = (unsigned char*)VirtualAlloc(
        NULL, 64, MEM_COMMIT|MEM_RESERVE, PAGE_EXECUTE_READWRITE);
    if (!tramp) { log_line("AIZEN_FLAME: VirtualAlloc failed"); return; }
    memcpy(tramp, entry, 13);                                    /* stolen prologue */
    unsigned long long ret = (unsigned long long)(entry + 13);
    tramp[13]=0x48; tramp[14]=0xB8; memcpy(tramp+15,&ret,8);     /* mov rax,entry+13 */
    tramp[23]=0xFF; tramp[24]=0xE0;                              /* jmp rax          */
    FlushInstructionCache(GetCurrentProcess(), tramp, 64);
    o_aizen_uniq = (aizen_uniq_t)tramp;

    unsigned char patch[13];
    unsigned long long hk = (unsigned long long)&hk_aizen_uniq;
    patch[0]=0x48; patch[1]=0xB8; memcpy(patch+2,&hk,8);         /* mov rax,&hk      */
    patch[10]=0xFF; patch[11]=0xE0; patch[12]=0x90;              /* jmp rax ; nop    */
    DWORD old;
    if (VirtualProtect(entry, 13, PAGE_EXECUTE_READWRITE, &old)) {
        memcpy(entry, patch, 13);
        VirtualProtect(entry, 13, old, &old);
        FlushInstructionCache(GetCurrentProcess(), entry, 13);
        log_line("AIZEN_FLAME: installed at RVA 0x%X (flame off 0x%X)",
                 AIZEN_UNIQ_RVA, AIZEN_FLAME_OFF);
    } else {
        o_aizen_uniq = NULL;
        log_line("AIZEN_FLAME: VirtualProtect failed");
    }
}

static DWORD WINAPI worker(LPVOID u)
{
    (void)u;
    log_line("==== dinput8 proxy loaded INTO GAME (pid %lu) ====", GetCurrentProcessId());
    load_settings();
    patch_version_string();
    patch_yamamoto_selfcost();
    /* patch_byakuya_evo_icon() repoints Pl22's vtable slot 22 (RVA 0x1440678)
       to a private form-getter stub. The Sakura Gauge hook under development
       writes to that SAME slot, so while testing the gauge, comment this call
       out locally -- but it MUST stay enabled in anything that ships, or a
       dev->live push silently removes Byakuya's evo icon (which is exactly how
       it went missing once already). */
    patch_byakuya_evo_icon();
    patch_aizen_kikon_counter();
    patch_aizen_flamecost();
    for (int i=0;i<600;i++){ int r=try_install(); if(r==1)return 0; if(r<0)return 0; Sleep(500); }
    log_line("ERROR: steam_api64/matchmaking never appeared -- is this the game process?");
    return 0;
}

BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID res)
{
    (void)res;
    if (reason==DLL_PROCESS_ATTACH) {
        if (InterlockedCompareExchange(&g_started,1,0)==0) {
            DisableThreadLibraryCalls(h);
            CreateThread(NULL,0,worker,NULL,0,NULL);
        }
    }
    return TRUE;
}
