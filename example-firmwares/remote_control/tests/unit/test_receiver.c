#include "unity.h"
#include "receiver_internal.h"

Receiver parser;
static bool handler_called = false;

/* =========================================================
 * MOCKS
 * ========================================================= */

void handle_incoming_frame(RingBuffer *task_rb, Frame *frame)
{
    handler_called = true;
    TEST_ASSERT_EQUAL_UINT8(0x01, frame->header.message_type);
}

/* =========================================================
 * SETUP / TEARDOWN
 * ========================================================= */

void setUp(void)
{
    parser.state = WAIT_START;
    parser.index = 0;

    handler_called = false;
}

void tearDown(void)
{
}

/* =========================================================
 * TESTS
 * ========================================================= */

void test_parser_detects_complete_frame(void)
{
    uint8_t frame[] = {
        0xAA,       // start
        0x01,       // type
        0x00,       // flags
        0x42,       // tx id
        0x00, 0x03, // payload len = 3
        0x11,
        0x22,
        0x33};

    bool complete = false;

    for (int i = 0; i < sizeof(frame); i++)
    {
        complete = frame_parser_feed(&parser, frame[i]);
    }

    TEST_ASSERT_TRUE(complete);

    TEST_ASSERT_EQUAL_UINT8(0x01,
                            parser.frame.header.message_type);

    TEST_ASSERT_EQUAL_UINT16(3,
                             parser.frame.header.payload_len);

    TEST_ASSERT_EQUAL_UINT8(0x11,
                            parser.frame.payload[0]);

    TEST_ASSERT_EQUAL_UINT8(0x33,
                            parser.frame.payload[2]);
}

void test_parser_rejects_too_large_payload(void)
{
    uint8_t frame[] = {
        0xAA,
        0x01,
        0x00,
        0x42,
        0xFF, 0xFF};

    for (int i = 0; i < sizeof(frame); i++)
    {
        frame_parser_feed(&parser, frame[i]);
    }

    TEST_ASSERT_EQUAL(WAIT_START, parser.state);
}

void test_process_rx_calls_handler(void)
{
    int ringbuffer_size = sizeof(Frame) * 32;

    RingBuffer incoming;
    RingBuffer task_rb;
    uint8_t incoming_storage[ringbuffer_size];
    uint8_t outgoing_storage[ringbuffer_size];

    ringbuffer_init(&incoming, &incoming_storage, ringbuffer_size, sizeof(Frame));
    Receiver receiver = {
        .state = WAIT_START,
        .incoming_rb = &incoming,
        .task_rb = &task_rb};

    uint8_t frame[] = {0xAA, 0x01, 0x00, 0x42, 0x00, 0x01, 0x99};
    for (int i = 0; i < sizeof(frame); i++)
    {
        ringbuffer_push(&incoming, &frame[i]);
    }

    process_rx(&receiver);

    TEST_ASSERT_TRUE(handler_called);
}

int main(void)
{
    UNITY_BEGIN();

    RUN_TEST(test_parser_detects_complete_frame);
    RUN_TEST(test_parser_rejects_too_large_payload);

    RUN_TEST(test_process_rx_calls_handler);

    return UNITY_END();
}
