#include <gccore.h>
#include <stdio.h>

static void *xfb;
static GXRModeObj *rmode;

#define TRIFORCE_RESET_FLAG ((volatile u32 *)0x811FFF00)

int main(int argc, char **argv)
{
    (void)argc;
    (void)argv;

    VIDEO_Init();
    PAD_Init();

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
    printf("\x1b[2;0HTRIFORCE NETBOOT SEGABOOT RESET PROBE v09");
    printf("\x1b[3;0H--------------------------------------------");
    printf("\x1b[5;0HFULL RESET / FIRMWARE HAND-OFF EXPERIMENT");
    printf("\x1b[7;0HFor Dolphin 2609b Triforce mode ONLY.");
    printf("\x1b[8;0HDO NOT RUN THIS TEST ON REAL TRIFORCE HARDWARE.");
    printf("\x1b[10;0HThis sets the OS reset hand-off flag, then");
    printf("\x1b[11;0Hrequests a cold PPC reset via SYS_ResetSystem.");
    printf("\x1b[12;0HNo DI Write/Execute command or firmware write.");
    printf("\x1b[14;0HAfter reset, Dolphin should follow the normal");
    printf("\x1b[15;0Hboot path; the 0x2440 read should map SegaBoot.");
    printf("\x1b[17;0HMake sure segaboot.gcm and IPL_TRI.bin are");
    printf("\x1b[18;0Hconfigured in Dolphin before proceeding.");
    printf("\x1b[20;0HPRESS START to request the reset.");
    printf("\x1b[22;0HAny other button leaves this screen running.");

    while (1)
    {
        PAD_ScanPads();
        const u16 down = PAD_ButtonsDown(0);
        if (down & PAD_BUTTON_START)
        {
            printf("\x1b[20;0HRESET REQUESTED - DO NOT INTERRUPT");
            *TRIFORCE_RESET_FLAG = 1;
            DCFlushRange((void *)TRIFORCE_RESET_FLAG, sizeof(u32));
            __asm__ volatile("sync" ::: "memory");
            VIDEO_WaitVSync();
            SYS_ResetSystem(SYS_RESTART, 0, TRUE);

            printf("\x1b[20;0HSYS_ResetSystem RETURNED");
            while (1)
                VIDEO_WaitVSync();
        }
        VIDEO_WaitVSync();
    }

    return 0;
}
