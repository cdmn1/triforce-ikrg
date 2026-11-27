#include <gccore.h>
#include <stdio.h>
#include <string.h>

static void *xfb;
static GXRModeObj *rmode;

static u8 apploader_header[0x20] __attribute__((aligned(32)));
static u8 firmware_header[0x40] __attribute__((aligned(32)));

#define DI_BASE ((volatile u32 *)0xCC006000)
#define DI_STATUS       0
#define DI_COVER        1
#define DI_COMMAND_0    2
#define DI_COMMAND_1    3
#define DI_COMMAND_2    4
#define DI_DMA_ADDRESS  5
#define DI_DMA_LENGTH   6
#define DI_CONTROL      7

#define TRIFORCE_DI_READ 0xA8u
#define TRIFORCE_SEED    1u
#define TRIFORCE_RESET_FLAG ((volatile u32 *)0x811FFF00)
#define SEGA_BOOT_SIGNATURE_ADDRESS ((volatile u32 *)0x8006BF70)

static int triforce_di_read(u32 offset, u32 length, void *buffer,
                            u32 key_a, u32 key_b, u32 key_c, u32 *status_out)
{
    volatile u32 *di = DI_BASE;
    const u32 seed = TRIFORCE_SEED;

    if ((offset & 3u) != 0 || (length & 31u) != 0)
        return 0;

    // The known-good Triforce DOL encodes all three DI command words:
    // word0 = (seed << 16 | command) XOR key A
    // word1 = (byte_offset >> 2) XOR key B
    // word2 = transfer_length XOR key C
    // A seed of 1 is valid (the reference protocol uses an odd 16-bit seed)
    // and leaves the evolving keys unchanged for this two-read probe.
    DCInvalidateRange(buffer, length);

    // Match the reference DOL's DI cover-register acknowledge.
    di[DI_COVER] = di[DI_COVER];

    di[DI_COMMAND_0] = ((seed << 16) | TRIFORCE_DI_READ) ^ key_a;
    di[DI_COMMAND_1] = (offset >> 2) ^ key_b;
    di[DI_COMMAND_2] = length ^ key_c;
    di[DI_DMA_ADDRESS] = (u32)buffer;
    di[DI_DMA_LENGTH] = length;

    __asm__ volatile("sync" ::: "memory");
    // Triforce reference DOL uses DI + DMA + START (0x7).
    di[DI_CONTROL] = 0x7;
    __asm__ volatile("sync" ::: "memory");

    int completed = 0;
    for (int frame = 0; frame < 180; ++frame)
    {
        if ((di[DI_CONTROL] & 1u) == 0)
        {
            completed = 1;
            break;
        }
        VIDEO_WaitVSync();
    }

    DCInvalidateRange(buffer, length);
    if (status_out != NULL)
        *status_out = di[DI_STATUS];

    return completed;
}

static u32 read_be32(const u8 *p)
{
    return ((u32)p[0] << 24) | ((u32)p[1] << 16) |
           ((u32)p[2] << 8) | (u32)p[3];
}

static void copy_title(char *out, unsigned out_size, const u8 *in, unsigned in_size)
{
    unsigned n = in_size;
    if (n >= out_size)
        n = out_size - 1;

    for (unsigned i = 0; i < n; ++i)
    {
        const u8 c = in[i];
        out[i] = (c >= 0x20 && c <= 0x7e) ? (char)c : ' ';
    }
    out[n] = '\0';
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
    printf("\x1b[2;0HTRIFORCE NETBOOT FIRMWARE MAP PROBE v08");
    printf("\x1b[3;0H----------------------------------------");
    printf("\x1b[5;0HREAD-ONLY DI test; no reset or firmware writes.");
    printf("\x1b[6;0HEmulator diagnostic only; do not run on hardware.");

    // Dolphin seeds its AM-Mediaboard command decoder from these RAM words
    // during Triforce boot. The probe deliberately uses seed 1 so keys remain
    // unchanged between its two read commands.
    const u32 key_a = *(volatile u32 *)0x00000000;
    const u32 key_b = *(volatile u32 *)0x00000004;
    const u32 key_c = *(volatile u32 *)0x00000008;
    const u32 sega_signature = *SEGA_BOOT_SIGNATURE_ADDRESS;

    printf("\x1b[8;0HDI keys A/B/C: %08X %08X %08X", key_a, key_b, key_c);
    printf("\x1b[9;0HSegaBoot signature RAM: %08X", sega_signature);

    // Dolphin's Triforce media-board handler only enables its firmware-read
    // source when this OSResetSystem flag is set and a DI command touches
    // offset 0x2440. We emulate only the flag and read sequence, not reset.
    *TRIFORCE_RESET_FLAG = 1;
    DCFlushRange((void *)TRIFORCE_RESET_FLAG, sizeof(u32));
    __asm__ volatile("sync" ::: "memory");

    memset(apploader_header, 0xA5, sizeof(apploader_header));
    u32 status_apploader = 0;
    const int read_apploader = triforce_di_read(0x2440, sizeof(apploader_header),
                                                apploader_header, key_a, key_b, key_c,
                                                &status_apploader);

    printf("\x1b[11;0HReset flag: %08X", *TRIFORCE_RESET_FLAG);
    printf("\x1b[12;0HRead @0x2440: %-8s DI status: %08X",
           read_apploader ? "COMPLETE" : "TIMEOUT", status_apploader);

    // Once the special 0x2440 read has enabled firmware mapping, a read at
    // offset zero (length 0x40, deliberately not 0x80) should return the
    // SegaBoot GCM header rather than the current game image header.
    memset(firmware_header, 0xA5, sizeof(firmware_header));
    u32 status_firmware = 0;
    const int read_firmware = triforce_di_read(0x0000, sizeof(firmware_header),
                                               firmware_header, key_a, key_b, key_c,
                                               &status_firmware);

    char title[33];
    copy_title(title, sizeof(title), firmware_header + 0x20, 0x20);
    const u32 magic = read_be32(firmware_header + 0x1C);
    const int is_game_image = memcmp(firmware_header, "GVSJ8P", 6) == 0;
    const int valid_header = magic == 0xC2339F3D;

    printf("\x1b[14;0HRead @0x0000: %-8s DI status: %08X",
           read_firmware ? "COMPLETE" : "TIMEOUT", status_firmware);
    printf("\x1b[16;0HReturned ID: %.6s", firmware_header);
    printf("\x1b[17;0HReturned title: %.32s", title);
    printf("\x1b[18;0HGC image magic: %08X (%s)", magic,
           valid_header ? "valid" : "invalid");
    printf("\x1b[20;0HMAP RESULT: %s",
           !read_apploader || !read_firmware ? "READ FAILED" :
           !valid_header ? "UNKNOWN / INVALID HEADER" :
           is_game_image ? "GAME IMAGE - MAP NOT OBSERVED" :
                           "DIFFERENT IMAGE - FIRMWARE CANDIDATE");

    printf("\x1b[22;0HThe map flag remains set until Dolphin is restarted.");
    while (1)
        VIDEO_WaitVSync();

    return 0;
}
