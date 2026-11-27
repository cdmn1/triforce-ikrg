#include <gccore.h>
#include <ogc/si.h>
#include <stdio.h>
#include <string.h>

static void *xfb;
static GXRModeObj *rmode;

#define TRIFORCE_RESET_FLAG ((volatile u32 *)0x811FFF00)
#define JVS_P1_START 0x08

static u32 si_out[32] __attribute__((aligned(32)));
static u32 si_in[32] __attribute__((aligned(32)));

static int baseboard_jvs_transfer(const u8 *frame, u8 frame_length)
{
    u8 *out = (u8 *)si_out;

    memset(si_out, 0, sizeof(si_out));
    memset(si_in, 0, sizeof(si_in));

    out[0] = 0x70;
    out[1] = (u8)(2 + frame_length);
    out[2] = 0x40;
    out[3] = frame_length;
    memcpy(out + 4, frame, frame_length);

    for (int attempt = 0; attempt < 120; ++attempt)
    {
        if (SI_Transfer(SI_CHAN0, si_out, 128, si_in, 128, NULL, 0))
        {
            SI_Sync();
            return 1;
        }
        SI_Sync();
        VIDEO_WaitVSync();
    }
    return 0;
}

static int unescape_jvs(const u8 *src, unsigned src_length,
                        u8 *dst, unsigned dst_capacity)
{
    unsigned written = 0;
    for (unsigned i = 0; i < src_length; ++i)
    {
        u8 value = src[i];
        if (value == 0xD0)
        {
            if (++i >= src_length)
                return -1;
            value = (u8)(src[i] + 1);
        }
        if (written >= dst_capacity)
            return -1;
        dst[written++] = value;
    }
    return (int)written;
}

static int read_jvs_switches(u8 *system_inputs, u8 *player1_switch0,
                             u8 *player1_switch1)
{
    const u8 frame[] = {0xE0, 0x01, 0x04, 0x20, 0x01, 0x02, 0x28};
    u8 decoded[32];

    if (!baseboard_jvs_transfer(frame, sizeof(frame)))
        return 0;

    const u8 *response = (const u8 *)si_in;
    if (response[0] != 0x01 || response[2] != 0x40 || response[3] < 9)
        return 0;
    if (response[4] != 0xE0)
        return 0;

    const int decoded_length = unescape_jvs(response + 5, response[3] - 1,
                                             decoded, sizeof(decoded));
    if (decoded_length < 8)
        return 0;
    if (decoded[0] != 0x00 || decoded[2] != 0x01 || decoded[3] != 0x01)
        return 0;
    if (decoded[1] + 2 != decoded_length)
        return 0;

    u8 checksum = 0;
    for (int i = 0; i < decoded_length - 1; ++i)
        checksum = (u8)(checksum + decoded[i]);
    if (checksum != decoded[decoded_length - 1])
        return 0;

    *system_inputs = decoded[4];
    *player1_switch0 = decoded[5];
    *player1_switch1 = decoded[6];
    return 1;
}

int main(int argc, char **argv)
{
    (void)argc;
    (void)argv;

    VIDEO_Init();
    rmode = VIDEO_GetPreferredMode(NULL);
    if (rmode == NULL)
        while (1) { }

    xfb = MEM_K0_TO_K1(SYS_AllocateFramebuffer(rmode));
    if (xfb == NULL)
        while (1) { }

    console_init(xfb, 20, 20, rmode->fbWidth, rmode->xfbHeight,
                 rmode->fbWidth * VI_DISPLAY_PIX_SZ);
    VIDEO_Configure(rmode);
    VIDEO_SetNextFramebuffer(xfb);
    VIDEO_SetBlack(FALSE);
    VIDEO_Flush();
    VIDEO_WaitVSync();
    if (rmode->viTVMode & VI_NON_INTERLACE)
        VIDEO_WaitVSync();

    printf("\x1b[2J");
    printf("\x1b[2;0HTRIFORCE NETBOOT SEGABOOT RESET PROBE v10");
    printf("\x1b[3;0H--------------------------------------------");
    printf("\x1b[5;0HFULL RESET / FIRMWARE HAND-OFF EXPERIMENT");
    printf("\x1b[7;0HFor Dolphin 2609b Triforce mode ONLY.");
    printf("\x1b[8;0HDO NOT RUN THIS TEST ON REAL TRIFORCE HARDWARE.");
    printf("\x1b[10;0HUses the tested Triforce SI/JVS input path.");
    printf("\x1b[11;0HPress Player 1 START (JVS switch bit 0x08).");
    printf("\x1b[12;0HReset flag then SYS_ResetSystem(SYS_RESTART).");
    printf("\x1b[14;0HNo DI Write/Execute command or firmware write.");
    printf("\x1b[16;0HSet up segaboot.gcm and IPL_TRI.bin first.");
    printf("\x1b[18;0HWaiting for JVS input...");

    const u8 set_address[] = {0xE0, 0xFF, 0x03, 0xF1, 0x01, 0xF4};
    const int address_sent = baseboard_jvs_transfer(set_address, sizeof(set_address));
    const u8 prime[] = {0xE0, 0x01, 0x04, 0x20, 0x01, 0x02, 0x28};
    baseboard_jvs_transfer(prime, sizeof(prime));
    baseboard_jvs_transfer(prime, sizeof(prime));

    printf("\x1b[20;0HSetAddress: %s", address_sent ? "sent" : "FAILED");

    u8 system_inputs = 0, p1_switch0 = 0, p1_switch1 = 0;
    while (1)
    {
        const int valid = read_jvs_switches(&system_inputs, &p1_switch0, &p1_switch1);
        printf("\x1b[18;0HJVS response: %-12s", valid ? "PASS" : "WAIT/NO DATA");
        printf("\x1b[21;0HSYSTEM: %02X  P1 SW0: %02X  P1 SW1: %02X",
               system_inputs, p1_switch0, p1_switch1);
        printf("\x1b[22;0HP1 START bit 0x08: %s",
               (p1_switch0 & JVS_P1_START) ? "PRESSED" : "released");

        if (valid && (p1_switch0 & JVS_P1_START))
        {
            printf("\x1b[24;0HSTART DETECTED - REQUESTING RESET");
            *TRIFORCE_RESET_FLAG = 1;
            DCFlushRange((void *)TRIFORCE_RESET_FLAG, sizeof(u32));
            __asm__ volatile("sync" ::: "memory");
            VIDEO_WaitVSync();
            SYS_ResetSystem(SYS_RESTART, 0, TRUE);

            printf("\x1b[24;0HSYS_ResetSystem RETURNED");
            while (1)
                VIDEO_WaitVSync();
        }
        VIDEO_WaitVSync();
    }
    return 0;
}
