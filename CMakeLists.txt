
get_filename_component(RS_DIR ${CMAKE_CURRENT_LIST_DIR} ABSOLUTE)
get_filename_component(binroot ${CMAKE_CURRENT_BINARY_DIR}/.. ABSOLUTE)
if(NOT DEFINED root)
	set(root ${RS_DIR})
endif()
message("# RediSearch root: " ${RS_DIR})
message("# RediSearch binroot: " ${binroot})

include(build/cmake/common.cmake)

#----------------------------------------------------------------------------------------------

option(RS_BUILD_STATIC "Build a static library" OFF)
# RS_BUILD_COORDINATOR
# RS_BUILD_COORD_OSS
# RS_BUILD_COORD_RLEC

option(USE_REDIS_ALLOCATOR "Use redis allocator" ON)
option(USE_COVERAGE "Build with coverage" OFF)
option(STATIC_LIBSTDCXX "Link libstdc++ statically" ON)

option(RS_RUN_TESTS "Build & Run RediSearch's tests" OFF)
option(USE_ASAN "Use AddressSanitizer (clang)" OFF)
option(USE_MSAN "Use MemorySanitizer (clang)" OFF)
option(USE_TSAN "Use ThreadSanitizer (clang)" OFF)

message("# RediSearch static libstdc++: " ${STATIC_LIBSTDCXX})

#----------------------------------------------------------------------------------------------

project(redisearch)

include(build/cmake/redisearch_cflags.cmake)
include(build/cmake/redisearch_debug.cmake)

#----------------------------------------------------------------------------------------------

set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} ${RS_C_FLAGS}")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} ${RS_CXX_FLAGS}")

set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} ${RS_EXE_FLAGS}")
set(CMAKE_SHARED_LINKER_FLAGS "${CMAKE_SHARED_LINKER_FLAGS} ${RS_SO_FLAGS} ${RS_VECSIM_SO_FLAGS}")
if (STATIC_LIBSTDCXX AND NOT (USE_ASAN OR USE_MSAN))
	set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} ${CMAKE_STATIC_LIBSTDCXX_FLAGS}")
	set(CMAKE_SHARED_LINKER_FLAGS "${CMAKE_SHARED_LINKER_FLAGS} ${CMAKE_STATIC_LIBSTDCXX_FLAGS}")
endif()

if (NOT RS_MODULE_NAME)
    set(RS_MODULE_NAME "search")
endif()
add_definitions(-DREDISEARCH_MODULE_NAME=\\"${RS_MODULE_NAME}\\")

add_definitions(-UNDEBUG)
add_definitions(-DGIT_VERSPEC=\\"${GIT_VERSPEC}\\")
add_definitions(-DRS_GIT_SHA=\\"${GIT_SHA}\\")
add_definitions(-DREDISMODULE_EXPERIMENTAL_API)
add_definitions(-D_GNU_SOURCE)
if (USE_REDIS_ALLOCATOR)
    add_definitions(-DREDIS_MODULE_TARGET)
endif()

#----------------------------------------------------------------------------------------------

include_directories(${PROJECT_SOURCE_DIR}/src)
include_directories(${PROJECT_SOURCE_DIR}/deps)
include_directories(${PROJECT_SOURCE_DIR}/deps/VectorSimilarity/src)
include_directories(${PROJECT_SOURCE_DIR})

add_subdirectory(deps/rmutil)
add_subdirectory(deps/friso)
add_subdirectory(deps/snowball)
add_subdirectory(deps/phonetics)
option(VECSIM_STATIC "Build as static library" ON)
option(VECSIM_BUILD_TESTS "Build vecsim tests" OFF)
add_subdirectory(deps/VectorSimilarity/src)

#----------------------------------------------------------------------------------------------

file(GLOB RS_SRC
    "src/*.c"
    "src/aggregate/*.c"
    "src/aggregate/expr/*.c"
    "src/aggregate/functions/*.c"
    "src/aggregate/reducers/*.c"
    "src/ext/*.c"
    "src/hll/*.c"
    "src/query_parser/v1/*.c"
    "src/query_parser/v2/*.c"
    "src/util/*.c"
    "src/trie/*.c"
    ${RS_DEBUG_SRC}

    "deps/cndict/cndict_data.c"
    "deps/libnu/*.c"
    "deps/miniz/*.c"
    "deps/base64/*.c"
    "deps/thpool/*.c"
    "deps/triemap/*.c"
    "deps/geohash/*.c")

add_library(rscore OBJECT ${RS_SRC})

set(FINAL_OBJECTS
    $<TARGET_OBJECTS:rscore>
    $<TARGET_OBJECTS:rmutil>
    $<TARGET_OBJECTS:friso>
    $<TARGET_OBJECTS:snowball>
    $<TARGET_OBJECTS:metaphone>)

#----------------------------------------------------------------------------------------------

if (RS_BUILD_COORDINATOR)
    if (RS_BUILD_COORD_OSS)
        add_library(redisearch-oss STATIC ${RS_SRC} ${FINAL_OBJECTS} src/module-init/module-init.c)
        target_compile_definitions(redisearch-oss PRIVATE RS_NO_ONLOAD RS_NO_RMAPI RS_CLUSTER_OSS)
        set_target_properties(redisearch-oss PROPERTIES OUTPUT_NAME "redisearch-oss")
        if (APPLE)
            set_target_properties(redisearch-oss PROPERTIES LINK_FLAGS "-undefined dynamic_lookup")
        endif()

    elseif (RS_BUILD_COORD_RLEC)
        add_library(redisearch-enterprise STATIC ${RS_SRC} ${FINAL_OBJECTS} src/module-init/module-init.c)
        target_compile_definitions(redisearch-enterprise PRIVATE RS_NO_ONLOAD RS_NO_RMAPI RS_CLUSTER_ENTERPRISE)
        set_target_properties(redisearch-enterprise PROPERTIES OUTPUT_NAME "redisearch-enterprise")
        if (APPLE)
            set_target_properties(redisearch-enterprise PROPERTIES LINK_FLAGS "-undefined dynamic_lookup")
        endif()
    endif()

elseif (RS_BUILD_STATIC)
    add_library(redisearchS STATIC ${FINAL_OBJECTS} src/module-init/module-init.c)
    target_compile_definitions(redisearchS PRIVATE RS_NO_ONLOAD RS_NO_RMAPI)
    set_target_properties(redisearchS PROPERTIES OUTPUT_NAME "redisearch")

    add_library(redisearch SHARED ${FINAL_OBJECTS} src/module-init/module-init.c)
    target_link_libraries(redisearch dl m)
    set_target_properties(redisearch PROPERTIES LINKER_LANGUAGE CXX)
    set_target_properties(redisearch PROPERTIES PREFIX "")
    set_target_properties(redisearch PROPERTIES SUFFIX ".so")
    add_ldflags(redisearch "-Wl,--enable-new-dtags -Wl,-rpath,\$ORIGIN")

    set(RS_TEST_MODULE redisearchS)
    set(RS_TEST_MODULE_SO $<TARGET_FILE:redisearch>)

else() # OSS RediSearch
    add_library(redisearch SHARED ${FINAL_OBJECTS} src/module-init/module-init.c)
    target_link_libraries(redisearch VectorSimilarity dl m)
    set_target_properties(redisearch PROPERTIES LINKER_LANGUAGE CXX)
    set_target_properties(redisearch PROPERTIES PREFIX "")
    set_target_properties(redisearch PROPERTIES SUFFIX ".so")
    add_ldflags(redisearch "-Wl,--enable-new-dtags -Wl,-rpath,\$ORIGIN")

    if (APPLE)
        set_target_properties(redisearch PROPERTIES LINK_FLAGS "-undefined dynamic_lookup")
    endif()

	if (NOT CMAKE_BUILD_TYPE STREQUAL DEBUG)
		if (NOT APPLE)
			add_custom_command(TARGET redisearch POST_BUILD
				COMMAND cp $<TARGET_FILE:redisearch> $<TARGET_FILE:redisearch>.debug
				COMMAND objcopy --add-gnu-debuglink $<TARGET_FILE:redisearch>.debug $<TARGET_FILE:redisearch>
				COMMAND ${CMAKE_STRIP} -g $<TARGET_FILE:redisearch>)
		else()
			add_custom_command(TARGET redisearch POST_BUILD
				COMMAND cp $<TARGET_FILE:redisearch> $<TARGET_FILE:redisearch>.debug)
		endif()
#        add_custom_command(TARGET redisearch POST_BUILD
#            COMMAND objcopy --only-keep-debug $<TARGET_FILE:redisearch> $<TARGET_FILE:redisearch>.debug
#            COMMAND objcopy --add-gnu-debuglink $<TARGET_FILE:redisearch>.debug $<TARGET_FILE:redisearch>
#            COMMAND ${CMAKE_STRIP} -g $<TARGET_FILE:redisearch>)
    endif()
	
	add_dependencies(redisearch VectorSimilarity)
endif()

#----------------------------------------------------------------------------------------------

if (RS_BUILD_COORDINATOR)
    set(RS_RUN_TESTS OFF)
endif()

if (RS_RUN_TESTS)
    enable_testing()
endif()

if (RS_RUN_TESTS AND NOT RS_BUILD_COORDINATOR AND NOT RS_BUILD_STATIC)
    set(BUILD_GTEST ON CACHE BOOL "enable gtest" FORCE)
    set(BUILD_GMOCK OFF CACHE BOOL "disable gmock" FORCE)

    add_subdirectory(deps/googletest)
    add_subdirectory(tests/cpptests)
    add_subdirectory(tests/ctests)
    add_subdirectory(tests/pytests)
    add_subdirectory(tests/c_utils)
    add_subdirectory(tests/ctests/ext-example example_extension)
    if (RS_ENABLE_MOCK)
        add_subdirectory(tests/cpptests/redismock)
    endif()
endif()
