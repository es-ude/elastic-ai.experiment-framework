#include "unity.h"
#include "receiver.h"
#include <string.h>

/* =========================================================
 * GLOBAL STATE
 * ========================================================= */

Receiver parser;
static bool handler_called = false;

/* =========================================================
 * MOCKS
 * ========================================================= */

void handle_incoming_frame(RingBuffer *task_rb, Frame *frame, TaskManager *task_manager)
{
    (void)task_rb;

    handler_called = true;

    TEST_ASSERT_EQUAL_UINT8(0x01, frame->header.message_type);
    TEST_ASSERT_EQUAL_UINT16(3, frame->header.payload_len);

    TEST_ASSERT_EQUAL_UINT8(0x11, frame->payload[0]);
    TEST_ASSERT_EQUAL_UINT8(0x33, frame->payload[2]);
}

/* =========================================================
 * SETUP / TEARDOWN
 * ========================================================= */

static TaskManager mock_task_manager = {0};

void setUp(void)
{
    memset(&parser, 0, sizeof(parser));
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

void test_process_rx_detects_complete_frame(void)
{
    int size = 64;

    uint8_t incoming_storage[64];
    RingBuffer incoming;
    ringbuffer_init(&incoming, incoming_storage, size, sizeof(uint8_t));

    RingBuffer task_rb;

    Receiver rx = {
        .state = WAIT_START,
        .incoming_rb = &incoming,
        .task_rb = &task_rb};

    uint8_t frame[] = {
        0xAA, // start
        0x01, // type
        0x00, // flags
        0x42, // tx id
        0x00,
        0x03, 0x00, // payload len = 3
        0x11,
        0x22,
        0x33};

    for (int i = 0; i < sizeof(frame); i++)
    {
        ringbuffer_push(&incoming, &frame[i]);
    }

    process_rx(&rx, &mock_task_manager, NULL);

    TEST_ASSERT_TRUE(handler_called);
}

void test_process_rx_rejects_too_large_payload(void)
{
    int size = 64;
    uint8_t incoming_storage[64];
    RingBuffer incoming;
    ringbuffer_init(&incoming, incoming_storage, size, sizeof(uint8_t));

    RingBuffer task_rb;

    Receiver rx = {
        .state = WAIT_START,
        .incoming_rb = &incoming,
        .task_rb = &task_rb};

    uint8_t frame[] = {
        0xAA,
        0x01,
        0x00,
        0x42,
        0x00,
        0xFF,
        0xFF};

    for (int i = 0; i < sizeof(frame); i++)
    {
        ringbuffer_push(&incoming, &frame[i]);
    }

    process_rx(&rx, &mock_task_manager, NULL);

    TEST_ASSERT_FALSE(handler_called);
    TEST_ASSERT_EQUAL(WAIT_START, rx.state);
}

/* =========================================================
 * MAIN
 * ========================================================= */

int main(void)
{
    UNITY_BEGIN();

    RUN_TEST(test_process_rx_detects_complete_frame);
    RUN_TEST(test_process_rx_rejects_too_large_payload);

    return UNITY_END();
}