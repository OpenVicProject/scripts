# Third-party dependency fetching shared by all OpenVic repos.
#
# Deps are fetched as pinned GitHub source tarballs into the build tree's
# `_deps/` dir (via FetchContent). The SHA/SHA256 pins in each repo's
# openvic_declare_dep() calls are the single source of truth for third-party
# versions; there are no third-party git submodules. Fetched sources live
# outside the working tree, so branch switches and CI checkouts never touch
# their mtimes and returning to an already-built pin is a no-op.
#
# First-party code (openvic-simulation, openvic-dataloader, lexy-vdf) is NOT
# fetched -- it is the code under development and must rebuild on branch
# switches, so it builds from the submodule tree via add_subdirectory().

include_guard(GLOBAL)

include(FetchContent)

# CMP0168 (CMake >= 3.30): FetchContent populates directly during configure
# with no per-dep sub-build -- a meaningful configure-time win across the ~15
# fetched deps. Guarded so it is a no-op on 3.28/3.29. Set at include (directory)
# scope so it propagates to every repo's MakeAvailable call sites.
if(POLICY CMP0168)
    cmake_policy(SET CMP0168 NEW)
endif()

#[[ openvic_declare_dep(<name>
        REPO <org/repo>          GitHub owner/repo the tarball comes from
        SHA <full-commit-sha>    commit the tarball is pinned to
        SHA256 <hash>            tarball URL_HASH (integrity + download-skip)
        [DOWNLOAD_ONLY]          populate the source but do NOT add_subdirectory
                                 it (for deps whose CMakeLists we don't use)
        [SOURCE_SUBDIR <dir>]    add_subdirectory this subdir of the tarball
        [SOURCE_DIR <dir>]       override the extraction directory
    )

Declares a dep with FetchContent. The caller follows with
FetchContent_MakeAvailable(<name>) (after any option-setting the dep needs),
then uses ${<name>_SOURCE_DIR} for DOWNLOAD_ONLY deps.

Declaring the same FetchContent name twice keeps the first declaration
(standard FetchContent behavior). This is expected for the two vendored lexy
copies: openvic-dataloader's pin wins in composed builds, lexy-vdf's own pin
applies only when it builds standalone.

Fetched as a source tarball rather than a git clone: a full-SHA GIT_TAG cannot
use a shallow clone, so git-based fetches of the larger repos (godot-cpp,
range-v3, spdlog) would pull full history. None of these deps need nested git
submodules at their pinned commit, so tarballs are strictly cheaper.

Local-dev escape hatch: -DFETCHCONTENT_SOURCE_DIR_<UPPER_NAME>=<path> points a
single dep back at a working-tree checkout (this reintroduces mtime coupling
for that one dep -- it is a debugging tool, not the default).
]]
function(openvic_declare_dep name)
    cmake_parse_arguments(
        PARSE_ARGV 1 ARG
        "DOWNLOAD_ONLY"
        "REPO;SHA;SHA256;SOURCE_SUBDIR;SOURCE_DIR"
        ""
    )

    if(NOT ARG_REPO OR NOT ARG_SHA OR NOT ARG_SHA256)
        message(FATAL_ERROR "openvic_declare_dep(${name}) requires REPO, SHA and SHA256")
    endif()

    set(declare_args "")
    if(ARG_DOWNLOAD_ONLY)
        # SOURCE_SUBDIR pointing at a nonexistent dir makes MakeAvailable
        # populate the source but skip add_subdirectory (documented behavior,
        # CMake >= 3.28). Used for deps whose upstream CMakeLists we replace
        # with a hand-rolled target (or whose CMakeLists pollutes global state).
        list(APPEND declare_args SOURCE_SUBDIR "_openvic_do_not_add")
    elseif(ARG_SOURCE_SUBDIR)
        list(APPEND declare_args SOURCE_SUBDIR "${ARG_SOURCE_SUBDIR}")
    endif()
    if(ARG_SOURCE_DIR)
        list(APPEND declare_args SOURCE_DIR "${ARG_SOURCE_DIR}")
    endif()

    FetchContent_Declare(
        ${name}
        URL "https://github.com/${ARG_REPO}/archive/${ARG_SHA}.tar.gz"
        URL_HASH SHA256=${ARG_SHA256}
        SYSTEM
        EXCLUDE_FROM_ALL
        ${declare_args}
    )
endfunction()
