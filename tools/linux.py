# Based on https://github.com/godotengine/godot-cpp/blob/98ea2f60bb3846d6ae410d8936137d1b099cd50b/tools/linux.py
import common_compiler_flags
from SCons.Variables import BoolVariable
from SCons.Tool import clang, clangxx


def options(opts):
    opts.Add(BoolVariable("use_llvm", "Use the LLVM compiler - only effective when targeting Linux", False))
    opts.Add(BoolVariable("use_ubsan", "Use LLVM/GCC compiler undefined behavior sanitizer (UBSAN)", False))
    opts.Add(BoolVariable("use_asan", "Use LLVM/GCC compiler address sanitizer (ASAN)", False))
    opts.Add(BoolVariable("use_lsan", "Use LLVM/GCC compiler leak sanitizer (LSAN)", False))
    opts.Add(BoolVariable("use_tsan", "Use LLVM/GCC compiler thread sanitizer (TSAN)", False))
    opts.Add(BoolVariable("use_msan", "Use LLVM compiler memory sanitizer (MSAN)", False))


def exists(env):
    return True


def generate(env):
    if env["use_llvm"]:
        clang.generate(env)
        clangxx.generate(env)
    elif env.use_hot_reload:
        # Required for hot reload support.
        env.Append(CXXFLAGS=["-fno-gnu-unique"])

    env.Append(CCFLAGS=["-fPIC", "-Wwrite-strings"])
    env.Append(LINKFLAGS=["-Wl,-R,'$$ORIGIN'"])

    if env["arch"] == "x86_64":
        # -m64 and -m32 are x86-specific already, but it doesn't hurt to
        # be clear and also specify -march=x86-64. Similar with 32-bit.
        env.Append(CCFLAGS=["-m64", "-march=x86-64"])
        env.Append(LINKFLAGS=["-m64", "-march=x86-64"])
    elif env["arch"] == "x86_32":
        env.Append(CCFLAGS=["-m32", "-march=i686"])
        env.Append(LINKFLAGS=["-m32", "-march=i686"])
    elif env["arch"] == "arm64":
        env.Append(CCFLAGS=["-march=armv8-a"])
        env.Append(LINKFLAGS=["-march=armv8-a"])
    elif env["arch"] == "rv64":
        env.Append(CCFLAGS=["-march=rv64gc"])
        env.Append(LINKFLAGS=["-march=rv64gc"])

    if env["use_ubsan"] or env["use_asan"] or env["use_lsan"] or env["use_tsan"] or env["use_msan"]:
        env.extra_suffix += ".san"
        env.Append(CCFLAGS=["-DSANITIZERS_ENABLED"])

        if env["use_ubsan"]:
            env.Append(
                CCFLAGS=[
                    "-fsanitize=undefined,shift,shift-exponent,integer-divide-by-zero,unreachable,vla-bound,null,return,signed-integer-overflow,bounds,float-divide-by-zero,float-cast-overflow,nonnull-attribute,returns-nonnull-attribute,bool,enum,vptr,pointer-overflow,builtin"
                ]
            )
            env.Append(LINKFLAGS=["-fsanitize=undefined"])
            if env["use_llvm"]:
                env.Append(
                    CCFLAGS=[
                        "-fsanitize=nullability-return,nullability-arg,function,nullability-assign,implicit-integer-sign-change"
                    ]
                )
            else:
                env.Append(CCFLAGS=["-fsanitize=bounds-strict"])

        if env["use_asan"]:
            env.Append(CCFLAGS=["-fsanitize=address,pointer-subtract,pointer-compare"])
            env.Append(LINKFLAGS=["-fsanitize=address"])

        if env["use_lsan"]:
            env.Append(CCFLAGS=["-fsanitize=leak"])
            env.Append(LINKFLAGS=["-fsanitize=leak"])

        if env["use_tsan"]:
            env.Append(CCFLAGS=["-fsanitize=thread"])
            env.Append(LINKFLAGS=["-fsanitize=thread"])

        if env["use_msan"] and env["use_llvm"]:
            env.Append(CCFLAGS=["-fsanitize=memory"])
            env.Append(CCFLAGS=["-fsanitize-memory-track-origins"])
            env.Append(CCFLAGS=["-fsanitize-recover=memory"])
            env.Append(LINKFLAGS=["-fsanitize=memory"])

    env.Append(CPPDEFINES=["LINUX_ENABLED", "UNIX_ENABLED"])

    if env["lto"] == "auto":
        env["lto"] = "full"

    common_compiler_flags.generate(env)
