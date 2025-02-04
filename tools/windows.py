# Copied from https://github.com/godotengine/godot-cpp/blob/df5b1a9a692b0d972f5ac3c853371594cdec420b/tools/windows.py
import sys

import my_spawn

from SCons.Tool import msvc, mingw
from SCons.Variables import BoolVariable


def options(opts):
    opts.Add(BoolVariable("use_mingw", "Use the MinGW compiler instead of MSVC - only effective on Windows", False))
    opts.Add(BoolVariable("use_clang_cl", "Use the clang driver instead of MSVC - only effective on Windows", False))
    opts.Add(BoolVariable("use_static_cpp", "Link MinGW/MSVC C++ runtime libraries statically", False))
    opts.Add(BoolVariable("debug_crt", "Compile with MSVC's debug CRT (/MDd)", False))
    opts.Add(BoolVariable("use_asan", "Use address sanitizer (ASAN)", False))


def exists(env):
    return True


def generate(env):
    base = None

    msvc_found = msvc.exists(env)
    mingw_found = mingw.exists(env)

    if not msvc_found and not mingw_found:
        print("Could not find installation of msvc or mingw, please properly install (or reinstall) MSVC with C++ or Mingw first.")
        env.Exit(1)

    if not env["use_mingw"] and msvc_found:
        if env["arch"] == "x86_64":
            env["TARGET_ARCH"] = "amd64"
        elif env["arch"] == "x86_32":
            env["TARGET_ARCH"] = "x86"
        env["is_msvc"] = True

        # MSVC, linker, and archiver.
        msvc.generate(env)
        env.Tool("mslib")
        env.Tool("mslink")

        env.Append(CPPDEFINES=["TYPED_METHOD_BIND", "NOMINMAX"])
        env.Append(CCFLAGS=["/utf-8", "/Zc:preprocessor"])
        env.Append(LINKFLAGS=["/WX"])

        if env["use_clang_cl"]:
            env["CC"] = "clang-cl"
            env["CXX"] = "clang-cl"

        if env["debug_crt"]:
            # Always use dynamic runtime, static debug CRT breaks thread_local.
            env.AppendUnique(CCFLAGS=["/MDd"])
        else:
            if env["use_static_cpp"]:
                env.Append(CCFLAGS=["/MT"])
            else:
                env.Append(CCFLAGS=["/MD"])

    elif (sys.platform == "win32" or sys.platform == "msys") and mingw_found:
        env["use_mingw"] = True
        mingw.generate(env)
        # Don't want lib prefixes
        env["IMPLIBPREFIX"] = ""
        env["SHLIBPREFIX"] = ""
        # Want dll suffix
        env["SHLIBSUFFIX"] = ".dll"

        env.Append(CCFLAGS=["-Wwrite-strings"])
        env.Append(LINKFLAGS=["-Wl,--no-undefined"])
        if env["use_static_cpp"]:
            env.Append(
                LINKFLAGS=[
                    "-static",
                    "-static-libgcc",
                    "-static-libstdc++",
                ]
            )

        # Long line hack. Use custom spawn, quick AR append (to avoid files with the same names to override each other).
        my_spawn.configure(env)

    elif mingw_found:
        env["use_mingw"] = True
        # Cross-compilation using MinGW
        prefix = "i686" if env["arch"] == "x86_32" else env["arch"]
        env["CXX"] = prefix + "-w64-mingw32-g++"
        env["CC"] = prefix + "-w64-mingw32-gcc"
        env["AR"] = prefix + "-w64-mingw32-ar"
        env["RANLIB"] = prefix + "-w64-mingw32-ranlib"
        env["LINK"] = prefix + "-w64-mingw32-g++"
        # Want dll suffix
        env["SHLIBSUFFIX"] = ".dll"

        env.Append(CCFLAGS=["-Wwrite-strings"])
        env.Append(LINKFLAGS=["-Wl,--no-undefined"])
        if env["use_static_cpp"]:
            env.Append(
                LINKFLAGS=[
                    "-static",
                    "-static-libgcc",
                    "-static-libstdc++",
                ]
            )

    else:
        print("'use_mingw' set but Mingw is not installed, please install Mingw first.")
        env.Exit(1)

    if env["use_asan"]:
        env.extra_suffix += ".san"
        env.Append(LINKFLAGS=["/INFERASANLIBS"])
        env.Append(CCFLAGS=["/fsanitize=address"])

    env.Append(CPPDEFINES=["WINDOWS_ENABLED"])
