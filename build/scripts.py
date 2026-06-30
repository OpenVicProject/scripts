# Based on https://github.com/godotengine/godot-cpp/blob/ba0edfed90512ec64aba51d4295a3e7e30112f86/tools/godotcpp.py
import atexit
import os
import platform
import sys

from SCons import __version__ as scons_raw_version
from SCons.Builder import Builder
from SCons.Errors import UserError
from SCons.Script import ARGUMENTS
from SCons.Tool import Tool
from SCons.Variables import BoolVariable, EnumVariable, PathVariable
from SCons.Variables.BoolVariable import _text2bool

from build.author_info import author_builder
from build.cache import show_progress
from build.gch import add_gch_builder
from build.git_info import get_git_info, git_builder
from build.glob_recursive import GlobRecursive, GlobRecursiveVariant
from build.library_builders import (
    add_library_includes,
    add_library_sources,
    build_base_library,
    build_dependency_library,
    build_headless_program,
    build_unit_test,
    build_benchmark
)
from build.license_info import license_builder
from build.no_verbose import no_verbose


def get_cmdline_bool(option, default):
    """We use `ARGUMENTS.get()` to check if options were manually overridden on the command line,
    and SCons' _text2bool helper to convert them to booleans, otherwise they're handled as strings.
    """
    cmdline_val = ARGUMENTS.get(option)
    if cmdline_val is not None:
        return _text2bool(cmdline_val)
    else:
        return default


def normalize_path(val, env):
    """Normalize a path that was provided by the user on the command line
    and is thus either an absolute path, or relative to the top level directory (#)
    where the command was run.
    """
    # If val is an absolute path, it will not be joined.
    return os.path.join(env.Dir("#").abspath, val)


def validate_file(key, val, env):
    if not os.path.isfile(normalize_path(val, env)):
        raise UserError("'%s' is not a file: %s" % (key, val))


def validate_dir(key, val, env):
    if not os.path.isdir(normalize_path(val, env)):
        raise UserError("'%s' is not a directory: %s" % (key, val))


def validate_parent_dir(key, val, env):
    if not os.path.isdir(normalize_path(os.path.dirname(val), env)):
        raise UserError("'%s' is not a directory: %s" % (key, os.path.dirname(val)))


def get_platform_tools_paths(env):
    result = [env.Dir("tools").srcnode().abspath]

    project_tools_dir = env.Dir("../tools").srcnode()
    if project_tools_dir.exists():
        result.insert(0, project_tools_dir.abspath)

    custom_tools_path = env.get("custom_tools", None)
    if custom_tools_path is not None:
        result.insert(0, normalize_path(custom_tools_path, env))

    return result


def get_project_platforms(env):
    path = env.Dir("../tools").srcnode()
    if not path.exists():
        return []
    platforms = []
    for x in os.listdir(path.srcnode().abspath):
        if not x.endswith(".py"):
            continue
        platforms.append(x.removesuffix(".py"))
    return platforms


def get_custom_platforms(env):
    path = env.get("custom_tools", None)
    if path is None:
        return []
    platforms = []
    for x in os.listdir(normalize_path(path, env)):
        if not x.endswith(".py"):
            continue
        platforms.append(x.removesuffix(".py"))
    return platforms


def project_info_generator_emitter(target, source, env):
    for i in range(len(target)):
        target[i] = os.path.join(env["gen_dir"], target[i])
    return target, source


def dump(env):
    """
    Dumps latest build information for debugging purposes and external tools.
    """

    with open(".scons_env.json", "w", encoding="utf-8", newline="\n") as file:
        file.write(env.Dump(format="json"))


def prepare_purge(env):
    from SCons.Script.Main import GetBuildFailures

    def purge_flaky_files():
        paths_to_keep = []
        for build_failure in GetBuildFailures():
            path = build_failure.node.path
            if os.path.isfile(path) and path not in paths_to_keep:
                os.remove(path)

    atexit.register(purge_flaky_files)


def prepare_timer():
    import time

    def print_elapsed_time(time_at_start: float):
        time_elapsed = time.monotonic() - time_at_start
        time_formatted = time.strftime("%Hh %Mm %Ss", time.gmtime(time_elapsed))
        time_centiseconds = (time_elapsed % 1) * 100
        print(f"[BUILD TIMING] elapsed: {time_formatted} {time_centiseconds:02.0f}cs ({time_elapsed:.1f}s total)")

    atexit.register(print_elapsed_time, time.monotonic())


# CPU architecture options.
architecture_array = [
    "",
    "universal",
    "x86_32",
    "x86_64",
    "arm32",
    "arm64",
    "rv64",
    "ppc32",
    "ppc64",
    "wasm32",
]
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

platforms = ["linux", "macos", "windows"]


def exists(env):
    return True


def options(opts, env):
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

    opts.Add(
        PathVariable(
            key="build_dir",
            help="Path to directory containing build file",
            default=env.get("build_dir", None),
            validator=validate_dir,
        )
    )

    opts.Add(
        PathVariable(
            key="custom_tools",
            help="Path to directory containing custom tools",
            default=env.get("custom_tools", None),
            validator=validate_dir,
        )
    )

    opts.Update(env)

    project_platforms = get_project_platforms(env)
    custom_platforms = get_custom_platforms(env)

    opts.Add(
        EnumVariable(
            key="platform",
            help="Target platform",
            default=env.get("platform", default_platform),
            allowed_values=platforms + custom_platforms,
            ignorecase=2,
        )
    )

    # Editor and template_debug are compatible (i.e. you can use the same binary for editor builds and debug templates).
    # Release templates are only compatible with "template_release" builds.
    # For this reason, we default to template_debug builds.
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

    opts.Add(
        BoolVariable(
            key="use_hot_reload",
            help="Enable the extra accounting required to support hot reload.",
            default=env.get("use_hot_reload", False),
        )
    )

    opts.Add(
        BoolVariable(
            "disable_exceptions", "Force disabling exception handling code", default=env.get("disable_exceptions", True)
        )
    )

    opts.Add(
        BoolVariable("disable_rtti", "Force disabling runtime type information", default=env.get("disable_rtti", True))
    )

    opts.Add(
        EnumVariable(
            key="symbols_visibility",
            help="Symbols visibility on GNU platforms. Use 'auto' to apply the default value.",
            default=env.get("symbols_visibility", "hidden"),
            allowed_values=["auto", "visible", "hidden"],
        )
    )

    opts.Add(
        EnumVariable(
            "optimize",
            "The desired optimization flags. Inferred from 'target' and 'dev_build' by default.",
            "auto",
            ("auto", "none", "custom", "debug", "speed", "speed_trace", "size"),
        )
    )
    opts.Add(
        EnumVariable(
            "lto",
            "Link-time optimization",
            "none",
            ("none", "auto", "thin", "full"),
        )
    )
    opts.Add(
        EnumVariable(
            "harden_memory",
            "Library memory hardening. Inferred from 'dev_build' by default.",
            "auto",
            ["auto", "none", "fast"],
            ignorecase=2,
        )
    )
    opts.Add(BoolVariable("debug_symbols", "Build with debugging symbols", True))
    opts.Add(BoolVariable("dev_build", "Developer build with dev-only debugging code (DEV_ENABLED)", False))
    opts.Add(BoolVariable("verbose", "Enable verbose output for the compilation", False))
    opts.Add(BoolVariable("progress", "Show a progress indicator during compilation", True))
    opts.Add(BoolVariable("use_pch", "Enable precompiled headers when the toolchain supports it", True))

    # Add platform options (custom tools can override platforms)
    for pl in sorted(set(platforms + project_platforms + custom_platforms)):
        tool = Tool(pl, toolpath=get_platform_tools_paths(env))
        if hasattr(tool, "options"):
            tool.options(opts)


def generate(env):
    env.scons_version = env._get_major_minor_revision(scons_raw_version)

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

    # Process CPU architecture argument.
    if env["arch"] == "":
        # No architecture specified. Default to arm64 if building for Android,
        # universal if building for macOS or iOS, wasm32 if building for web,
        # otherwise default to the host architecture.
        if env["platform"] in ["macos", "ios"]:
            env["arch"] = "universal"
        elif env["platform"] == "android":
            env["arch"] = "arm64"
        elif env["platform"] == "web":
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
                env.Exit(1)

    print("Building for architecture " + env["arch"] + " on platform " + env["platform"])

    # These defaults may be needed by platform tools
    env.use_hot_reload = env["use_hot_reload"]
    env.editor_build = env["target"] == "editor"
    env.dev_build = env["dev_build"]
    env.debug_features = env["target"] in ["editor", "template_debug"]

    opt_level = env["optimize"]
    if env["optimize"] == "auto":
        if env.dev_build:
            opt_level = "none"
        elif env.debug_features:
            opt_level = "speed_trace"
        else:  # Release
            opt_level = "speed"

    env["optimize"] = ARGUMENTS.get("optimize", opt_level)

    harden_level = env["harden_memory"]
    if env["harden_memory"] == "auto":
        if env.dev_build:
            harden_level = "none"
        else:
            harden_level = "fast"

    env["harden_memory"] = ARGUMENTS.get("harden_memory", harden_level)

    env["debug_symbols"] = get_cmdline_bool("debug_symbols", env.dev_build)

    tool = Tool(env["platform"], toolpath=get_platform_tools_paths(env))

    if tool is None or not tool.exists(env):
        raise ValueError("Required toolchain not found for platform " + env["platform"])

    tool.generate(env)

    project_tools_dir = env.Dir("../tools").srcnode()
    if project_tools_dir.exists():
        for pl in sorted(set(get_project_platforms(env)) - set(platforms)):
            tool = Tool(pl, toolpath=[project_tools_dir.abspath])
            if hasattr(tool, "generate"):
                tool.generate(env)

    env.Decider("MD5-timestamp")

    scons_cache_path = os.environ.get("SCONS_CACHE")
    if scons_cache_path is not None:
        env.CacheDir(scons_cache_path)
        print("Scons cache enabled... (path: '" + scons_cache_path + "')")

    # Always presume godot-cpp thread=yes
    env.Append(CPPDEFINES=["THREADS_ENABLED"])

    if env.use_hot_reload:
        env.Append(CPPDEFINES=["HOT_RELOAD_ENABLED"])

    if env.editor_build:
        env.Append(CPPDEFINES=["TOOLS_ENABLED"])

    if env.debug_features:
        # DEBUG_ENABLED enables debugging *features* and debug-only code, which is intended
        # to give *users* extra debugging information for their development.
        env.Append(CPPDEFINES=["DEBUG_ENABLED"])

    if env.dev_build:
        # DEV_ENABLED enables *developer* code which should only be compiled for those
        # working on the project itself.
        env.Append(CPPDEFINES=["DEV_ENABLED"])
    else:
        # Disable assert() for production targets.
        env.Append(CPPDEFINES=["NDEBUG"])

    if env["precision"] == "double":
        env.Append(CPPDEFINES=["REAL_T_IS_DOUBLE"])

    # Suffix
    suffix = ".{}.{}".format(env["platform"], env["target"])
    if env.dev_build:
        suffix += ".dev"
    if env["precision"] == "double":
        suffix += ".double"
    suffix += "." + env["arch"]
    if env["platform"] == "windows":
        if env.get("debug_crt", False):
            suffix += ".mdd"
        elif env.get("use_static_cpp", False):
            suffix += ".mt"
        else:
            suffix += ".md"
    if env.get("use_asan", False):
        suffix += ".san"

    env["BUILDSUFFIX"] = suffix  # Exposed when included from another project
    env["OLDPROGSUFFIX"] = env.subst("$PROGSUFFIX")
    env["OLDOBJSUFFIX"] = env.subst("$OBJSUFFIX")
    env["OLDSHOBJSUFFIX"] = env.subst("$SHOBJSUFFIX")
    env["OLDLIBSUFFIX"] = env.subst("$LIBSUFFIX")
    env["OLDSHLIBSUFFIX"] = env.subst("$SHLIBSUFFIX")
    env["PROGSUFFIX"] = "${BUILDSUFFIX}${OLDPROGSUFFIX}"
    env["OBJSUFFIX"] = "${BUILDSUFFIX}${OLDOBJSUFFIX}"
    env["SHOBJSUFFIX"] = "${BUILDSUFFIX}${OLDSHOBJSUFFIX}"
    env["LIBSUFFIX"] = "${BUILDSUFFIX}${OLDLIBSUFFIX}"
    env["SHLIBSUFFIX"] = "${BUILDSUFFIX}${OLDSHLIBSUFFIX}"

    if env.is_standalone:
        if "build_dir" in env:
            env["build_dir"] = env.Dir(env["build_dir"]).srcnode()
        else:
            env["build_dir"] = env.Dir("#build").Dir(env["BUILDSUFFIX"].lstrip("."))
    else:
        env["build_dir"] = env.Dir(".")

    if "gen_dir" in env:
        env["gen_dir"] = env.Dir(env["build_dir"]).Dir(env["gen_dir"])
    else:
        env["gen_dir"] = env.Dir(env["build_dir"])

    if env["compiledb"] and env.is_standalone:
        # compile_commands.json
        env.Tool("compilation_db")
        env.Alias("compiledb", env.CompilationDatabase(normalize_path(env["compiledb_file"], env)))
        env.Default("compiledb")
        if not env["verbose"]:
            env["COMPILATIONDB_COMSTR"] = "$GENCOMSTR"

    # Formatting
    if not env["verbose"]:
        no_verbose(env)

    # Builders
    env.Append(
        BUILDERS={
            "License": Builder(action=license_builder, emitter=project_info_generator_emitter),
            "Git": Builder(action=git_builder, emitter=project_info_generator_emitter),
            "Author": Builder(action=author_builder, emitter=project_info_generator_emitter),
        }
    )
    env.GlobRecursive = GlobRecursive
    env.AddMethod(get_git_info, "GetGitInfo")
    env.AddMethod(GlobRecursiveVariant, "GlobRecursiveVariant")

    env.AddMethod(add_library_includes, "AddLibraryIncludes")
    env.AddMethod(add_library_sources, "AddLibrarySources")

    env.AddMethod(build_base_library, "BuildBaseLibrary")
    env.AddMethod(build_headless_program, "BuildHeadlessProgram")
    env.AddMethod(build_unit_test, "BuildUnitTest")
    env.AddMethod(build_benchmark, "BuildBenchmark")
    env.AddMethod(build_dependency_library, "BuildDependencyLibrary")

    add_gch_builder(env)

    if not env.GetOption("clean") and not env.GetOption("help") and env.is_standalone:
        dump(env)
        show_progress(env)
        prepare_purge(env)
        prepare_timer()
