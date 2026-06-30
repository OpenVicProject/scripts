import os

from build.glob_recursive import GlobRecursive


def add_library_includes(env, include_dir, expose_includes=True, add_variant_dir=False, variant_dir=None):
    """
    include_dir is the location(s) to add to the CPPPATH
    expose_includes determines whether location(s) are added to env.exposed_includes
    add_variant_dir determines whether the include automatically includes the vairiant_dir (does nothing if variant_dir is specified)
    variant_dir is the VariantDir to include alongside include_dir as variant_dir/include_dir
    """

    if add_variant_dir and not variant_dir:
        variant_dir = env["build_dir"]

    if isinstance(include_dir, list):
        result = []
        for d in include_dir:
            result.append(
                add_library_includes(
                    env, d, expose_includes=expose_includes, add_variant_dir=add_variant_dir, variant_dir=variant_dir
                )
            )
        return result

    if isinstance(include_dir, str):
        include_dir = env.Dir(include_dir).srcnode()

    if variant_dir:
        return add_library_includes(env, [variant_dir.Dir(include_dir), include_dir], expose_includes=expose_includes)

    env.AppendUnique(CPPPATH=[include_dir])

    try:
        env["INCPATH"]
    except Exception:
        env["INCPATH"] = []
    env["INCPATH"] += [include_dir]

    if expose_includes:
        try:
            env.exposed_includes
        except Exception:
            env.exposed_includes = []
        env.exposed_includes += [include_dir]

    return include_dir


def add_library_sources(env, src_dir, glob="*.cpp", exclude=None, variant_dir=None):
    """
    src_dir is the root directory to glob for files from
    variant_dir is the VariantDir to source from and build files into
    glob is a directory recursive glob over files inside src_dir
    exclude are the files or list of files to exclude from the glob
    """

    if isinstance(src_dir, list):
        result = []
        for d in src_dir:
            result.append(
                add_library_sources(env=env, src_dir=src_dir, glob=glob, exclude=exclude, variant_dir=variant_dir)
            )
        return result

    if variant_dir:
        variant_dir = env["build_dir"].Dir(variant_dir)
    elif env.Dir(".") != env.Dir(".").srcnode():
        variant_dir = env.Dir(".")
    else:
        variant_dir = env["build_dir"]

    src_variant_dir = variant_dir.Dir(src_dir)

    if isinstance(src_dir, str):
        src_dir = env.Dir(src_dir).srcnode()

    env.AppendUnique(CPPPATH=[src_variant_dir, src_dir])

    try:
        env.sources
    except Exception:
        env.sources = []

    env.sources += GlobRecursive(glob, src_variant_dir, exclude=exclude)
    return src_variant_dir


def build_base_library(env, target, variant_dir=None):
    """
    target is the target to build
    variant_dir is the VariantDir to build the library into
    """

    if variant_dir:
        variant_dir = env["build_dir"].Dir(variant_dir)
    elif env.Dir(".") != env.Dir(".").srcnode():
        variant_dir = env.Dir(".")
    else:
        variant_dir = env["build_dir"]

    target_location = None
    if env.Dir(".") == env.Dir(".").srcnode():
        target_location = os.path.join(variant_dir.File(target).dir, os.path.basename(target))
    else:
        target_location = target

    env.library = env.StaticLibrary(
        target=target_location,
        source=env.sources,
    )
    env.NoCache(env.library)

    env.Depends(env.library, env["LIBS"])

    env.Default(env.library)
    if env.is_standalone:
        env.Default(env.InstallAs(env.File(env.library[0]).srcnode(), env.library[0]))

    env.PrependUnique(LIBS=[env.library[0]])

    return env.library


def build_headless_program(env, target, src_dir, defines_prefix, include_lib_src, variant_dir=None):
    """
    target is the target to build
    src_dir is the headless source directory
    defines_prefix is the prefix (to be uppercased) for the HEADLESS define
    include_lib_src determines whether the headless environment includes previous sources
    variant_dir is the VariantDir to build the program into
    """

    headless_env = env.Clone()
    headless_env.Append(CPPDEFINES=[f"{defines_prefix.upper()}_HEADLESS"])

    if variant_dir:
        variant_dir = headless_env["build_dir"].Dir(variant_dir)
    elif headless_env.Dir(".") != headless_env.Dir(".").srcnode():
        variant_dir = headless_env.Dir(".")
    else:
        variant_dir = headless_env["build_dir"]

    target_location = None
    if headless_env.Dir(".") == headless_env.Dir(".").srcnode():
        target_location = os.path.join(variant_dir.File(target).dir, os.path.basename(target))
    else:
        target_location = target

    if not include_lib_src:
        headless_env.sources = []

    add_library_sources(headless_env, src_dir)

    headless_program = headless_env.Program(
        target=target_location,
        source=headless_env.sources,
        PROGSUFFIX=".headless" + headless_env.subst("$PROGSUFFIX"),
        OBJSUFFIX=".headless" + headless_env.subst("$OBJSUFFIX"),
    )
    env.NoCache(headless_program)

    env.Depends(headless_program, env["LIBS"])

    env.Default(headless_program)
    if env.is_standalone:
        env.Default(env.InstallAs(env.File(headless_program[0]).srcnode(), headless_program[0]))

    return headless_program


def build_unit_test(env, target, src_dir, defines_prefix, variant_dir=None, **kwargs):
    """
    target is the target to build
    src_dir is the unit test source directory
    defines_prefix is the prefix (to be uppercased) for the TESTS define
    variant_dir is the VariantDir to build the program into
    kwargs are passed to env.Program as is
    """

    if variant_dir:
        variant_dir = env["build_dir"].Dir(variant_dir)
    elif env.Dir(".") != env.Dir(".").srcnode():
        variant_dir = env.Dir(".")
    else:
        variant_dir = env["build_dir"]

    env.Append(CPPDEFINES=[f"{defines_prefix.upper()}_TESTS"])

    target_location = None
    if env.Dir(".") == env.Dir(".").srcnode():
        target_location = os.path.join(variant_dir.File(target).dir, os.path.basename(target))
    else:
        target_location = target

    env.sources = []
    add_library_sources(env, src_dir, variant_dir=variant_dir)

    env.unit_test = env.Program(
        target=target_location,
        source=env.sources,
        PROGSUFFIX=".tests" + env.subst("$PROGSUFFIX"),
        OBJSUFFIX=".tests" + env.subst("$OBJSUFFIX"),
        **kwargs,
    )
    env.NoCache(env.unit_test)

    env.Depends(env.unit_test, env["LIBS"])

    env.Default(env.unit_test)
    if env.is_standalone:
        env.Default(env.InstallAs(env.File(env.unit_test[0]).srcnode(), env.unit_test[0]))

    def run_unit_test(env):
        def run_unit_test_post_action(target=None, source=None, env=None):
            import subprocess

            print()
            return subprocess.run([target[0].path]).returncode

        unit_test_action = env.Action(run_unit_test_post_action, None)
        test_post_action = env.AddPostAction(env.unit_test, unit_test_action)
        env.AlwaysBuild(test_post_action)

    env.AddMethod(run_unit_test, "RunUnitTest")

    return env

def build_benchmark(env, target, src_dir, defines_prefix, variant_dir=None, **kwargs):
    """
    target is the target to build
    src_dir is the unit test source directory
    defines_prefix is the prefix (to be uppercased) for the TESTS define
    variant_dir is the VariantDir to build the program into
    kwargs are passed to env.Program as is
    """

    if variant_dir:
        variant_dir = env["build_dir"].Dir(variant_dir)
    elif env.Dir(".") != env.Dir(".").srcnode():
        variant_dir = env.Dir(".")
    else:
        variant_dir = env["build_dir"]

    env.Append(CPPDEFINES=[f"{defines_prefix.upper()}_BENCHMARKS"])

    target_location = None
    if env.Dir(".") == env.Dir(".").srcnode():
        target_location = os.path.join(variant_dir.File(target).dir, os.path.basename(target))
    else:
        target_location = target

    env.sources = []
    add_library_sources(env, src_dir, variant_dir=variant_dir)

    env.benchmark = env.Program(
        target=target_location,
        source=env.sources,
        PROGSUFFIX=".benchmarks" + env.subst("$PROGSUFFIX"),
        OBJSUFFIX=".benchmarks" + env.subst("$OBJSUFFIX"),
        **kwargs,
    )
    env.NoCache(env.benchmark)

    env.Depends(env.benchmark, env["LIBS"])

    env.Default(env.benchmark)
    if env.is_standalone:
        env.Default(env.InstallAs(env.File(env.benchmark[0]).srcnode(), env.benchmark[0]))

    def run_benchmark(env):
        def run_benchmark_post_action(target=None, source=None, env=None):
            import subprocess

            print()
            return subprocess.run([target[0].path]).returncode

        benchmark_action = env.Action(run_benchmark_post_action, None)
        test_post_action = env.AddPostAction(env.benchmark, benchmark_action)
        env.AlwaysBuild(test_post_action)

    env.AddMethod(run_benchmark, "RunBenchmark")

    return env


def add_external_includes(env, include_dir):
    if isinstance(include_dir, list):
        result = []
        for d in include_dir:
            result.append(add_external_includes(env, d))
        return result

    if isinstance(include_dir, str):
        include_dir = env.Dir(include_dir)

    if env.get("is_msvc", False):
        env.AppendUnique(CXXFLAGS=[f"/external:I{include_dir}", "/external:W0"])
    else:
        env.Append(CXXFLAGS=["-isystem", include_dir])


def build_dependency_library(
    parent_env, target, src_dir, include_dir, variant_dir=None, glob="*.cpp", exclude=None, shared_library=False
):
    """
    target is the target to build
    src_dir is the library source directory
    include_dir is library include directory
    variant_dir is the VariantDir to build the library into
    glob is a directory recursive glob over files inside src_dir
    exclude are the files or list of files to exclude from the glob
    shared_library determines whether the library is built as a shared library
    """

    add_library_includes(parent_env, include_dir)
    env = parent_env.Clone()

    if variant_dir:
        variant_dir = env["build_dir"].Dir(variant_dir)
    elif env.Dir(".") != env.Dir(".").srcnode():
        variant_dir = env.Dir(".")
    else:
        variant_dir = env["build_dir"]

    if exclude is None:
        pass
    elif isinstance(exclude, str):
        exclude = [env.Dir(src_dir).File(exclude)]
    else:
        exclude = [env.Dir(src_dir).File(e) for e in exclude]

    env.sources = []
    add_library_sources(env, src_dir, glob=glob, exclude=exclude, variant_dir=variant_dir)

    if shared_library:
        library = env.SharedLibrary(target=target, source=env.sources)
    else:
        library = env.StaticLibrary(target=target, source=env.sources)
    env.NoCache(library)

    add_external_includes(parent_env, include_dir)

    parent_env.PrependUnique(LIBS=[library])

    return env, library
