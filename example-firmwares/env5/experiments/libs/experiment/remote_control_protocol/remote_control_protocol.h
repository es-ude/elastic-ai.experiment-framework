#ifndef REMOTE_CONTROL_PROTOCOL
#define REMOTE_CONTROL_PROTOCOL
#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>

typedef struct RCPFrame RCPFrame;

uint16_t RCP_getPayloadSize(const RCPFrame *frame);
uint16_t RCP_getMaxPayloadSize(const RCPFrame *frame);
const uint8_t *RCP_getFrameBuffer(const RCPFrame *frame);
uint16_t RCP_getFrameBufferSize(const RCPFrame *frame);
uint8_t RCP_getChecksum(const RCPFrame *frame);
uint8_t RCP_computeChecksum(const RCPFrame *frame);
RCPFrame *RCP_createFrame(void *buffer, uint16_t buffer_size);
void RCP_setPayloadSize(RCPFrame *frame, uint16_t size);
void RCP_updateChecksum(RCPFrame *frame);
void RCP_requireChecksum(RCPFrame *frame);
bool RCP_doesRequireChecksum(const RCPFrame *frame);
void RCP_disableChecksum(RCPFrame *frame);

/*
For performance reasons, you can write to the payload buffer
directly, but it is your responsibility to not write past the
allowed payload size.
*/
void *RCP_getPayload(RCPFrame *frame);

void RCP_send(const RCPFrame *frame);
void RCP_receive(RCPFrame *frame);

typedef void (*RCP_writeFN)(const void *, size_t);
typedef void (*RCP_readFN)(void *, size_t);

void RCP_setWriteFN(RCP_writeFN writeFn);
void RCP_setReadFN(RCP_readFN readFn);

typedef struct RCPFrameIterator
{
    RCPFrame *frame;
    uint8_t *current_byte;
} RCPFrameIterator;

typedef RCPFrameIterator RCPFrameWriter;

/*
The functions below are useful, if you want to store frames byte by
byte, e.g., from inside an interrupt handler, so you know when the
full frame has been written.
*/
void RCP_initFrameWriter(RCPFrameWriter *writer, RCPFrame *frame);
void RCP_writeByteToFrame(RCPFrameWriter *writer, uint8_t data);
bool RCP_frameWriterFinished(const RCPFrameWriter *self);

#endif