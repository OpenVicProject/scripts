# Shared CMake support for OpenVic projects (OpenVic, openvic-simulation,
# openvic-dataloader, lexy-vdf). Each repo fetches this `scripts` repo as a
# pinned FetchContent tarball in its root CMakeLists.txt bootstrap block and
# then includes this module, guarded by:
#
#     if(NOT COMMAND openvic_setup_base_flags)
#
# In a composed build (a parent already loaded its own copy) the fetch and
# include are skipped, so the first-loaded (outermost) module version wins.
# To bump the pin in a consuming repo, see the procedure in README.md.

include_guard(GLOBAL)

find_package(Python3 COMPONENTS Interpreter REQUIRED)

include("${CMAKE_CURRENT_LIST_DIR}/OpenVicFlags.cmake")
include("${CMAKE_CURRENT_LIST_DIR}/OpenVicCodegen.cmake")
include("${CMAKE_CURRENT_LIST_DIR}/OpenVicDeps.cmake")
