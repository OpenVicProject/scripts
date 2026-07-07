# OpenVicProject/scripts

Shared CMake helpers for the [OpenVicProject repos](https://github.com/OpenVicProject)
(OpenVic, openvic-simulation, openvic-dataloader, lexy-vdf).


Each consuming repo fetches this repo as a **pinned FetchContent tarball**

```cmake
if(NOT COMMAND openvic_setup_base_flags)
    include(FetchContent)
    FetchContent_Declare(
        openvic_scripts
        URL "https://github.com/OpenVicProject/scripts/archive/<SHA>.tar.gz"
        URL_HASH SHA256=<SHA256>
    )
    FetchContent_MakeAvailable(openvic_scripts)
    include("${openvic_scripts_SOURCE_DIR}/cmake/OpenVicScripts.cmake")
endif()
```

## Bumping the pin in a consuming repo

After a change lands on `master` here:

1. Note the new commit SHA.
2. Compute the tarball hash:
   ```sh
   curl -sL https://github.com/OpenVicProject/scripts/archive/<SHA>.tar.gz | sha256sum
   ```
3. In the consumer's root `CMakeLists.txt` bootstrap block, update the `URL`
   SHA and the `URL_HASH SHA256=` value.

To test uncommitted changes to this repo from a consumer, configure the
consumer with:

```sh
cmake --preset <preset> -DFETCHCONTENT_SOURCE_DIR_OPENVIC_SCRIPTS=<path-to-this-checkout>
```
