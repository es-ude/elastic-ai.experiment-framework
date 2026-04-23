# **RCP Specification**
**Transport**: USB UART (8N1)
**Endianness**: Little-endian
**Max Chunk Size**: Configurable (32-65535 bytes, default 256)
**Checksum**: Optional CRC-8 (Polynomial: 0x07)

---

### **Message Header (6 bytes)**
| Field       | Size (bytes) | Description                                  |
|-------------|--------------|----------------------------------------------|
| sync        | 1            | Sync byte (0xAA)                             |
| type        | 1            | Message type ID                              |
| flags       | 1            | Bitfield (see below)                         |
| msg_id      | 1            | Message ID (0-255)                           |
| payload_len | 2            | Payload length (little-endian)               |

---

### **Message Types**
| ID (Hex) | Message Type   |
|----------|----------------|
| 0x01     | IMMEDIATE_CALL |
| 0x02     | RETURN         |
| 0x03     | DATA_CHUNK     |
| 0x04     | OPEN_STREAM    |
| 0x05     | CLOSE_STREAM   |
| 0x06     | ACK            |
| 0x07     | NAK            |
| 0x08     | HANDSHAKE      |

---

### **Flags Bitfield**
| Bit Index | Field    |
|-----------|----------|
| 0         | NEED_ACK |
| 1         | HAS_CRC  |
| 2         | reserved |
| 3         | reserved |
| 4         | reserved |
| 5         | reserved |
| 6         | reserved |
| 7         | reserved |

---

# **Message Specification**

### **IMMEDIATE_CALL:**
```
sync    type    flags   msg_id  payload_len |    fn_ptr      number of arguments    arguments      checksum (if enabled)
AA      01      ...     ...     ...         |    ...         ...                    ...            ...
```


---

### **RETURN:**
```
sync    type    flags   msg_id  payload_len |   code    function_id    msg_id   checksum (if enabled)
AA      02      ...     ...     1           |   ...     ...            ...      ...

ReturnCode: 0=Success, 1=Error, 2=Invalid Function
```

---

### **DATA_CHUNK:**
```
sync    type    flags   msg_id  payload_len |   data_id     data    checksum (if enabled)
AA      03      ...     ...     ...         |   ...         ...     ...
```

---

### **OPEN_STREAM:**
```
sync    type    flags   msg_id  payload_len |   checksum (if enabled)
AA      04      ...     ...      ...        |   ...
```

---

### **CLOSE_STREAM:**
```
sync    type    flags   msg_id  payload_len |   checksum (if enabled)
AA      05      ...     ...     ...         |   ...
```

---

### **ACK:**
```
sync    type    flags   msg_id  payload_len |   checksum (if enabled)
AA      06      ...     ...     ...         |   ...
```

---

### **NACK:**
```
sync    type    flags   msg_id  payload_len |   checksum (if enabled)
AA      07      ...     ...     ...         |   ...
```

---

### **HANDSHAKE:**
```
sync    type    flags   msg_id  payload_len |   version     capabilities    checksum (if enabled)
AA      08      ...     ...     ...         |   ...         ...             ...
```

---

# **State Machines**

### **IMMEDIATE_CALL:**
```
PC:
[Send IMMEDIATE_CALL] → [yield] → [Process RETURN]

EXPERIMENT PLATFORM:
[Receive IMMEDIATE_CALL] → [Process] → [Send RETURN]
                                     → [Send OPEN_STREAM] → [Send DATA_CHUNK]* → [Send CLOSE_STREAM] → [Send RETURN]
```

```mermaid
sequenceDiagram
  PC->>+ExpPlatform: Send IMMEDIATE_CALL
  opt
      PC->>ExpPlatform: Send OPEN_STREAM
      PC->>ExpPlatform: Send DATA_CHUNK
  end
  alt
    ExpPlatform-->>PC: Send RETURN
  else
    ExpPlatform-->>PC: Send OPEN_STREAM
    loop
      ExpPlatform-->>PC: Send DATA_CHUNK
    end
    ExpPlatform-->>PC: Send CLOSE_STREAM
    ExpPlatform-->>PC: Send RETURN
  end
```


---

### **OPEN_STREAM:**
```
PC:
[Send OPEN_STREAM]      → [Send DATA_CHUNK]*    → [Process RETURN]
                                                → [Process OPEN_STREAM] → [Process DATA_CHUNK]* → [Process CLOSE_STREAM] → [Process RETURN]

EXPERIMENT PLATFORM:
[Receive OPEN_STREAM]   → [Process DATA_CHUNK]* → [Send RETURN]
                                                → [Send OPEN_STREAM]    → [Send DATA_CHUNK]*    → [Send STREAM_CLOSE]    → [Send RETURN] 
```

---


# **TO-DO**

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

