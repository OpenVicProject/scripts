#!/usr/bin/env python

# This file is heavily based on https://github.com/godotengine/godot-cpp/blob/ba0edfed90512ec64aba51d4295a3e7e30112f86/SConstruct
import os
import sys

import SCons

remove_module = [module_name for module_name in sys.modules if module_name.startswith("build.")]
if "build" in sys.modules.keys():
    del sys.modules["build"]
for module_name in remove_module:
    del sys.modules[module_name]

# Add scripts folder to sys.path, so that we can import local modules.
sys.path.append(Dir(".").srcnode().abspath)

import build.scripts as scripts_tool

is_standalone = SCons.Script.sconscript_reading == 2

try:
    Import("env")
    parent_env = env
    env = Environment(tools=["default"], PLATFORM="")
    env.parent_env = parent_env
except Exception:
    # Default tools with no platform defaults to gnu toolchain.
    # We apply platform specific toolchains via our custom tools.
    env = Environment(tools=["default"], PLATFORM="")

try:
    Import("gen_dir")
    env["gen_dir"] = gen_dir
except Exception:
    pass

env.is_standalone = is_standalone

env.PrependENVPath("PATH", os.getenv("PATH"))

if env.get("parent_env", None) is not None:
    skip_parent_item = True
    for key in parent_env.Dictionary():
        if skip_parent_item:
            if key == "arch":
                skip_parent_item = False
            else:
                continue
        env[key] = parent_env[key]

# Custom options and profile flags.
customs = ["custom.py"]
try:
    customs += Import("customs")
except Exception:
    pass
profile = ARGUMENTS.get("profile", "")
if profile:
    if os.path.isfile(profile):
        customs.append(profile)
    elif os.path.isfile(profile + ".py"):
        customs.append(profile + ".py")

if "custom_tools" not in env:
    try:
        Import("custom_tools")
        env["custom_tools"] = custom_tools
    except Exception:
        pass

opts = Variables(customs, ARGUMENTS)
scripts_tool.options(opts, env)
opts.Update(env)

Help(opts.GenerateHelpText(env))

scripts_tool.generate(env)

# Prevent this scripts' from polluting later module imports.
sys.path.remove(Dir(".").srcnode().abspath)

Return("env")
