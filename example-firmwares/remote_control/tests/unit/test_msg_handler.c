#include "unity.h"

#include "msg_handler.h"
#include "task_manager.h"
#include "frame.h"
#include "msg_types.h"

#include <string.h>
#include <stdlib.h>

/* =========================
 * TEST FIXTURES
 * ========================= */

static Frame make_frame(uint8_t type, uint8_t tx_id, uint8_t flags, uint8_t payload0)
{
    Frame f;
    memset(&f, 0, sizeof(f));

    f.header.start_byte = 0xAA;
    f.header.message_type = type;
    f.header.transaction_id = tx_id;
    f.header.flags = flags;
    f.header.payload_len = 1;
    f.payload[0] = payload0;

    return f;
}

/* =========================
 * SETUP
 * ========================= */

RingBuffer out_rb;

void setUp(void)
{
    init_tasks(&out_rb);
}

void tearDown(void)
{
}

/* =========================
 * TESTS
 * ========================= */

/* -------- OPEN_TASK -------- */

void test_msg_open_task_creates_task(void)
{
    Frame f = make_frame(OPEN_TASK, 1, 0, 0x01);

    int id = msg_open_task(&f);

    TEST_ASSERT_TRUE(id > 0);

    Task *t = get_task_by_id(id);
    printf("Opened Task with id: %i\n", t->id);
    fflush(stdout);
    TEST_ASSERT_NOT_NULL(t);
    TEST_ASSERT_EQUAL(TASK_STATUS_PREPARING, t->status);
}

/* -------- DATA_CHUNK -------- */

static int fake_called = 0;

static void fake_rn(Task *self)
{
    fake_called++;
}

void test_msg_data_chunk_routes_to_task(void)
{
    /* setup task */
    Frame open = make_frame(OPEN_TASK, 2, 0, 0x00);
    int id = msg_open_task(&open);
    TEST_ASSERT_EQUAL_INT(2, id);
    Task *t = get_task_by_id(id);

    RingBuffer task_rb;
    Task *task_storage[1024];
    ringbuffer_init(&task_rb, &task_storage, 1024, sizeof(Task *));
    t->run = fake_rn;
    TEST_ASSERT_NOT_NULL(t);
    Frame data = make_frame(DATA_CHUNK, id, 0, 0x99);

    int ret = msg_data_chunk(&task_rb, &data);

    TEST_ASSERT_EQUAL(id, ret);

    process_tasks(&task_rb, NULL);

    TEST_ASSERT_EQUAL(1, fake_called);
    TEST_ASSERT_EQUAL_UINT8(0x99, t->input_data[0]);
}

/* -------- UNKNOWN MESSAGE -------- */

void test_handle_incoming_frame_unknown_type_does_not_crash(void)
{
    Frame f = make_frame(0xFF, 0, 0, 0x00);

    RingBuffer task_rb;
    handle_incoming_frame(&task_rb, &f);

    /* success = no crash */
    TEST_ASSERT_TRUE(1);
}

/* -------- DATA CHUNK invalid task -------- */

void test_msg_data_chunk_invalid_task(void)
{
    Frame f = make_frame(DATA_CHUNK, 255, 0, 0x00);
    RingBuffer task_rb;
    int ret = msg_data_chunk(&task_rb, &f);

    TEST_ASSERT_EQUAL(-1, ret);
}

/* =========================
 * MAIN
 * ========================= */

int main(void)
{
    UNITY_BEGIN();

    RUN_TEST(test_msg_open_task_creates_task);
    RUN_TEST(test_msg_data_chunk_routes_to_task);
    RUN_TEST(test_handle_incoming_frame_unknown_type_does_not_crash);
    RUN_TEST(test_msg_data_chunk_invalid_task);
    return UNITY_END();
}