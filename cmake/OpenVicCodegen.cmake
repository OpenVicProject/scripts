# Generated-header support shared by all OpenVic repos, driving gen/codegen.py
# (git/license/author info headers and foonathan/memory config headers).

include_guard(GLOBAL)

get_filename_component(_openvic_codegen_script "${CMAKE_CURRENT_LIST_DIR}/../gen/codegen.py" ABSOLUTE)
set(OPENVIC_CODEGEN_SCRIPT "${_openvic_codegen_script}" CACHE INTERNAL "Path to the OpenVic codegen CLI")

# commit-info is filled in at configure time with configure_file() from local
# git metadata -- no codegen.py (Python startup) and no `gh release list`
# network call on the build's critical path.
get_filename_component(_openvic_commit_info_template "${CMAKE_CURRENT_LIST_DIR}/../gen/commit_info.gen.hpp.in" ABSOLUTE)
set(OPENVIC_COMMIT_INFO_TEMPLATE "${_openvic_commit_info_template}" CACHE INTERNAL "Path to the OpenVic commit-info header template")

#[[ openvic_generate_commit_info(TARGET <tgt> PREFIX <game|sim|...> REPO_DIR <dir> OUTPUT <path>)
Fills <path> at configure time with configure_file(), substituting
<PREFIX>_TAG/_RELEASE/_COMMIT_HASH/_COMMIT_TIMESTAMP from local git metadata (no
network). RELEASE mirrors TAG unless OPENVIC_RELEASE is set; OPENVIC_TAG likewise
forces TAG. The stamp is captured at configure time only -- it refreshes on the
next reconfigure, not on every build. Release/CI builds should configure fresh
(and typically set OPENVIC_RELEASE/OPENVIC_TAG) before building. TARGET is
accepted for call-site symmetry with the other generators but is unused (the
header exists on disk before the build starts). ]]
function(openvic_generate_commit_info)
    cmake_parse_arguments(PARSE_ARGV 0 ARG "" "TARGET;PREFIX;REPO_DIR;OUTPUT" "")

    string(TOUPPER "${ARG_PREFIX}" PREFIX_UPPER)

    # --- tag ---
    if(DEFINED ENV{OPENVIC_TAG})
        set(GIT_TAG "$ENV{OPENVIC_TAG}")
    else()
        execute_process(
            COMMAND git describe --tags --abbrev=0
            WORKING_DIRECTORY "${ARG_REPO_DIR}"
            OUTPUT_VARIABLE GIT_TAG OUTPUT_STRIP_TRAILING_WHITESPACE
            ERROR_QUIET RESULT_VARIABLE _res
        )
        if(NOT _res EQUAL 0 OR GIT_TAG STREQUAL "")
            set(GIT_TAG "<tag missing>")
        endif()
    endif()

    # --- release: OPENVIC_RELEASE if set, otherwise the tag (no `gh`/network) ---
    if(DEFINED ENV{OPENVIC_RELEASE})
        set(GIT_RELEASE "$ENV{OPENVIC_RELEASE}")
    else()
        set(GIT_RELEASE "${GIT_TAG}")
    endif()

    # --- commit hash ---
    execute_process(
        COMMAND git rev-parse HEAD
        WORKING_DIRECTORY "${ARG_REPO_DIR}"
        OUTPUT_VARIABLE GIT_HASH OUTPUT_STRIP_TRAILING_WHITESPACE
        ERROR_QUIET RESULT_VARIABLE _res
    )
    if(NOT _res EQUAL 0 OR GIT_HASH STREQUAL "")
        set(GIT_HASH "0000000000000000000000000000000000000000")
    endif()

    # --- commit timestamp (UNIX seconds) ---
    execute_process(
        COMMAND git log -1 --pretty=format:%ct --no-show-signature
        WORKING_DIRECTORY "${ARG_REPO_DIR}"
        OUTPUT_VARIABLE GIT_TIMESTAMP OUTPUT_STRIP_TRAILING_WHITESPACE
        ERROR_QUIET RESULT_VARIABLE _res
    )
    if(NOT _res EQUAL 0 OR GIT_TIMESTAMP STREQUAL "")
        set(GIT_TIMESTAMP "0")
    endif()

    configure_file("${OPENVIC_COMMIT_INFO_TEMPLATE}" "${ARG_OUTPUT}" @ONLY NEWLINE_STYLE UNIX)
endfunction()

#[[ openvic_generate_license_info(TARGET <tgt> PREFIX <p> COPYRIGHT <file> LICENSE <file> OUTPUT <path>) ]]
function(openvic_generate_license_info)
    cmake_parse_arguments(PARSE_ARGV 0 ARG "" "TARGET;PREFIX;COPYRIGHT;LICENSE;OUTPUT" "")

    add_custom_command(
        OUTPUT ${ARG_OUTPUT}
        COMMAND
            ${Python3_EXECUTABLE} ${OPENVIC_CODEGEN_SCRIPT} license-info --prefix ${ARG_PREFIX} --copyright
            ${ARG_COPYRIGHT} --license ${ARG_LICENSE} -o ${ARG_OUTPUT}
        DEPENDS ${ARG_COPYRIGHT} ${ARG_LICENSE} ${OPENVIC_CODEGEN_SCRIPT}
        COMMENT "Generating ${ARG_PREFIX} license_info.gen.hpp"
        VERBATIM
    )
    target_sources(${ARG_TARGET} PRIVATE ${ARG_OUTPUT})
endfunction()

#[[ openvic_generate_author_info(TARGET <tgt> PREFIX <p> AUTHORS <file> OUTPUT <path> SECTIONS <Heading=MACRO>...) ]]
function(openvic_generate_author_info)
    cmake_parse_arguments(PARSE_ARGV 0 ARG "" "TARGET;PREFIX;AUTHORS;OUTPUT" "SECTIONS")

    set(section_args "")
    foreach(section IN LISTS ARG_SECTIONS)
        list(APPEND section_args --section "${section}")
    endforeach()

    add_custom_command(
        OUTPUT ${ARG_OUTPUT}
        COMMAND
            ${Python3_EXECUTABLE} ${OPENVIC_CODEGEN_SCRIPT} author-info --prefix ${ARG_PREFIX} --authors
            ${ARG_AUTHORS} ${section_args} -o ${ARG_OUTPUT}
        DEPENDS ${ARG_AUTHORS} ${OPENVIC_CODEGEN_SCRIPT}
        COMMENT "Generating ${ARG_PREFIX} author_info.gen.hpp"
        VERBATIM
    )
    target_sources(${ARG_TARGET} PRIVATE ${ARG_OUTPUT})
endfunction()

#[[ openvic_generate_memory_headers(MEMORY_DIR <foonathan-memory-root> DEFINES <KEY=VALUE>...)
Writes config_impl.hpp and detail/container_node_sizes_impl.hpp into the
foonathan/memory source tree at configure time, byte-identical to the files
the SCons build generates (both build systems share these source-tree files,
and codegen.py leaves them untouched when the content already matches). ]]
function(openvic_generate_memory_headers)
    cmake_parse_arguments(PARSE_ARGV 0 ARG "" "MEMORY_DIR" "DEFINES")

    set(define_args "")
    foreach(define IN LISTS ARG_DEFINES)
        list(APPEND define_args --define "${define}")
    endforeach()

    set(inner_include "${ARG_MEMORY_DIR}/include/foonathan/memory")
    execute_process(
        COMMAND
            ${Python3_EXECUTABLE} ${OPENVIC_CODEGEN_SCRIPT} memory-config ${define_args} -o
            "${inner_include}/config_impl.hpp"
        RESULT_VARIABLE result
    )
    if(NOT result EQUAL 0)
        message(FATAL_ERROR "codegen.py memory-config failed (${result})")
    endif()

    execute_process(
        COMMAND
            ${Python3_EXECUTABLE} ${OPENVIC_CODEGEN_SCRIPT} memory-node-sizes -o
            "${inner_include}/detail/container_node_sizes_impl.hpp"
        RESULT_VARIABLE result
    )
    if(NOT result EQUAL 0)
        message(FATAL_ERROR "codegen.py memory-node-sizes failed (${result})")
    endif()
endfunction()
