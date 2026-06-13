#include "unity.h"

#include "task_manager.h"
#include "ringbuffer.h"
#include "frame.h"
#include "msg_types.h"

#include <string.h>
#include <stdlib.h>

/* =========================
 * TEST FIXTURES
 * ========================= */

#define RB_CAPACITY 8

static Task *rb_storage[RB_CAPACITY];
static RingBuffer task_rb;

static Frame out_storage[RB_CAPACITY];
static RingBuffer out_rb;

/* fake frame for testing */
static Frame make_frame(uint8_t payload0, uint8_t flags, uint8_t tx_id)
{
    Frame f;
    memset(&f, 0, sizeof(f));

    f.header.start_byte = 0xAA;
    f.header.message_type = 1;
    f.header.flags = flags;
    f.header.transaction_id = tx_id;
    f.header.payload_len = 1;
    f.payload[0] = payload0;

    return f;
}

/* =========================
 * SETUP
 * ========================= */

static TaskManager task_manager;
static TaskContext ctx;

void setUp(void)
{
    ringbuffer_init(&task_rb, rb_storage, RB_CAPACITY, sizeof(Task *));
    ringbuffer_init(&out_rb, out_storage, RB_CAPACITY, sizeof(Frame));

    init_task_manager(&out_rb, &task_manager); // global task pool reset
}

void tearDown(void)
{
}

/* =========================
 * TESTS
 * ========================= */

void test_init_tasks_creates_idle_tasks(void)
{
    Task *t = get_free_task(&task_manager);

    TEST_ASSERT_NOT_NULL(t);
    TEST_ASSERT_EQUAL(TASK_STATUS_IDLE, t->status);
}

void test_enqueue_task_pushes_into_ringbuffer(void)
{
    Task *t = get_free_task(&task_manager);
    TEST_ASSERT_NOT_NULL(t);

    enqueue_task(&task_rb, t);

    Task *out;
    TEST_ASSERT_TRUE(ringbuffer_pop(&task_rb, &out));
    TEST_ASSERT_EQUAL(t->id, out->id);
}

void test_start_task_sets_running_and_enqueues(void)
{
    Task *t = get_free_task(&task_manager);
    TEST_ASSERT_NOT_NULL(t);

    int rc = start_task(&task_rb, t);

    TEST_ASSERT_TRUE(rc);
    TEST_ASSERT_EQUAL(TASK_STATUS_RUNNING, t->status);

    Task *popped;
    TEST_ASSERT_TRUE(ringbuffer_pop(&task_rb, &popped));
}

void test_finish_resets_task(void)
{
    Task *t = get_free_task(&task_manager);
    TEST_ASSERT_NOT_NULL(t);

    t->status = TASK_STATUS_RUNNING;
    t->ctx.input_data_len = 3;

    bool ok = finish_task(t, &task_manager);

    TEST_ASSERT_TRUE(ok);
    TEST_ASSERT_EQUAL(TASK_STATUS_IDLE, t->status);
    TEST_ASSERT_EQUAL_INT(0, t->ctx.input_data_len);
}

/* -------- receive (basic append) -------- */

void test_receive_datachunk_accumulates_data(void)
{
    Task *t = get_free_task(&task_manager);
    TEST_ASSERT_NOT_NULL(t);
    Frame f = make_frame(0x42, 0, t->id);

    send_frame_to_task(&task_rb, t, &f);

    TEST_ASSERT_EQUAL_UINT8(0x42, t->ctx.input_data[0]);
}

/* -------- process_tasks -------- */

static void dummy_run(TaskContext *task_context)
{
    task_context->output_data[0] = 1;
}

void test_process_tasks_executes_task(void)
{
    TaskDefinition td = {0};
    Task *t = get_free_task(&task_manager);
    TEST_ASSERT_NOT_NULL(t);
    /* minimal setup */
    t->funcs = &td;
    t->funcs->handle = dummy_run;

    int result = start_task(&task_rb, t);
    TEST_ASSERT_TRUE(result);

    TEST_ASSERT_EQUAL_PTR(dummy_run, t->funcs->handle);
    fflush(stdout);

    process_tasks(&task_rb, &out_rb, &task_manager);

    TEST_ASSERT_EQUAL_INT(1, t->ctx.output_data[0]);
}

/* =========================
 * MAIN
 * ========================= */

int main(void)
{
    UNITY_BEGIN();

    RUN_TEST(test_init_tasks_creates_idle_tasks);
    RUN_TEST(test_enqueue_task_pushes_into_ringbuffer);
    RUN_TEST(test_start_task_sets_running_and_enqueues);
    RUN_TEST(test_finish_resets_task);
    RUN_TEST(test_receive_datachunk_accumulates_data);
    RUN_TEST(test_process_tasks_executes_task);

    return UNITY_END();
}