# Based on https://github.com/godotengine/godot-cpp/blob/98ea2f60bb3846d6ae410d8936137d1b099cd50b/tools/macos.py
import os
import sys

from build import common_compiler_flags
from SCons.Variables import BoolVariable


def has_osxcross():
    return "OSXCROSS_ROOT" in os.environ


def options(opts):
    opts.Add("macos_deployment_target", "macOS deployment target", "default")
    opts.Add("macos_sdk_path", "macOS SDK path", "")
    if has_osxcross():
        opts.Add("osxcross_sdk", "OSXCross SDK version", "darwin16")
    opts.Add(BoolVariable("use_ubsan", "Use LLVM/GCC compiler undefined behavior sanitizer (UBSAN)", False))
    opts.Add(BoolVariable("use_asan", "Use LLVM/GCC compiler address sanitizer (ASAN)", False))
    opts.Add(BoolVariable("use_tsan", "Use LLVM/GCC compiler thread sanitizer (TSAN)", False))


def exists(env):
    return sys.platform == "darwin" or has_osxcross()


def generate(env):
    if env["arch"] not in ("universal", "arm64", "x86_64"):
        print("Only universal, arm64, and x86_64 are supported on macOS. Exiting.")
        env.Exit(1)

    if sys.platform == "darwin":
        # Use clang on macOS by default
        env["CXX"] = "clang++"
        env["CC"] = "clang"
    else:
        # OSXCross
        root = os.environ.get("OSXCROSS_ROOT", "")
        if env["arch"] == "arm64":
            basecmd = root + "/target/bin/arm64-apple-" + env["osxcross_sdk"] + "-"
        else:
            basecmd = root + "/target/bin/x86_64-apple-" + env["osxcross_sdk"] + "-"

        env["CC"] = basecmd + "clang"
        env["CXX"] = basecmd + "clang++"
        env["AR"] = basecmd + "ar"
        env["RANLIB"] = basecmd + "ranlib"
        env["AS"] = basecmd + "as"

        binpath = os.path.join(root, "target", "bin")
        if binpath not in env["ENV"]["PATH"]:
            # Add OSXCROSS bin folder to PATH (required for linking).
            env.PrependENVPath("PATH", binpath)

    # Common flags
    if env["arch"] == "universal":
        env.Append(LINKFLAGS=["-arch", "x86_64", "-arch", "arm64"])
        env.Append(CCFLAGS=["-arch", "x86_64", "-arch", "arm64"])
    else:
        env.Append(LINKFLAGS=["-arch", env["arch"]])
        env.Append(CCFLAGS=["-arch", env["arch"]])

    if env["macos_deployment_target"] != "default":
        env.Append(CCFLAGS=["-mmacosx-version-min=" + env["macos_deployment_target"]])
        env.Append(LINKFLAGS=["-mmacosx-version-min=" + env["macos_deployment_target"]])

    if env["macos_sdk_path"]:
        env.Append(CCFLAGS=["-isysroot", env["macos_sdk_path"]])
        env.Append(LINKFLAGS=["-isysroot", env["macos_sdk_path"]])

    env.Append(
        LINKFLAGS=[
            "-framework",
            "Foundation",
            "-Wl,-undefined,dynamic_lookup",
        ]
    )

    if env["use_ubsan"] or env["use_asan"] or env["use_tsan"]:
        env.extra_suffix += ".san"
        env.Append(CCFLAGS=["-DSANITIZERS_ENABLED"])

        if env["use_ubsan"]:
            env.Append(
                CCFLAGS=[
                    "-fsanitize=undefined,shift,shift-exponent,integer-divide-by-zero,unreachable,vla-bound,null,return,signed-integer-overflow,bounds,float-divide-by-zero,float-cast-overflow,nonnull-attribute,returns-nonnull-attribute,bool,enum,vptr,pointer-overflow,builtin"
                ]
            )
            env.Append(LINKFLAGS=["-fsanitize=undefined"])
            env.Append(CCFLAGS=["-fsanitize=nullability-return,nullability-arg,function,nullability-assign"])

        if env["use_asan"]:
            env.Append(CCFLAGS=["-fsanitize=address,pointer-subtract,pointer-compare"])
            env.Append(LINKFLAGS=["-fsanitize=address"])

        if env["use_tsan"]:
            env.Append(CCFLAGS=["-fsanitize=thread"])
            env.Append(LINKFLAGS=["-fsanitize=thread"])

    env.Append(CPPDEFINES=["MACOS_ENABLED", "UNIX_ENABLED"])

    if env["lto"] == "auto":
        env["lto"] = "none"

    common_compiler_flags.generate(env)
