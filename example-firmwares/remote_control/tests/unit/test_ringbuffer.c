#include "unity.h"
#include "ringbuffer_internal.h"
#include "frame.h"

#include <string.h>
#include <stdint.h>

#define CAPACITY 4

static uint8_t storage[CAPACITY * sizeof(Frame)];
static RingBuffer rb;

/* =========================================================
 * SETUP / TEARDOWN
 * ========================================================= */

void setUp(void)
{
    ringbuffer_init(&rb, storage, CAPACITY, sizeof(Frame));
}

void tearDown(void)
{
}

/* --------------------------
 * HELPER
 * -------------------------- */
static void push_int(uint8_t value)
{
    Frame a;
    a.header.start_byte = value;
    ringbuffer_push(&rb, &a);
}

static uint8_t pop_int(void)
{
    Frame a;
    ringbuffer_pop(&rb, &a);
    return a.header.start_byte;
}

/* --------------------------
 * TESTS
 * -------------------------- */

void test_ringbuffer_starts_empty(void)
{
    TEST_ASSERT_TRUE(ringbuffer_empty(&rb));
    TEST_ASSERT_FALSE(ringbuffer_full(&rb));
}

void test_ringbuffer_push_and_pop(void)
{
    Frame a;
    a.header.start_byte = 0xFF;
    TEST_ASSERT_TRUE(ringbuffer_push(&rb, &a));
    TEST_ASSERT_FALSE(ringbuffer_empty(&rb));

    Frame b;
    TEST_ASSERT_TRUE(ringbuffer_pop(&rb, &b));
    TEST_ASSERT_EQUAL_INT(0xFF, b.header.start_byte);

    TEST_ASSERT_TRUE(ringbuffer_empty(&rb));
}

void test_ringbuffer_fifo_order(void)
{
    int a = 1, b = 2, c = 3;

    push_int(a);
    push_int(b);
    push_int(c);

    TEST_ASSERT_EQUAL_INT(1, pop_int());
    TEST_ASSERT_EQUAL_INT(2, pop_int());
    TEST_ASSERT_EQUAL_INT(3, pop_int());
}

void test_ringbuffer_full_condition(void)
{
    push_int(1);
    push_int(2);
    push_int(3);

    TEST_ASSERT_TRUE(ringbuffer_full(&rb));

    Frame a;
    TEST_ASSERT_FALSE(ringbuffer_push(&rb, &a));
}

void test_ringbuffer_wrap_around(void)
{
    // fill to near capacity
    push_int(1);
    push_int(2);
    push_int(3);

    pop_int(); // remove 1
    pop_int(); // remove 2

    // now wrap around should work
    Frame a;
    a.header.start_byte = 10;
    TEST_ASSERT_TRUE(ringbuffer_push(&rb, &a));

    TEST_ASSERT_EQUAL_INT(3, pop_int());
    TEST_ASSERT_EQUAL_INT(10, pop_int());
}

int main(void)
{
    UNITY_BEGIN();

    RUN_TEST(test_ringbuffer_starts_empty);
    RUN_TEST(test_ringbuffer_push_and_pop);
    RUN_TEST(test_ringbuffer_fifo_order);
    RUN_TEST(test_ringbuffer_full_condition);
    RUN_TEST(test_ringbuffer_wrap_around);

    return UNITY_END();
}