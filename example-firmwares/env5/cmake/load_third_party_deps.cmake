include(FetchContent)

macro(add_runtime_enV5 tag)
    set(EAI_RUNTIME_FETCH_FROM_GIT on)
    set(EAI_RUNTIME_FETCH_FROM_GIT_TAG ${tag})
    include(${CMAKE_SOURCE_DIR}/cmake/eai_runtime_import.cmake)
endmacro()

macro(add_unity)
    FetchContent_Declare(
            unity
            GIT_REPOSITORY https://github.com/ThrowTheSwitch/Unity.git
            GIT_TAG v2.5.2
            OVERRIDE_FIND_PACKAGE)
    FetchContent_MakeAvailable(unity)
    find_package(unity)
endmacro()

macro(add_rp2_lib)
    FetchContent_Declare(
        rp2_lib
        GIT_REPOSITORY https://github.com/AErbsloeh/rp2_runtime_library/
        GIT_TAG main
    )
    FetchContent_MakeAvailable(rp2_lib)
endmacro()

macro(add_ctest)
    include(CTest)
endmacro()
