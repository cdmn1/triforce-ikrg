#include <gccore.h>
#include <stdio.h>
#include <stdlib.h>

static void *xfb;
static GXRModeObj *rmode;

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

    printf("\x1b[2;0H");
    printf("TRIFORCE NETBOOT HELLO WORLD v01\n");
    printf("--------------------------------\n");
    printf("GameCube / Triforce PowerPC Gekko\n");
    printf("Video initialization: PASS\n");
    printf("No DVD reads or external files\n");
    printf("No Joybus controller required\n");
    printf("\nWaiting for next development step...\n");

    while (1)
        VIDEO_WaitVSync();

    return 0;
}
