# Based on https://github.com/godotengine/godot-cpp/blob/ba0edfed90512ec64aba51d4295a3e7e30112f86/tools/common_compiler_flags.py
import os
import subprocess


def using_emcc(env):
    return "emcc" in os.path.basename(env["CC"])


def using_clang(env):
    return "clang" in os.path.basename(env["CC"])


def is_vanilla_clang(env):
    if not using_clang(env):
        return False
    try:
        version = subprocess.check_output([env.subst(env["CXX"]), "--version"]).strip().decode("utf-8")
    except (subprocess.CalledProcessError, OSError):
        print("Couldn't parse CXX environment variable to infer compiler version.")
        return False
    return not version.startswith("Apple")


def exists(env):
    return True


def generate(env):
    assert env["lto"] in ["thin", "full", "none"], "Unrecognized lto: {}".format(env["lto"])
    if env["lto"] != "none":
        print("Using LTO: " + env["lto"])

    # Require C++20
    if env.get("is_msvc", False):
        env.Prepend(CXXFLAGS=["/std:c++20"])
    else:
        env.Prepend(CXXFLAGS=["-std=c++20"])

    # Disable exception handling. We doesn't use exceptions anywhere, and this
    # saves around 20% of binary size and very significant build time.
    if env["disable_exceptions"]:
        if env.get("is_msvc", False):
            env.Append(CPPDEFINES=[("_HAS_EXCEPTIONS", 0)])
        else:
            env.Append(CXXFLAGS=["-fno-exceptions"])
    elif env.get("is_msvc", False):
        env.Append(CXXFLAGS=["/EHsc"])

    if not env.get("is_msvc", False):
        if env["symbols_visibility"] == "visible":
            env.AppendUnique(CCFLAGS=["-fvisibility=default"])
            env.AppendUnique(LINKFLAGS=["-fvisibility=default"])
        elif env["symbols_visibility"] == "hidden":
            env.AppendUnique(CCFLAGS=["-fvisibility=hidden"])
            env.AppendUnique(LINKFLAGS=["-fvisibility=hidden"])

    if env["optimize"] == "speed":
        env.AppendUnique(CPPDEFINES=["OPT_SPEED_ENABLED"])
    elif env["optimize"] == "speed_trace":
        env.AppendUnique(CPPDEFINES=["OPT_SPEED_TRACE_ENABLED"])
    elif env["optimize"] == "size":
        env.AppendUnique(CPPDEFINES=["OPT_SIZE_ENABLED"])
    elif env["optimize"] == "debug":
        env.AppendUnique(CPPDEFINES=["OPT_DEBUG_ENABLED"])

    if env["harden_memory"] == "fast":
        env.AppendUnique(CPPDEFINES=["_GLIBCXX_ASSERTIONS", ("_LIBCPP_HARDENING_MODE", "_LIBCPP_HARDENING_MODE_FAST"), ("_MSVC_STL_HARDENING", 1)])

    # Set optimize and debug_symbols flags.
    # "custom" means do nothing and let users set their own optimization flags.
    if env.get("is_msvc", False):
        if env["debug_symbols"]:
            env.AppendUnique(CCFLAGS=["/Zi", "/FS"])
            env.AppendUnique(LINKFLAGS=["/DEBUG:FULL"])

        if env["disable_rtti"]:
            env.AppendUnique(CCFLAGS=["/GR-"])

        if env["optimize"] == "speed":
            env.AppendUnique(CCFLAGS=["/O2"])
            env.AppendUnique(LINKFLAGS=["/OPT:REF"])
        elif env["optimize"] == "speed_trace":
            env.AppendUnique(CCFLAGS=["/O2"])
            env.AppendUnique(LINKFLAGS=["/OPT:REF", "/OPT:NOICF"])
        elif env["optimize"] == "size":
            env.AppendUnique(CCFLAGS=["/O1"])
            env.AppendUnique(LINKFLAGS=["/OPT:REF"])
        elif env["optimize"] == "debug" or env["optimize"] == "none":
            env.AppendUnique(CCFLAGS=["/Od"])

        if env["lto"] == "thin":
            if not env["use_llvm"]:
                print("ThinLTO is only compatible with LLVM, use `use_llvm=yes` or `lto=full`.")
                env.Exit(255)

            env.AppendUnique(CCFLAGS=["-flto=thin"])
            env.AppendUnique(LINKFLAGS=["-flto=thin"])
        elif env["lto"] == "full":
            if env["use_llvm"]:
                env.AppendUnique(CCFLAGS=["-flto"])
                env.AppendUnique(LINKFLAGS=["-flto"])
            else:
                env.AppendUnique(CCFLAGS=["/GL"])
                env.AppendUnique(ARFLAGS=["/LTCG"])
                env.AppendUnique(LINKFLAGS=["/LTCG"])
    else:
        if env["debug_symbols"]:
            # Adding dwarf-4 explicitly makes stacktraces work with clang builds,
            # otherwise addr2line doesn't understand them.
            env.AppendUnique(CCFLAGS=["-gdwarf-4"])
            if using_emcc(env):
                # Emscripten only produces dwarf symbols when using "-g3".
                env.AppendUnique(CCFLAGS=["-g3"])
                # Emscripten linker needs debug symbols options too.
                env.AppendUnique(LINKFLAGS=["-gdwarf-4"])
                env.AppendUnique(LINKFLAGS=["-g3"])
            elif env.dev_build:
                env.AppendUnique(CCFLAGS=["-g3"])
            else:
                env.AppendUnique(CCFLAGS=["-g2"])
        else:
            if using_clang(env) and not is_vanilla_clang(env) and not env["use_mingw"]:
                # Apple Clang, its linker doesn't like -s.
                env.AppendUnique(LINKFLAGS=["-Wl,-S", "-Wl,-x", "-Wl,-dead_strip"])
            else:
                env.AppendUnique(LINKFLAGS=["-s"])

        if env["disable_rtti"]:
            env.AppendUnique(CCFLAGS=["-fno-rtti"])

        if env["optimize"] == "speed":
            env.AppendUnique(CCFLAGS=["-O3"])
        # `-O2` is friendlier to debuggers than `-O3`, leading to better crash backtraces.
        elif env["optimize"] == "speed_trace":
            env.AppendUnique(CCFLAGS=["-O2"])
        elif env["optimize"] == "size":
            env.AppendUnique(CCFLAGS=["-Os"])
        elif env["optimize"] == "debug":
            env.AppendUnique(CCFLAGS=["-Og"])
        elif env["optimize"] == "none":
            env.AppendUnique(CCFLAGS=["-O0"])

        if env["lto"] == "thin":
            if (env["platform"] == "windows" or env["platform"] == "linux") and not env["use_llvm"]:
                print("ThinLTO is only compatible with LLVM, use `use_llvm=yes` or `lto=full`.")
                env.Exit(255)
            env.AppendUnique(CCFLAGS=["-flto=thin"])
            env.AppendUnique(LINKFLAGS=["-flto=thin"])
        elif env["lto"] == "full":
            env.AppendUnique(CCFLAGS=["-flto"])
            env.AppendUnique(LINKFLAGS=["-flto"])
