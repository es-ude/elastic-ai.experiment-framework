#include "remote_control_protocol.h"
#include <stdio.h>
#include <string.h>
#include <stdbool.h>

#define PAYLOAD_OFFSET 3
#define PAYLOAD_SIZE_OFFSET 1
#define FRAME_OVERHEAD 3
#define CHECKSUM_SIZE 1

struct RCPFrame
{
    uint16_t max_payload_size;
    uint8_t *frame_buffer;
};

bool RCP_doesRequireChecksum(const RCPFrame *frame)
{
    return frame->frame_buffer[0] & 0x80;
}

void RCP_setPayloadSize(RCPFrame *frame, uint16_t size)
{
    frame->frame_buffer[PAYLOAD_SIZE_OFFSET] = size & 0xff;
    frame->frame_buffer[PAYLOAD_SIZE_OFFSET + 1] = (size >> 8) & 0xff;
}

uint16_t RCP_getPayloadSize(const RCPFrame *frame)
{
    return frame->frame_buffer[PAYLOAD_SIZE_OFFSET] | (frame->frame_buffer[PAYLOAD_SIZE_OFFSET + 1] << 8);
}

const uint8_t *RCP_getFrameBuffer(const RCPFrame *frame)
{
    return frame->frame_buffer;
}

void *RCP_getPayload(RCPFrame *frame)
{
    return frame->frame_buffer + PAYLOAD_OFFSET;
}

RCPFrame *RCP_createFrame(void *frame_buffer, uint16_t size)
{
    RCPFrame *frame = frame_buffer;
    frame->frame_buffer = frame_buffer + sizeof(RCPFrame);
    int max_payload_size = size - sizeof(RCPFrame);
    frame->max_payload_size = max_payload_size;
    frame->require_checksum = false;
    memset(frame->frame_buffer, 0, max_payload_size);
    return frame;
}

uint16_t RCP_getMaxPayloadSize(const RCPFrame *frame)
{
    return frame->max_payload_size;
}

void RCP_requireChecksum(RCPFrame *frame)
{
    frame->require_checksum = true;
    frame->frame_buffer[0] |= (1 << 7);
}

void RCP_disableChecksum(RCPFrame *frame)
{
    frame->require_checksum = false;
}

uint8_t RCP_computeChecksum(const RCPFrame *frame)
{
    uint8_t checksum = 0;
    uint16_t size = PAYLOAD_OFFSET + RCP_getPayloadSize(frame);
    for (int i = 0; i < size; i++)
    {
        checksum ^= frame->frame_buffer[i];
    }
    return checksum;
}

void RCP_updateChecksum(RCPFrame *frame)
{
    uint16_t size = PAYLOAD_OFFSET + RCP_getPayloadSize(frame);
    frame->frame_buffer[size] = RCP_computeChecksum(frame);
}

static bool writingIterIsFresh(RCPFrameWriter *iter)
{
    return iter->frame->frame_buffer == iter->current_byte;
}

void RCP_initFrameWriter(RCPFrameWriter *writer, RCPFrame *frame)
{
    writer->current_byte = frame->frame_buffer;
    writer->frame = frame;
}

void RCP_writeByteToFrame(RCPFrameWriter *self, uint8_t data)
{
    *self->current_byte = data;
    self->current_byte++;
}

static bool wroteHeader(int offset)
{
    return offset >= PAYLOAD_OFFSET;
}

static bool wroteRestOfFrame(const RCPFrame *frame, int offset)
{
    int effective_size = PAYLOAD_OFFSET + RCP_getPayloadSize(frame);
    if (RCP_doesRequireChecksum(frame))
    {
        effective_size++;
    }
    return offset >= effective_size;
}

bool RCP_frameWriterFinished(const RCPFrameWriter *self)
{
    int current_offset = self->current_byte - self->frame->frame_buffer;
    return wroteHeader(current_offset) && wroteRestOfFrame(self->frame, current_offset);
}

uint16_t
RCP_getFrameBufferSize(const RCPFrame *self)
{
    uint16_t size = PAYLOAD_OFFSET + RCP_getPayloadSize(self);
    if (RCP_doesRequireChecksum(self))
    {
        size++;
    }
    return size;
}