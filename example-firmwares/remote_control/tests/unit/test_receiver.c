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

void test_received_checksum(void)
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
        0xAA,         // start
        0x01,         // type
        FLAG_HAS_CRC, // flags
        0x42,         // tx id
        0x00,
        0x03, 0x00, // payload len = 3
        0x11,
        0x22,
        0x33,
        0x12}; // Checksum mockup

    for (int i = 0; i < sizeof(frame); i++)
    {
        ringbuffer_push(&incoming, &frame[i]);
    }

    process_rx(&rx, &mock_task_manager, NULL);

    TEST_ASSERT_TRUE(handler_called);

    printf("rx.frame (%zu Bytes):\n", sizeof(rx.frame));
    uint8_t *bytes = (uint8_t *)&rx.frame;

    for (size_t i = 0; i < sizeof(rx.frame); i++)
    {
        printf("%02X ", bytes[i]);
    }
    printf("\n");

    TEST_ASSERT_EQUAL_UINT8(0xAA, rx.frame.header.start_byte);
    TEST_ASSERT_EQUAL_UINT8(0x01, rx.frame.header.message_type);
    TEST_ASSERT_EQUAL_UINT8(FLAG_HAS_CRC, rx.frame.header.flags);
    TEST_ASSERT_EQUAL_UINT8(0x42, rx.frame.header.transaction_id);
    TEST_ASSERT_EQUAL_UINT8(0x00, rx.frame.header.msg_id);
    TEST_ASSERT_EQUAL_UINT16(3, rx.frame.header.payload_len);

    TEST_ASSERT_EQUAL_UINT8_ARRAY(&frame[7],
                                  rx.frame.payload,
                                  4); // 3 Payload + CRC
}

/* =========================================================
 * MAIN
 * ========================================================= */

int main(void)
{
    UNITY_BEGIN();

    RUN_TEST(test_process_rx_detects_complete_frame);
    RUN_TEST(test_process_rx_rejects_too_large_payload);
    RUN_TEST(test_received_checksum);

    return UNITY_END();
}