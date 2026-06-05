#include "unity.h"

#include "transport.h"

#include <pthread.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

/* =========================
 * TEST FIXTURES
 * ========================= */

static const uint16_t TEST_PORT = 6000;

static volatile int ready = 0;
static volatile int running = 1;

static Transport transport = {0};
static Transport *server = NULL;

static int client_sock = -1;
static pthread_t server_tid;

/* =========================
 * SERVER THREAD
 * ========================= */

static void *server_thread(void *arg)
{
    Transport *t = (Transport *)arg;

    TransportConfig cfg = {
        .type = TRANSPORT_SOCKET,
        .cfg.socket.port = 6000};

    transport_init(t, cfg); // nur listen()
    ready = 1;

    transport_accept(t); // BLOCKING wait for client

    while (running)
    {
        sleep(0.1);
    }

    return NULL;
}

/* =========================
 * CLIENT HELPERS
 * ========================= */

static int create_client(uint16_t port)
{
    int sock = socket(AF_INET, SOCK_STREAM, 0);

    struct sockaddr_in addr = {0};
    addr.sin_family = AF_INET;
    addr.sin_port = htons(port);
    inet_pton(AF_INET, "127.0.0.1", &addr.sin_addr);

    printf("Connecting with server...\n");
    fflush(stdout);
    connect(sock, (struct sockaddr *)&addr, sizeof(addr));
    printf("Connected with server!\n");
    fflush(stdout);
    return sock;
}

static void client_send(int sock, uint8_t b)
{
    send(sock, &b, 1, 0);
}

static uint8_t client_recv(int sock)
{
    uint8_t b = 0;
    recv(sock, &b, 1, 0);
    return b;
}

/* =========================
 * SETUP / TEARDOWN
 * ========================= */

void setUp(void)
{
    int rc;

    running = 1;
    rc = pthread_create(&server_tid, NULL, server_thread, &transport);

    TEST_ASSERT_EQUAL_INT(0, rc);

    /*
     * Give server time to:
     * socket()
     * bind()
     * listen()
     * accept()
     */
    while (!ready)
    {
        sleep(1);
        printf("test server not ready\n");
        fflush(stdout);
    }

    client_sock = create_client(TEST_PORT);

    TEST_ASSERT_TRUE(client_sock >= 0);

    server = &transport;

    TEST_ASSERT_NOT_NULL(server);
}

void tearDown(void)
{
    running = 0;
    if (client_sock >= 0)
    {
        close(client_sock);
        client_sock = -1;
    }

    if (server)
    {
        server->destroy(server);
        server = NULL;
    }
    pthread_join(server_tid, NULL);
}

/* =========================
 * TESTS
 * ========================= */
void test_server_receives_byte_from_client(void)
{
    printf("Starting task1\n");
    fflush(stdout);
    client_send(client_sock, 0x42);
    uint8_t b = server->recv_byte(server);
    TEST_ASSERT_EQUAL_UINT8(0x42, b);
    printf("received byte %x\n", b);
    fflush(stdout);
}

void test_server_sends_byte_to_client(void)
{
    printf("Starting task2\n");
    fflush(stdout);
    server->send_byte(server, 0x99);

    uint8_t b = client_recv(client_sock);

    TEST_ASSERT_EQUAL_UINT8(0x99, b);
}

void test_bidirectional_communication(void)
{
    printf("Starting task3\n");
    fflush(stdout);
    client_send(client_sock, 0x10);
    client_send(client_sock, 0x20);

    uint8_t a = server->recv_byte(server);
    uint8_t b = server->recv_byte(server);

    TEST_ASSERT_EQUAL_UINT8(0x10, a);
    TEST_ASSERT_EQUAL_UINT8(0x20, b);

    server->send_byte(server, 0x55);

    uint8_t r = client_recv(client_sock);

    TEST_ASSERT_EQUAL_UINT8(0x55, r);
}

void test_server_receives_x_bytes_from_client(void)
{
    printf("Starting task4\n");
    fflush(stdout);
    uint8_t bytes_to_send[] = {0x01, 0x02, 0x03, 0x04, 0x05};

    for (size_t i = 0; i < sizeof(bytes_to_send); i++)
    {
        client_send(client_sock, bytes_to_send[i]);
    }

    for (size_t i = 0; i < sizeof(bytes_to_send); i++)
    {
        uint8_t b = server->recv_byte(server);
        TEST_ASSERT_EQUAL_UINT8(bytes_to_send[i], b);
        printf("received byte %x\n", b);
        fflush(stdout);
    }
}

/* =========================
 * MAIN
 * ========================= */

int main(void)
{
    UNITY_BEGIN();

    RUN_TEST(test_server_receives_byte_from_client);
    sleep(1);
    RUN_TEST(test_server_sends_byte_to_client);
    sleep(1);
    RUN_TEST(test_bidirectional_communication);

    RUN_TEST(test_server_receives_x_bytes_from_client);

    return UNITY_END();
}