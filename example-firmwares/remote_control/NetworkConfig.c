#include "eai/network/Network.h"
#include "eai/network/MqttBroker.h"

networkCredentials_t networkCredentials = {.ssid = "SSID", .password = "password"};
mqttBrokerHost_t mqttHost = {.ip = "0.0.0.0", .port = "1883", .userID = "", .password = ""};
