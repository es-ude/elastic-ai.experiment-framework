#include "unity.h"
#include "sender_internal.h"

#include "transport.h"
/* =========================================================
 * MOCKS
 * ========================================================= */

static uint8_t mock_out[512];
static int mock_idx = 0;

static void mock_send(Transport *t, uint8_t b)
{
    mock_out[mock_idx++] = b;
}

static Transport mock_transport;

static Frame rb_frame;
static int rb_has_data = 0;

/* =========================================================
 * SETUP / TEARDOWN
 * ========================================================= */

void setUp(void)
{
    mock_idx = 0;

    mock_transport.send_byte = mock_send;
    mock_transport.recv_byte = NULL;
    mock_transport.destroy = NULL;
}

void tearDown(void)
{
}

/* =========================================================
 * TESTS
 * ========================================================= */

void test_tx_start_initializes_context(void)
{
    Sender tx = {0};

    Frame frame = {
        .header = {
            .message_type = 0x01,
            .flags = 0x02,
            .transaction_id = 0x03,
            .payload_len = 2},
        .payload = {0xAA, 0xBB}};

    bool ok = tx_start(&tx, &frame);

    TEST_ASSERT_TRUE(ok);
    TEST_ASSERT_EQUAL(TX_SEND_START, tx.state);
    TEST_ASSERT_EQUAL_UINT8(0x01, tx.frame.header.message_type);
    TEST_ASSERT_EQUAL_UINT16(2, tx.frame.header.payload_len);
}

void test_tx_process_sends_complete_frame(void)
{
    Sender tx = {0};
    tx.transport = &mock_transport;

    Frame frame = {
        .header = {
            .message_type = 0x10,
            .flags = 0x20,
            .transaction_id = 0x30,
            .payload_len = 2},
        .payload = {0xAA, 0xBB}};

    tx_start(&tx, &frame);

    for (int i = 0; i < 20; i++)
    {
        tx_process(&tx);
        if (tx.state == TX_IDLE)
            break;
    }

    uint8_t expected[] = {
        0xAA,
        0x10,
        0x20,
        0x30,
        0x00, 0x02,
        0xAA, 0xBB};

    TEST_ASSERT_EQUAL_UINT8_ARRAY(expected, mock_out, 8);
}

void test_process_tx_starts_from_ringbuffer(void)
{
    Frame frame = {
        .header = {
            .message_type = 0x42,
            .flags = 0x00,
            .transaction_id = 0x01,
            .payload_len = 1},
        .payload = {0x99}};

    RingBuffer dummy_rb;
    Frame dummy_storage[64];
    ringbuffer_init(&dummy_rb, &dummy_storage, 64, sizeof(Frame));
    ringbuffer_push(&dummy_rb, &frame);

    Sender tx = {.outgoing_rb = &dummy_rb,
                 .transport = &mock_transport};

    process_tx(&tx);

    TEST_ASSERT_EQUAL(TX_SEND_HEADER, tx.state);
}

int main(void)
{
    UNITY_BEGIN();

    RUN_TEST(test_tx_start_initializes_context);
    RUN_TEST(test_tx_process_sends_complete_frame);
    RUN_TEST(test_process_tx_starts_from_ringbuffer);

    return UNITY_END();
}