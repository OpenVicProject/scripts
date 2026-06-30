import SCons.Action
import SCons.Builder
import SCons.Errors
import SCons.Tool
import SCons.Util


def gch_emitter(target, source, env):
    """Ensure proper suffix and dependency tracking."""

    gch = None

    for t in target:
        if SCons.Util.splitext(str(t))[1] == ".gch":
            gch = t

    target = [gch]
    return (target, source)


gch_action = SCons.Action.Action("$GCHCOM", "$GCHCOMSTR")
gch_builder = SCons.Builder.Builder(
    action=gch_action, suffix=".gch", emitter=gch_emitter, source_scanner=SCons.Tool.SourceFileScanner
)

gchsh_action = SCons.Action.Action("$GCHSHCOM", "$GCHSHCOMSTR")
gchsh_builder = SCons.Builder.Builder(
    action=gchsh_action, suffix=".gch", emitter=gch_emitter, source_scanner=SCons.Tool.SourceFileScanner
)


def get_gch_node(env, target, source):
    """
    Get the actual GCH file node
    """
    gch_subst = env.get("GCH", False) and env.subst("$GCH", target=target, source=source, conv=lambda x: x)

    if not gch_subst:
        return ""

    if SCons.Util.is_String(gch_subst):
        gch_subst = target[0].dir.File(gch_subst)

    return gch_subst


def add_gch_builder(env):
    """Add Gch / GchSh builders to the environment."""

    if not env.Detect(["g++", "gcc", "clang++"]):
        return

    # Command to build a gch from a header
    env["GCHCOM"] = "$CXX -x c++-header -o $TARGET $CXXFLAGS $CCFLAGS $_CCCOMCOM $SOURCE"
    env["BUILDERS"]["GCH"] = gch_builder

    env["GCHSHCOM"] = "$CXX -x c++-header -o $TARGET $SHCXXFLAGS $SHCCFLAGS $_CCCOMCOM $SOURCE"
    env["BUILDERS"]["GCHSH"] = gchsh_builder

    def gch_dependent_emitter(target, source, env, parent_emitter):
        parent_emitter(target, source, env)

        if not env.get("GCH"):
            return target, source

        gch = get_gch_node(env, target, source)
        if gch:
            if str(target[0]) not in [SCons.Util.splitext(str(gch))[0] + s for s in [".so", ".os", ".o"]]:
                env.Depends(target, gch)

        return target, source

    def gch_dependent_static_emitter(target, source, env):
        return gch_dependent_emitter(target, source, env, SCons.Defaults.StaticObjectEmitter)

    def gch_dependent_shared_emitter(target, source, env):
        return gch_dependent_emitter(target, source, env, SCons.Defaults.SharedObjectEmitter)

    modify_builders = [
        ("StaticObject", gch_dependent_static_emitter),
        ("SharedObject", gch_dependent_shared_emitter),
        ("Object", gch_dependent_static_emitter),
    ]

    for builder_tuple in modify_builders:
        if builder_tuple[0] not in env["BUILDERS"]:
            continue

        bld = env["BUILDERS"][builder_tuple[0]]
        bld.add_emitter(".cpp", builder_tuple[1])
        bld.add_emitter(".cc", builder_tuple[1])
        bld.add_emitter(".cxx", builder_tuple[1])
        bld.add_emitter(".c", builder_tuple[1])
