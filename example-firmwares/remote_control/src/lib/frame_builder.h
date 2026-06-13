#include "frame.h"
#include <stdint.h>

int frame_builder_return(Frame *frame, uint8_t flags, uint8_t return_code, uint8_t transaction_id);

int frame_builder_data_chunk(Frame *frame, uint8_t flags, uint8_t *data, uint16_t data_len,
                             uint8_t transaction_id, uint8_t starting_data_id, uint64_t max_chunk_size);

int frame_builder_open_task(Frame *frame, uint8_t transaction_id, uint8_t flags, uint8_t function_id);