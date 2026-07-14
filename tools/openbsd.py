# based on tools/linux.py
from build import common_compiler_flags
from SCons.Variables import BoolVariable
from SCons.Tool import clang, clangxx


def options(opts):
    opts.Add(BoolVariable("use_static_cpp", "Link libgcc and libstdc++ statically for better portability", False))
    opts.Add(BoolVariable("use_ubsan", "Use LLVM compiler undefined behavior sanitizer (UBSAN)", False))
    opts.Add(BoolVariable("use_asan", "Use LLVM compiler address sanitizer (ASAN)", False))
    opts.Add(BoolVariable("use_lsan", "Use LLVM compiler leak sanitizer (LSAN)", False))
    opts.Add(BoolVariable("use_tsan", "Use LLVM compiler thread sanitizer (TSAN)", False))


def exists(env):
    return True


def generate(env):
    clang.generate(env)
    clangxx.generate(env)

    env.Append(CCFLAGS=["-fPIC", "-Wwrite-strings"])
    env.Append(LINKFLAGS=["-Wl,-R,'$$ORIGIN'"])

    if env["arch"] == "x86_64":
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

    if env["use_static_cpp"]:
        env.Append(LINKFLAGS=["-static-libgcc", "-static-libstdc++"])

    if env["use_ubsan"] or env["use_asan"] or env["use_lsan"] or env["use_tsan"]:
        env.extra_suffix += ".san"
        env.Append(CCFLAGS=["-DSANITIZERS_ENABLED"])

        if env["use_ubsan"]:
            env.Append(
                CCFLAGS=[
                    "-fsanitize=undefined,shift,shift-exponent,integer-divide-by-zero,unreachable,vla-bound,null,return,signed-integer-overflow,bounds,float-divide-by-zero,float-cast-overflow,nonnull-attribute,returns-nonnull-attribute,bool,enum,vptr,pointer-overflow,builtin"
                ]
            )
            env.Append(LINKFLAGS=["-fsanitize=undefined"])
            env.Append(
                CCFLAGS=[
                    "-fsanitize=nullability-return,nullability-arg,function,nullability-assign,implicit-integer-sign-change"
                ]
            )

        if env["use_asan"]:
            env.Append(CCFLAGS=["-fsanitize=address,pointer-subtract,pointer-compare"])
            env.Append(LINKFLAGS=["-fsanitize=address"])

        if env["use_lsan"]:
            env.Append(CCFLAGS=["-fsanitize=leak"])
            env.Append(LINKFLAGS=["-fsanitize=leak"])

        if env["use_tsan"]:
            env.Append(CCFLAGS=["-fsanitize=thread"])
            env.Append(LINKFLAGS=["-fsanitize=thread"])

    env.Append(CPPDEFINES=["OPENBSD_ENABLED", "UNIX_ENABLED"])

    env.Append(CPPPATH=["/usr/local/include"])
    env.Append(LIBPATH=["/usr/local/lib"])
    env.Append(LIBS=["iconv"])

    if env["lto"] == "auto":
        env["lto"] = "none"

    common_compiler_flags.generate(env)
