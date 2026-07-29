# Compiler/define setup shared by all OpenVic repos.
#
# The Godot build axis reuses godot-cpp's cache variable names so one setting
# drives both godot-cpp and the OpenVic libraries; the declarations below also
# make them available in standalone builds that don't include godot-cpp.

include_guard(GLOBAL)

set(GODOTCPP_TARGET
    "template_debug"
    CACHE STRING
    "Which Godot target to build for: editor, template_debug, template_release"
)
set_property(CACHE GODOTCPP_TARGET PROPERTY STRINGS "template_debug;template_release;editor")
option(GODOTCPP_DEV_BUILD "Developer build with dev-only debugging code (DEV_ENABLED)" OFF)

if(NOT GODOTCPP_TARGET MATCHES "^(editor|template_debug|template_release)$")
    message(FATAL_ERROR "GODOTCPP_TARGET must be editor, template_debug or template_release, got '${GODOTCPP_TARGET}'")
endif()

#[[ Directory-scope flags every OpenVic repo builds with. Guarded by an
inherited (non-cache) variable so nested repos in a composed build inherit the
flags from their parent directory without re-adding them. Callers must invoke
this BEFORE add_subdirectory() of any code that should build with these flags
(and the OpenVic root invokes it AFTER add_subdirectory(godot-cpp), which owns
its own flag setup). ]]
macro(openvic_setup_base_flags)
    if(NOT OPENVIC_BASE_FLAGS_APPLIED)
        set(OPENVIC_BASE_FLAGS_APPLIED TRUE)

        # Third-party deps declare old cmake_minimum_required versions; give
        # them modern policy behavior (option() and set(CACHE) honor normal
        # variables, MSVC runtime via CMAKE_MSVC_RUNTIME_LIBRARY, and accept
        # minimums older than CMake 4 supports).
        set(CMAKE_POLICY_DEFAULT_CMP0077 NEW)
        set(CMAKE_POLICY_DEFAULT_CMP0091 NEW)
        set(CMAKE_POLICY_DEFAULT_CMP0126 NEW)
        if(NOT DEFINED CMAKE_POLICY_VERSION_MINIMUM)
            set(CMAKE_POLICY_VERSION_MINIMUM 3.5)
        endif()

        set(CMAKE_CXX_STANDARD 20)
        set(CMAKE_CXX_STANDARD_REQUIRED ON)
        set(CMAKE_CXX_EXTENSIONS OFF)
        set(CMAKE_POSITION_INDEPENDENT_CODE ON)

        # No C++20 modules are used anywhere in the OpenVic sources, so skip the
        # per-translation-unit module-import scan CMake adds for C++20 targets
        # (CMP0155, on since 3.28). Each scan is a separate preprocessor pass
        # per file -- pure overhead here, felt most on incremental builds.
        set(CMAKE_CXX_SCAN_FOR_MODULES OFF)

        if(MSVC)
            add_compile_options(/utf-8)
            if(CMAKE_CXX_COMPILER_ID STREQUAL "MSVC")
                # /Zc:preprocessor is required: the code uses __VA_OPT__.
                # clang-cl is already conformant and warns the flag is unused
                # (fatal in deps that compile with warnings-as-errors).
                add_compile_options(/Zc:preprocessor)
            endif()
            # Godot doesn't use exceptions anywhere; build without them.
            # /EHsc (a CMake default) must go too: it defines __cpp_exceptions,
            # which would flip exception-detection macros (e.g. vmcontainer's)
            # onto code paths that assume exceptions can propagate.
            string(REPLACE "/EHsc" "" CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS}")
            add_compile_definitions(NOMINMAX _HAS_EXCEPTIONS=0)
        else()
            add_compile_options(-fno-exceptions -fvisibility=hidden)
            if(WIN32)
                add_compile_definitions(NOMINMAX)
                if(CMAKE_CXX_SIMULATE_ID STREQUAL "MSVC")
                    # clang++ (GNU driver) with the MSVC STL: -fno-exceptions
                    # doesn't clear _HAS_EXCEPTIONS (defaults to 1), which
                    # keeps exception-detection macros on throw paths.
                    add_compile_definitions(_HAS_EXCEPTIONS=0)
                endif()
            endif()
        endif()

        if(NOT GODOTCPP_TARGET STREQUAL "template_release")
            add_compile_definitions(DEBUG_ENABLED)
        endif()
        if(GODOTCPP_DEV_BUILD)
            add_compile_definitions(DEV_ENABLED)
        endif()
    endif()
endmacro()

#[[ Directory-scope RTTI disable. The simulation stack (openvic-simulation,
openvic-dataloader, lexy-vdf) builds without RTTI; the extension itself keeps
RTTI on, so the OpenVic root must NOT call this. ]]
macro(openvic_disable_rtti)
    if(NOT OPENVIC_RTTI_DISABLED)
        set(OPENVIC_RTTI_DISABLED TRUE)
        if(CMAKE_CXX_SIMULATE_ID STREQUAL "MSVC")
            # clang (clang-cl or clang++) + MSVC STL: disabling RTTI clears
            # _HAS_STATIC_RTTI, which removes std::any (used by the
            # simulation). cl.exe's /GR- keeps static RTTI, so leave RTTI on
            # here rather than diverge.
        elseif(MSVC)
            add_compile_options(/GR-)
        else()
            add_compile_options(-fno-rtti)
        endif()
    endif()
endmacro()
