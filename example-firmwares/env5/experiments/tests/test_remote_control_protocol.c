#include "unity.h"
#include "remote_control_protocol.h"
#include "string.h"

void test_payload_size_is_written_correctly(void)
{
    int buffer_size = 256;
    char frame_buffer[buffer_size];
    RCPFrame *frame = RCP_createFrame(frame_buffer, buffer_size);
    int payload_size = 2;
    RCP_setPayloadSize(frame, payload_size);
    char expected[2] = {payload_size, 0};

    TEST_ASSERT_EQUAL_UINT8_ARRAY(expected, RCP_getFrameBuffer(frame) + 1, 2);
}

void test_write_full_payload(void)
{
    int buffer_size = 256;
    char frame_buffer[buffer_size];
    RCPFrame *frame = RCP_createFrame(frame_buffer, buffer_size);
    int payload_size = 2;
    RCP_setPayloadSize(frame, payload_size);
    char expected[2] = {payload_size, 0};
    uint8_t *payload = RCP_getPayload(frame);
    payload[1] = 0xff;
    TEST_ASSERT_EQUAL_HEX8(0xff, RCP_getFrameBuffer(frame)[4]);
}

void test_enable_checksum(void)
{
    int buffer_size = 256;
    char frame_buffer[buffer_size];
    RCPFrame *frame = RCP_createFrame(frame_buffer, buffer_size);
    int payload_size = 2;
    RCP_setPayloadSize(frame, payload_size);
    int num_bytes_without_checksum = RCP_getFrameBufferSize(frame);
    RCP_requireChecksum(frame);
    int num_bytes_with_checksum = RCP_getFrameBufferSize(frame);
    TEST_ASSERT_EQUAL_INT(1, num_bytes_with_checksum - num_bytes_without_checksum);
}

void test_compute_checksum(void)
{
    int buffer_size = 256;
    char frame_buffer[buffer_size];
    RCPFrame *frame = RCP_createFrame(frame_buffer, buffer_size);
    int payload_size = 2;
    RCP_setPayloadSize(frame, payload_size);
    RCP_requireChecksum(frame);
    uint8_t *payload = RCP_getPayload(frame);
    payload[0] = 0xff;
    payload[1] = 0xfE;
    RCP_updateChecksum(frame);

    TEST_ASSERT_EQUAL_HEX8(0x83, RCP_getFrameBuffer(frame)[5]);
}

void test_requiring_checksum_sets_checksum_flag_in_first_byte()
{
    int buffer_size = 256;
    char frame_buffer[buffer_size];
    RCPFrame *frame = RCP_createFrame(frame_buffer, buffer_size);
    int payload_size = 2;
    RCP_setPayloadSize(frame, payload_size);
    RCP_requireChecksum(frame);
    TEST_ASSERT_EQUAL_UINT8(1 << 7, RCP_getFrameBuffer(frame)[0]);
}

RCPFrame *prepare_incoming_frame(void *frame_buffer)
{
    RCPFrame *incoming_frame = RCP_createFrame(incoming_frame, 20);
    RCP_setPayloadSize(incoming_frame, 3);
    uint8_t *incoming_payload = RCP_getPayload(incoming_frame);
    incoming_payload[0] = 0x0A;
    incoming_payload[1] = 0x0B;
    incoming_payload[1] = 0x0C;
    return incoming_frame;
}

void test_framewriter_does_not_exceed_end_of_frame()
{
    int buffer_size = 256;
    char frame_buffer[buffer_size];
    char incoming_frame_buffer[20];

    RCPFrame *result = RCP_createFrame(frame_buffer, 256);
    RCPFrame *incoming_frame = prepare_incoming_frame(incoming_frame);
    RCPFrameWriter writer;
    RCP_initFrameWriter(&writer, result);

    int num_iters = 0;
    const uint8_t *raw_incoming_frame = RCP_getFrameBuffer(incoming_frame);
    while (!RCP_frameWriterFinished(&writer) || num_iters > 50)
    {
        num_iters++;
        RCP_writeByteToFrame(&writer, *raw_incoming_frame);
        raw_incoming_frame++;
    }
    TEST_ASSERT_EQUAL_INT(6, num_iters);
}

void test_framewriter_with_checksum_does_not_exceed_end_of_frame()
{
    int buffer_size = 256;
    char frame_buffer[buffer_size];
    char incoming_frame_buffer[20];

    RCPFrame *result = RCP_createFrame(frame_buffer, 256);
    RCPFrame *incoming_frame = prepare_incoming_frame(incoming_frame);
    RCPFrameWriter writer = {.frame = result};
    RCP_initFrameWriter(&writer, result);
    RCP_requireChecksum(incoming_frame);

    int num_iters = 0;
    const uint8_t *raw_incoming_frame = RCP_getFrameBuffer(incoming_frame);
    while (!RCP_frameWriterFinished(&writer) || num_iters > 50)
    {
        num_iters++;
        RCP_writeByteToFrame(&writer, *raw_incoming_frame);
        raw_incoming_frame++;
    }
    TEST_ASSERT_EQUAL_INT(7, num_iters);
}

int main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_payload_size_is_written_correctly);
    RUN_TEST(test_write_full_payload);
    RUN_TEST(test_enable_checksum);
    RUN_TEST(test_compute_checksum);
    RUN_TEST(test_requiring_checksum_sets_checksum_flag_in_first_byte);
    RUN_TEST(
        test_framewriter_does_not_exceed_end_of_frame);
    RUN_TEST(
        test_framewriter_with_checksum_does_not_exceed_end_of_frame);
    return UNITY_END();
}

void tearDown(void)
{
}

void setUp(void) {}