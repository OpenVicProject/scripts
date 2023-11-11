#!/usr/bin/env python

# This file is heavily based on https://github.com/godotengine/godot-cpp/blob/df5b1a9a692b0d972f5ac3c853371594cdec420b/SConstruct and https://github.com/godotengine/godot-cpp/blob/df5b1a9a692b0d972f5ac3c853371594cdec420b/tools/godotcpp.py
import os
import platform
import sys

import SCons

# Local
from build.option_handler import OptionsClass
from build.glob_recursive import GlobRecursive
from build.cache import show_progress

def normalize_path(val, env):
    return val if os.path.isabs(val) else os.path.join(env.Dir("#").abspath, val)

def validate_parent_dir(key, val, env):
    if not os.path.isdir(normalize_path(os.path.dirname(val), env)):
        raise UserError("'%s' is not a directory: %s" % (key, os.path.dirname(val)))

# Try to detect the host platform automatically.
# This is used if no `platform` argument is passed
if sys.platform.startswith("linux"):
    default_platform = "linux"
elif sys.platform == "darwin":
    default_platform = "macos"
elif sys.platform == "win32" or sys.platform == "msys":
    default_platform = "windows"
elif ARGUMENTS.get("platform", ""):
    default_platform = ARGUMENTS.get("platform")
else:
    raise ValueError("Could not detect platform automatically, please specify with platform=<platform>")

is_standalone = SCons.Script.sconscript_reading == 2

try:
    Import("env")
    old_env = env
    env = old_env.Clone()
except:
    # Default tools with no platform defaults to gnu toolchain.
    # We apply platform specific toolchains via our custom tools.
    env = Environment(tools=["default"], PLATFORM="")
    old_env = env

env.TOOLPATH = [env.Dir("../").rel_path(env.Dir("tools"))]
env.is_standalone = is_standalone
env.show_progress = show_progress

env.PrependENVPath("PATH", os.getenv("PATH"))

architecture_array = ["", "universal", "x86_32", "x86_64", "arm32", "arm64", "rv64", "ppc32", "ppc64", "wasm32"]
architecture_aliases = {
    "x64": "x86_64",
    "amd64": "x86_64",
    "armv7": "arm32",
    "armv8": "arm64",
    "arm64v8": "arm64",
    "aarch64": "arm64",
    "rv": "rv64",
    "riscv": "rv64",
    "riscv64": "rv64",
    "ppcle": "ppc32",
    "ppc": "ppc32",
    "ppc64le": "ppc64",
}

platforms = ("linux", "macos", "windows", "android", "ios", "javascript")
unsupported_known_platforms = ("android", "ios", "javascript")

def SetupOptions():
    # Default num_jobs to local cpu count if not user specified.
    # SCons has a peculiarity where user-specified options won't be overridden
    # by SetOption, so we can rely on this to know if we should use our default.
    initial_num_jobs = env.GetOption("num_jobs")
    altered_num_jobs = initial_num_jobs + 1
    env.SetOption("num_jobs", altered_num_jobs)
    if env.GetOption("num_jobs") == altered_num_jobs:
        cpu_count = os.cpu_count()
        if cpu_count is None:
            print("Couldn't auto-detect CPU count to configure build parallelism. Specify it with the -j argument.")
        else:
            safer_cpu_count = cpu_count if cpu_count <= 4 else cpu_count - 1
            print(
                "Auto-detected %d CPU cores available for build parallelism. Using %d cores by default. You can override it with the -j argument."
                % (cpu_count, safer_cpu_count)
            )
            env.SetOption("num_jobs", safer_cpu_count)

    opts = OptionsClass(ARGUMENTS.copy())

    opts.Add(
        EnumVariable(
            key="platform",
            help="Target platform",
            default=env.get("platform", default_platform),
            allowed_values=platforms,
            ignorecase=2,
        )
    )

    opts.Add(
        EnumVariable(
            key="target",
            help="Compilation target",
            default=env.get("target", "template_debug"),
            allowed_values=("editor", "template_release", "template_debug"),
        )
    )

    opts.Add(
        EnumVariable(
            key="precision",
            help="Set the floating-point precision level",
            default=env.get("precision", "single"),
            allowed_values=("single", "double"),
        )
    )

    opts.Add(
        BoolVariable(
            "disable_exceptions",
            "Force disabling exception handling code",
            default=env.get("disable_exceptions", True),
        )
    )

    # Add platform options
    tools = {}
    for pl in set(platforms) - set(unsupported_known_platforms):
        tool = Tool(pl, toolpath=env.TOOLPATH)
        if hasattr(tool, "options"):
            tool.options(opts)
        tools[pl] = tool

    # CPU architecture options.
    opts.Add(
        EnumVariable(
            key="arch",
            help="CPU architecture",
            default=env.get("arch", ""),
            allowed_values=architecture_array,
            map=architecture_aliases,
        )
    )

     # compiledb
    opts.Add(
        BoolVariable(
            key="compiledb",
            help="Generate compilation DB (`compile_commands.json`) for external tools",
            default=env.get("compiledb", False),
        )
    )
    opts.Add(
        PathVariable(
            key="compiledb_file",
            help="Path to a custom `compile_commands.json` file",
            default=env.get("compiledb_file", "compile_commands.json"),
            validator=validate_parent_dir,
        )
    )
    opts.Add(BoolVariable("verbose", "Enable verbose output for the compilation", False))
    opts.Add(BoolVariable("intermediate_delete", "Enables automatically deleting unassociated intermediate binary files.", True))
    opts.Add(BoolVariable("progress", "Show a progress indicator during compilation", True))

    # Targets flags tool (optimizations, debug symbols)
    target_tool = Tool("targets", toolpath=env.TOOLPATH)
    target_tool.options(opts)
    env._opts = opts
    env._target_tool = target_tool
    return opts

def FinalizeOptions():
    opts = env._opts
    target_tool = env._target_tool
    # Custom options and profile flags.
    opts.Make(["../custom.py"])
    opts.Finalize(env)
    Help(opts.GenerateHelpText(env))

    if env["platform"] in unsupported_known_platforms:
        print("Unsupported platform: " + env["platform"]+". Only supports " + ", ".join(set(platforms) - set(unsupported_known_platforms)))
        Exit()

    # Process CPU architecture argument.
    if env["arch"] == "":
        # No architecture specified. Default to arm64 if building for Android,
        # universal if building for macOS or iOS, wasm32 if building for web,
        # otherwise default to the host architecture.
        if env["platform"] in ["macos", "ios"]:
            env["arch"] = "universal"
        elif env["platform"] == "android":
            env["arch"] = "arm64"
        elif env["platform"] == "javascript":
            env["arch"] = "wasm32"
        else:
            host_machine = platform.machine().lower()
            if host_machine in architecture_array:
                env["arch"] = host_machine
            elif host_machine in architecture_aliases.keys():
                env["arch"] = architecture_aliases[host_machine]
            elif "86" in host_machine:
                # Catches x86, i386, i486, i586, i686, etc.
                env["arch"] = "x86_32"
            else:
                print("Unsupported CPU architecture: " + host_machine)
                Exit()

    print("Building for architecture " + env["arch"] + " on platform " + env["platform"])

    tool = Tool(env["platform"], toolpath=env.TOOLPATH)

    if tool is None or not tool.exists(env):
        raise ValueError("Required toolchain not found for platform " + env["platform"])

    tool.generate(env)
    target_tool.generate(env)

    # Disable exception handling. Godot doesn't use exceptions anywhere, and this
    # saves around 20% of binary size and very significant build time.
    if env["disable_exceptions"]:
        if env.get("is_msvc", False):
            env.Append(CPPDEFINES=[("_HAS_EXCEPTIONS", 0)])
        else:
            env.Append(CXXFLAGS=["-fno-exceptions"])
    elif env.get("is_msvc", False):
        env.Append(CXXFLAGS=["/EHsc"])

    # Require C++20
    if env.get("is_msvc", False):
        env.Append(CXXFLAGS=["/std:c++20"])
    else:
        env.Append(CXXFLAGS=["-std=c++20"])

    if env["precision"] == "double":
        env.Append(CPPDEFINES=["REAL_T_IS_DOUBLE"])

    scons_cache_path = os.environ.get("SCONS_CACHE")
    if scons_cache_path != None:
        CacheDir(scons_cache_path)
        Decider("MD5")
        print("Scons cache enabled... (path: '" + scons_cache_path + "')")

    if env["compiledb"] and is_standalone:
        # compile_commands.json
        env.Tool("compilation_db")
        env.Alias("compiledb", env.CompilationDatabase(normalize_path(env["compiledb_file"], env)))

env.SetupOptions = SetupOptions
env.FinalizeOptions = FinalizeOptions
env.GlobRecursive = GlobRecursive

Return("env")