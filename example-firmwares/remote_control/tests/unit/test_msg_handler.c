#include "unity.h"

#include "msg_handler.h"
#include "task_manager.h"
#include "frame.h"
#include "msg_types.h"
#include "sender.h"

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
uint8_t out_storage[1024];

Transport transport_protocol = {0};
Sender tx;

RingBuffer task_rb;
uint8_t task_rb_storage[1024];

static TaskManager task_manager;
static TaskContext ctx;

void setUp(void)
{
    ringbuffer_init(&task_rb, task_rb_storage, 1024, sizeof(Task *));
    ringbuffer_init(&out_rb, out_storage, 1024, sizeof(Frame));

    ctx = (TaskContext){.outgoing_rb = &out_rb};

    init_task_manager(&out_rb, &task_manager, ctx);

    tx = (Sender){
        .transport = &transport_protocol,
        .outgoing_rb = &out_rb,
    };
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

    int id = msg_open_task(&f, &task_manager);

    TEST_ASSERT_TRUE(id > 0);

    Task *t = get_task_by_id(id, &task_manager);

    TEST_ASSERT_NOT_NULL(t);
    TEST_ASSERT_EQUAL(TASK_STATUS_PREPARING, t->status);
}

void test_close_task(void)
{
    Frame open = make_frame(OPEN_TASK, 4, 0, 0x00);
    int id = msg_open_task(&open, &task_manager);

    TEST_ASSERT_EQUAL_INT(4, id);
    TEST_ASSERT_TRUE(get_task_by_id(id, &task_manager)->status != TASK_STATUS_IDLE);

    Frame close = make_frame(CLOSE_TASK, id, 0, 0x00);
    int ret = msg_close_task(&close, &task_manager);

    TEST_ASSERT_EQUAL(id, ret);

    Task *t = get_task_by_id(id, &task_manager);
    TEST_ASSERT_TRUE(t->status == TASK_STATUS_IDLE);
    TEST_ASSERT_EQUAL_INT(0, t->input_data_len);
    TEST_ASSERT_EQUAL_INT(0, t->output_data_len);
    TEST_ASSERT_NULL(t->funcs);
}

/* -------- DATA_CHUNK -------- */

static int fake_called = 0;

static void fake_rn(Task *self)
{
    fake_called++;
    TEST_ASSERT_EQUAL_UINT8(0x99, self->input_data[0]);
}

void test_msg_data_chunk_routes_to_task(void)
{
    fake_called = 0;

    Frame open = make_frame(OPEN_TASK, 2, 0, 0x00);
    int id = msg_open_task(&open, &task_manager);

    TEST_ASSERT_EQUAL_INT(2, id);

    Task *t = get_task_by_id(id, &task_manager);
    t->funcs = &(TaskDefinition){0};
    t->funcs->handle = fake_rn;

    Frame data = make_frame(DATA_CHUNK, id, 0, 0x99);

    int ret = msg_data_chunk(&task_rb, &data, &task_manager);
    TEST_ASSERT_EQUAL(id, ret);

    process_tasks(&task_rb, &out_rb, &task_manager);

    TEST_ASSERT_EQUAL(1, fake_called);
}

/* -------- UNKNOWN MESSAGE -------- */

void test_handle_incoming_frame_unknown_type_does_not_crash(void)
{
    Frame f = make_frame(0xFF, 0, 0, 0x00);

    handle_incoming_frame(&task_rb, &f, &task_manager);

    TEST_ASSERT_EQUAL(0, ringbuffer_size(&task_rb));
}

/* -------- DATA CHUNK invalid task -------- */

void test_msg_data_chunk_invalid_task(void)
{
    Frame f = make_frame(DATA_CHUNK, 255, 0, 0x00);

    int ret = msg_data_chunk(&task_rb, &f, &task_manager);

    TEST_ASSERT_EQUAL(-1, ret);
}

void test_msg_open_and_close_task(void)
{
    Frame f = make_frame(OPEN_TASK, 3, 0, 0x00);
    int id = msg_open_task(&f, &task_manager);
    TEST_ASSERT_EQUAL_INT(3, id);

    Frame close = make_frame(CLOSE_TASK, id, 0, 0x00);
    int ret = msg_close_task(&close, &task_manager);

    TEST_ASSERT_EQUAL_INT(0, ret);

    Task *t = get_task_by_id(id, &task_manager);
    TEST_ASSERT_NOT_NULL(t);
    TEST_ASSERT_EQUAL(TASK_STATUS_IDLE, t->status);
    TEST_ASSERT_EQUAL_INT(0, t->input_data_len);
    TEST_ASSERT_EQUAL_INT(0, t->output_data_len);
    TEST_ASSERT_NULL(t->funcs);
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
    RUN_TEST(test_close_task);
    return UNITY_END();
}