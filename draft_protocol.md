Here's the complete, final protocol specification incorporating all refinements for unlimited data transfers and streaming:

---

### **Final Protocol Specification v4.0**
**Transport**: USB UART (8N1)
**Endianness**: Little-endian
**Max Chunk Size**: Configurable (32-65535 bytes, default 256)
**Checksum**: Optional CRC-8 (Polynomial: 0x07)

---

### **Message Type IDs**
| Category          | Message Type               | ID (Hex) | ID (Dec) | Notes                          |
|-------------------|----------------------------|----------|----------|--------------------------------|
| **Core Calls**    | IMMEDIATE_CALL             | 0x01     | 1        |                                |
|                   | QUEUE_CALL                 | 0x02     | 2        |                                |
|                   | LOOP_START                 | 0x03     | 3        |                                |
|                   | LOOP_STOP                  | 0x04     | 4        |                                |
|                   | RUN_QUEUE                  | 0x05     | 5        |                                |
|                   | QUEUE_START                | 0x06     | 6        |                                |
|                   | QUEUE_END                  | 0x07     | 7        |                                |
| **Data Transfer** | DATA_START                 | 0x0E     | 14       | Initiate data transfer         |
|                   | DATA_CHUNK                 | 0x0F     | 15       | Data chunk                    |
|                   | DATA_END                   | 0x10     | 16       | Complete data transfer        |
| **Streaming**     | STREAM_OPEN                | 0x11     | 17       | Open stream channel           |
|                   | STREAM_CLOSE               | 0x12     | 18       | Close stream channel          |
| **System**        | ACK                        | 0x0A     | 10       |                                |
|                   | NAK                        | 0x0B     | 11       |                                |
|                   | HANDSHAKE                  | 0x0C     | 12       |                                |

---

### **Base Message Header (5-7 bytes)**
| Field       | Size (bytes) | Description                                  |
|-------------|--------------|----------------------------------------------|
| sync        | 1            | Sync byte (0xAA)                             |
| type        | 1            | Message type ID                              |
| flags       | 1            | Bitfield (see below)                         |
| msg_id      | 1            | Message ID (0-255)                           |
| payload_len | 2            | Payload length (little-endian)               |
| crc8        | 1*           | CRC-8 checksum (if enabled)                  |

*Flags Bitfield*:
```
Bit 0: NEED_ACK (1 = require ACK/NAK)
Bit 1: HAS_CRC (1 = CRC-8 included)
Bits 2-7: Reserved
```

---

### **Complete Message Specifications**

#### **1. IMMEDIATE_CALL (0x01)**
**Request**:
```
AA 01 [Flags] [MsgID] [PayloadLen] [FuncID:1] [ArgCount:1] [Args...] [CRC]
```
- **Small args**: Inline in payload
- **Large args**: Replace with `[DataID:1]`

**Response**:
```
AA 01 00 [MsgID] [PayloadLen] [ReturnCode:1] [ReturnData...] [CRC]
```
- `ReturnCode`: 0=Success, 1=Error, 2=Invalid Function
- **Small returns**: Inline in payload
- **Large returns**: `[DataID:1]` followed by DATA_START

#### **2. QUEUE_CALL (0x02)**
```
AA 02 [Flags] [MsgID] [PayloadLen] [FuncID:1] [ArgCount:1] [Args...] [CRC]
```
- Same argument handling as IMMEDIATE_CALL

#### **3. LOOP_START (0x03)**
```
AA 03 [Flags] [MsgID] [PayloadLen] [LoopID:1] [CRC]
```

#### **4. LOOP_STOP (0x04)**
```
AA 04 [Flags] [MsgID] [PayloadLen] [LoopID:1] [CRC]
```

#### **5. RUN_QUEUE (0x05)**
```
AA 05 [Flags] [MsgID] [PayloadLen] [Iterations:4] [CRC]
```
- `Iterations`: 0 = infinite

#### **6. QUEUE_START (0x06)**
```
AA 06 [Flags] [MsgID] [PayloadLen] [QueueID:1] [CRC]
```

#### **7. QUEUE_END (0x07)**
```
AA 07 [Flags] [MsgID] [PayloadLen] [QueueID:1] [Status:1] [CRC]
```
- `Status`: 0=Success, 1=Error, 2=Cancelled

#### **8. DATA_START (0x0E)**
```
AA 0E [Flags] [MsgID] [PayloadLen] [DataID:1] [TotalSize:4] [CRC]
```
- Initiates data transfer
- `DataID`: 1-255 (0 reserved)
- `TotalSize`: 0 = unknown (streaming)

#### **9. DATA_CHUNK (0x0F)**
```
AA 0F [Flags] [MsgID] [PayloadLen] [DataID:1] [ChunkID:2] [Data:N] [CRC]
```
- Contains partial data
- `ChunkID`: 0-65535

#### **10. DATA_END (0x10)**
```
AA 10 [Flags] [MsgID] [PayloadLen] [DataID:1] [Status:1] [CRC]
```
- Completes data transfer
- `Status`: 0=Success, 1=Error

#### **11. STREAM_OPEN (0x11)**
```
AA 11 [Flags] [MsgID] [PayloadLen] [StreamID:1] [Direction:1] [CRC]
```
- `Direction`: 0=Input, 1=Output

#### **12. STREAM_CLOSE (0x12)**
```
AA 12 [Flags] [MsgID] [PayloadLen] [StreamID:1] [Status:1] [CRC]
```

#### **13. ACK (0x0A)**
```
AA 0A 00 [MsgID] 00 00 [CRC]
```

#### **14. NAK (0x0B)**
```
AA 0B 00 [MsgID] 00 01 [ErrorCode] [CRC]
```
- `ErrorCode`: 1=Checksum fail, 2=Invalid type, 3=Queue full, 4=Data error

#### **15. HANDSHAKE (0x0C)**
**Request**:
```
AA 0C [Flags] [MsgID] [PayloadLen] [Version] [MaxChunkSize] [Capabilities] [CRC]
```
**Response**:
```
AA 0C 00 [MsgID] [PayloadLen] [AgreedChunkSize] [Status] [CRC]
```

---

### **Data Transfer Examples**

#### **1. Small Argument Call (Inline)**
```
HOST → EMBEDDED:
AA 01 01 05 00 03 00 05 02 01 02 [CRC]
[MsgID=5, FuncID=5, ArgCount=2, Args=[1,2]]
```

#### **2. Large Argument Call**
```
1. HOST → EMBEDDED:
   AA 0E 01 05 00 05 00 00 00 00 00 [CRC]
   [DATA_START DataID=5, Size=1024]

2. HOST → EMBEDDED:
   AA 0F 01 05 00 04 00 00 00 00 00 [CRC]
   AA 0F 01 05 01 04 00 00 00 00 00 [CRC]
   ... [More chunks]

3. HOST → EMBEDDED:
   AA 10 01 05 00 01 00 00 [CRC]
   [DATA_END DataID=5, Status=0]

4. HOST → EMBEDDED:
   AA 01 01 06 00 02 00 05 01 05 [CRC]
   [IMMEDIATE_CALL FuncID=5, ArgCount=1, Arg=DataID=5]
```

#### **3. Call with Stream Return**
```
1. HOST → EMBEDDED:
   AA 01 01 05 00 01 00 03 [CRC]
   [IMMEDIATE_CALL FuncID=3]

2. EMBEDDED → HOST:
   AA 11 00 06 00 02 00 01 01 [CRC]
   [STREAM_OPEN StreamID=1, Direction=Output]

3. EMBEDDED → HOST:
   AA 0F 00 06 00 04 00 01 00 00 00 [CRC]
   AA 0F 00 06 01 04 00 01 00 00 00 [CRC]
   ... [Stream data chunks]

4. EMBEDDED → HOST:
   AA 12 00 06 00 02 00 01 00 [CRC]
   [STREAM_CLOSE StreamID=1, Status=0]
```

#### **4. Scheduled Execution with Large Data**
```
1. HOST → EMBEDDED:
   AA 0E 01 05 00 05 00 00 00 00 00 [CRC]
   ... [Data chunks]
   AA 10 01 05 00 01 00 00 [CRC]

2. HOST → EMBEDDED:
   AA 02 01 06 00 02 00 05 01 05 [CRC]
   [QUEUE_CALL FuncID=5, ArgCount=1, Arg=DataID=5]

3. HOST → EMBEDDED:
   AA 05 01 07 00 04 00 00 00 [CRC]
   [RUN_QUEUE Iterations=0]

4. EMBEDDED → HOST:
   AA 06 00 07 00 01 00 01 [CRC]
   ... [Execution]
   AA 07 00 07 00 02 00 01 00 [CRC]
```

---

### **Protocol State Machine**
```
HOST SIDE:
[Idle] → [Send Message/Data] → [Wait ACK*] → [Process Response] → [Idle]

EMBEDDED SIDE:
[Idle] → [Receive Message/Data] → [Validate*] → [Process/Buffer] → [Send ACK*] → [Idle]
```

---

### **Error Handling**
| Error Condition       | Action                                  |
|-----------------------|-----------------------------------------|
| Invalid DataID        | NAK with error code                     |
| Missing chunk         | Request retransmit                      |
| Stream overflow       | Close stream with error status          |
| Memory exhaustion     | Abort transfer with error               |
| Invalid FuncID        | Skip call, continue execution           |

---

### **Implementation Guidelines**

#### **1. Data Manager**
```c
typedef struct {
    uint8_t data_id;
    uint32_t total_size;
    uint32_t received;
    uint8_t* buffer;
    bool is_stream;
} DataTransfer;

typedef struct {
    uint8_t stream_id;
    uint8_t direction;
    uint32_t bytes_transferred;
} StreamChannel;
```

#### **2. Call Processing**
```python
def process_call(msg):
    if msg.arg_count > 0 and msg.args[0] == DATA_ID_MARKER:
        data_id = msg.args[1]
        wait_for_data_completion(data_id)
        args = get_data_buffer(data_id)
    else:
        args = msg.args[2:]
    execute_function(msg.func_id, args)
```

#### **3. Memory Management**
- Pre-allocate buffers for known data sizes
- Use circular buffers for streams
- Implement garbage collection for completed transfers

---

### **Performance Characteristics**
| Data Size      | Transfer Method         | Overhead       | Use Case               |
|----------------|-------------------------|----------------|------------------------|
| <64 bytes      | Inline                  | 5-7 bytes      | Simple calls           |
| 64-65535 bytes | Single DATA_CHUNK      | 8-10 bytes     | Medium transfers       |
| >65535 bytes   | Multi-chunk             | 8-10 bytes/chunk | Large transfers      |
| Streams        | Continuous chunks       | 8-10 bytes/chunk | Real-time data       |

---

### **Final Notes**
This specification provides:
1. **Unlimited data transfers** for all call types
2. **Unified chunking mechanism** for both arguments and returns
3. **First-class streaming support**
4. **Efficient small data handling**
5. **Clean separation of concerns**
6. **Comprehensive error handling**

