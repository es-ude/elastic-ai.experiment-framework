#include "unity.h"

#include "sender.h"
#include "transport.h"

/* =========================================================
 * MOCKS
 * ========================================================= */

static uint8_t mock_out[512] = {0};
static int mock_idx = 0;

static void mock_send(Transport *t, uint8_t b)
{
    (void)t;
    mock_out[mock_idx++] = b;
}

static bool mock_tx_start(Sender *tx, Frame *frame)
{
    tx->frame = *frame; // copy header + payload
    tx->index = 0;
    tx->state = TX_SEND_START;
    return true;
}

static Transport mock_transport;

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

void test_tx_process_sends_complete_frame(void)
{
    Sender tx = {0};
    tx.transport = &mock_transport;

    Frame frame = {
        .header = {
            .start_byte = 0xAA,
            .message_type = 0x10,
            .flags = 0x20,
            .transaction_id = 0x01,
            .payload_len = 2},
        .payload = {0xAA, 0xBB}};

    mock_tx_start(&tx, &frame);

    for (int i = 0; i < 20; i++)
    {
        tx_process(&tx);
        if (tx.state == TX_IDLE)
            break;
    }

    uint8_t expected[] = {
        0xAA,       // start byte
        0x10,       // message type
        0x20,       // flags
        0x01,       // transaction id
        0x00,       // msg id
        0x02, 0x00, // payload length
        0xAA, 0xBB  // payload
    };

    TEST_ASSERT_EQUAL_UINT8_ARRAY(expected, mock_out, sizeof(expected));
}

void test_process_tx_starts_from_ringbuffer(void)
{
    Frame frame = {
        .header = {
            .start_byte = 0xAA,
            .message_type = 0x42,
            .flags = 0x00,
            .transaction_id = 0x01,
            .msg_id = 0x02,
            .payload_len = 1},
        .payload = {0x99}};

    RingBuffer dummy_rb;
    Frame dummy_storage[64];

    ringbuffer_init(&dummy_rb, dummy_storage, 64, sizeof(Frame));
    ringbuffer_push(&dummy_rb, &frame);

    Sender tx = {
        .outgoing_rb = &dummy_rb,
        .transport = &mock_transport};

    process_tx(&tx);

    TEST_ASSERT_EQUAL(TX_SEND_HEADER, tx.state);
}

void test_has_checksum(void)
{
    Sender tx = {0};
    tx.transport = &mock_transport;

    Frame frame = {
        .header = {
            .start_byte = 0xAA,
            .message_type = 0x10,
            .flags = 0 | FLAG_HAS_CRC,
            .transaction_id = 0x01,
            .payload_len = 2},
        .payload = {0xAA, 0xBB}};

    mock_tx_start(&tx, &frame);

    for (int i = 0; i < 20; i++)
    {
        tx_process(&tx);
        if (tx.state == TX_IDLE)
            break;
    }

    uint8_t expected[] = {
        0xAA,         // start byte
        0x10,         // message type
        FLAG_HAS_CRC, // flags
        0x01,         // transaction id
        0x00,         // msg id
        0x02,
        0x00, // payload length
        0xAA,
        0xBB, // payload
        0xB2  // Checksum
    };

    TEST_ASSERT_EQUAL_UINT8_ARRAY(expected, mock_out, sizeof(expected));
}

int main(void)
{
    UNITY_BEGIN();

    RUN_TEST(test_tx_process_sends_complete_frame);
    RUN_TEST(test_process_tx_starts_from_ringbuffer);
    RUN_TEST(test_has_checksum);

    return UNITY_END();
}