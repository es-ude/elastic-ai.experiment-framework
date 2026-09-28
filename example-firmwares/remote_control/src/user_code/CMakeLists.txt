target_sources(remote_lib PRIVATE
    task_definitions.c
    task_definition_host.c
)

if (ELASTIC_AI_TARGET STREQUAL "ENV5_2")
    
    target_sources(remote_lib PRIVATE
        task_definitions_pico.c
    )
endif()