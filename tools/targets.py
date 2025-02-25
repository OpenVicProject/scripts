# Copied from https://github.com/godotengine/godot-cpp/blob/df5b1a9a692b0d972f5ac3c853371594cdec420b/tools/targets.py
import os
import subprocess
import sys
from SCons.Script import ARGUMENTS
from SCons.Variables import EnumVariable, BoolVariable
from SCons.Variables.BoolVariable import _text2bool


# Helper methods


def get_cmdline_bool(option, default):
    """We use `ARGUMENTS.get()` to check if options were manually overridden on the command line,
    and SCons' _text2bool helper to convert them to booleans, otherwise they're handled as strings.
    """
    cmdline_val = ARGUMENTS.get(option)
    if cmdline_val is not None:
        return _text2bool(cmdline_val)
    else:
        return default


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


# Main tool definition


def options(opts):
    opts.Add(
        EnumVariable(
            "optimize",
            "The desired optimization flags",
            "speed_trace",
            ("none", "custom", "debug", "speed", "speed_trace", "size"),
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
    opts.Add(BoolVariable("debug_symbols", "Build with debugging symbols", True))
    opts.Add(BoolVariable("dev_build", "Developer build with dev-only debugging code (DEV_ENABLED)", False))


def exists(env):
    return True


def generate(env):
    # Configuration of build targets:
    # - Editor or template
    # - Debug features (DEBUG_ENABLED code)
    # - Dev only code (DEV_ENABLED code)
    # - Optimization level
    # - Debug symbols for crash traces / debuggers

    # Keep this configuration in sync with SConstruct in upstream Godot.

    env.use_hot_reload = env.get("use_hot_reload", env["target"] != "template_release")
    env.editor_build = env["target"] == "editor"
    env.dev_build = env["dev_build"]
    env.debug_features = env["target"] in ["editor", "template_debug"]

    if env.dev_build:
        opt_level = "none"
    elif env.debug_features:
        opt_level = "speed_trace"
    else:  # Release
        opt_level = "speed"

    env["optimize"] = ARGUMENTS.get("optimize", opt_level)
    env["debug_symbols"] = get_cmdline_bool("debug_symbols", env.dev_build)

    if env.use_hot_reload:
        env.Append(CPPDEFINES=["HOT_RELOAD_ENABLED"])

    if env.editor_build:
        env.Append(CPPDEFINES=["TOOLS_ENABLED"])

    if env.debug_features:
        # DEBUG_ENABLED enables debugging *features* and debug-only code, which is intended
        # to give *users* extra debugging information for their game development.
        env.Append(CPPDEFINES=["DEBUG_ENABLED"])
        # In upstream Godot this is added in typedefs.h when DEBUG_ENABLED is set.
        env.Append(CPPDEFINES=["DEBUG_METHODS_ENABLED"])

    if env.dev_build:
        # DEV_ENABLED enables *engine developer* code which should only be compiled for those
        # working on the engine itself.
        env.Append(CPPDEFINES=["DEV_ENABLED"])
    else:
        # Disable assert() for production targets (only used in thirdparty code).
        env.Append(CPPDEFINES=["NDEBUG"])
