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
    u8 *in = (u8 *)si_in;

    memset(si_out, 0, sizeof(si_out));
    memset(si_in, 0, sizeof(si_in));

    // GC-AM SI command 0x70; subcommand 0x40 forwards a JVS-IO frame.
    out[0] = 0x70;
    out[1] = (u8)(2 + frame_length);
    out[2] = 0x40;
    out[3] = frame_length;
    memcpy(out + 4, frame, frame_length);

    // Channel 0 is the Triforce baseboard when configured in Dolphin.
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

static int unescape_jvs(const u8 *src, unsigned src_length, u8 *dst, unsigned dst_capacity)
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

static int read_jvs_switches(u8 *system_inputs, u8 *player1_switch0, u8 *player1_switch1)
{
    const u8 switch_input_frame[] = {
        0xE0, 0x01, 0x04, 0x20, 0x01, 0x02, 0x28
    };
    u8 decoded[32];

    if (!baseboard_jvs_transfer(switch_input_frame, sizeof(switch_input_frame)))
        return 0;

    const u8 *response = (const u8 *)si_in;

    // GC-AM response: status, data length, JVS command, JVS byte count, JVS frame.
    if (response[0] != 0x01 || response[2] != 0x40 || response[3] < 9)
        return 0;
    if (response[4] != 0xE0)
        return 0;

    const int decoded_length = unescape_jvs(response + 5, response[3] - 1,
                                             decoded, sizeof(decoded));
    if (decoded_length < 8)
        return 0;

    // JVS response: node, length, status, report, system inputs, P1 bytes, checksum.
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
    printf("\x1b[2;0HTRIFORCE NETBOOT JVS INPUT PROBE v07");
    printf("\x1b[3;0H--------------------------------------");
    printf("\x1b[5;0HThis probe polls the Triforce baseboard SI/JVS path.");
    printf("\x1b[6;0HIt does not reset the system or alter firmware.");
    printf("\x1b[8;0HInitializing JVS node address...");

    // JVS broadcast SetAddress: assign node 1 to the baseboard I/O board.
    const u8 set_address_frame[] = {0xE0, 0xFF, 0x03, 0xF1, 0x01, 0xF4};
    const int address_sent = baseboard_jvs_transfer(set_address_frame,
                                                    sizeof(set_address_frame));

    // Prime the two-buffer GC-AM response queue, then begin reading SwitchInput.
    const u8 switch_input_frame[] = {0xE0, 0x01, 0x04, 0x20, 0x01, 0x02, 0x28};
    baseboard_jvs_transfer(switch_input_frame, sizeof(switch_input_frame));
    baseboard_jvs_transfer(switch_input_frame, sizeof(switch_input_frame));

    printf("\x1b[8;0HSetAddress transfer: %s", address_sent ? "sent" : "FAILED");
    printf("\x1b[10;0HPress the mapped Test and Service buttons.");
    printf("\x1b[11;0HExpected: Test sets SYSTEM bit 7 (0x80).");
    printf("\x1b[12;0HExpected: Service sets P1 switch bit 6 (0x40).");
    printf("\x1b[13;0HPlayer 1 START requests cold reset (Dolphin only).");

    u8 system_inputs = 0;
    u8 player1_switch0 = 0;
    u8 player1_switch1 = 0;
    int valid = 0;

    while (1)
    {
        valid = read_jvs_switches(&system_inputs, &player1_switch0, &player1_switch1);

        printf("\x1b[15;0HJVS SwitchInput response: %-12s", valid ? "PASS" : "WAIT/NO DATA");
        printf("\x1b[17;0HSYSTEM INPUT: 0x%02X   TEST: %s",
               system_inputs, (system_inputs & 0x80) ? "PRESSED" : "released");
        printf("\x1b[18;0HP1 SWITCH 0: 0x%02X   SERVICE: %s",
               player1_switch0, (player1_switch0 & 0x40) ? "PRESSED" : "released");
        printf("\x1b[19;0HP1 SWITCH 1: 0x%02X", player1_switch1);
        printf("\x1b[20;0HP1 START bit 0x08: %s",
               (player1_switch0 & JVS_P1_START) ? "PRESSED" : "released");

        if (valid && (player1_switch0 & JVS_P1_START))
        {
            printf("\x1b[22;0HSTART DETECTED - REQUESTING RESET");
            *TRIFORCE_RESET_FLAG = 1;
            DCFlushRange((void *)TRIFORCE_RESET_FLAG, sizeof(u32));
            __asm__ volatile("sync" ::: "memory");
            VIDEO_WaitVSync();
            SYS_ResetSystem(SYS_RESTART, 0, TRUE);
            printf("\x1b[22;0HSYS_ResetSystem RETURNED");
            while (1)
                VIDEO_WaitVSync();
        }
        VIDEO_WaitVSync();
    }

    return 0;
}
