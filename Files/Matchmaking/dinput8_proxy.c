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

/* ================= PART 2: Steam matchmaking hook =================== */
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

    /* All three or none -- a half-patched counter would deduct without paying
       back, or drain the gauge with the requirement already lifted. */
    if (memcmp(gate, sig_gate, sizeof(sig_gate)) != 0 ||
        memcmp(dedu, sig_dedu, sizeof(sig_dedu)) != 0 ||
        memcmp(hud,  sig_hud,  sizeof(sig_hud))  != 0) {
        log_line("AIZEN_COUNTER: sites not as expected (game updated?) -- skipped, cost unchanged");
        return;
    }

    static const unsigned char rep_gate[2] = {0xEB,0x05};                          /* jmp +5        */
    static const unsigned char rep_dedu[7] = {0x0F,0x1F,0x80,0x00,0x00,0x00,0x00}; /* nop dword[rax]*/
    static const unsigned char rep_hud [5] = {0x0F,0x1F,0x44,0x00,0x00};           /* nop dword[rax+rax] */

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
static DWORD WINAPI worker(LPVOID u)
{
    (void)u;
    log_line("==== dinput8 proxy loaded INTO GAME (pid %lu) ====", GetCurrentProcessId());
    load_settings();
    patch_version_string();
    patch_byakuya_evo_icon();
    patch_aizen_kikon_counter();
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
