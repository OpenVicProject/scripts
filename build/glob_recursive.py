def GlobRecursive(pattern, nodes=["."], exclude=None):
    import fnmatch
    import os

    import SCons

    fs = SCons.Node.FS.get_default_fs()
    Glob = fs.Glob

    if isinstance(exclude, str):
        exclude = [exclude]

    results = []
    for node in nodes:
        node_str = str(node)

        for f in Glob(node_str + "/*", source=True):
            if type(f) is SCons.Node.FS.Dir:
                child = node_str + "/" + os.path.basename(str(f))
                results += GlobRecursive(pattern, [child])

        results += Glob(node_str + "/" + pattern)

    if isinstance(exclude, list):

        def norm(s):
            return str(s).replace("\\", "/")

        norm_exclude = [norm(p) for p in exclude]
        results = [r for r in results if not any(fnmatch.fnmatch(norm(r), p) for p in norm_exclude)]
    return results


def GlobRecursiveVariant(env, pattern, src_root, variant_root, exclude=None):
    src_nodes = GlobRecursive(pattern, [src_root])
    src_abs = env.Dir(src_root).abspath.replace("\\", "/").rstrip("/") + "/"
    variant_prefix = env.Dir(variant_root).abspath.replace("\\", "/").rstrip("/") + "/"
    if exclude is None:
        exclude_abs = set()
    else:
        if isinstance(exclude, str):
            exclude = [exclude]
        exclude_abs = {env.File(e).abspath.replace("\\", "/") for e in exclude}
    out = []
    for n in src_nodes:
        p = n.abspath.replace("\\", "/")
        if p in exclude_abs:
            continue
        assert p.startswith(src_abs), f"{p!r} not under {src_abs!r}"
        out.append(env.File(variant_prefix + p[len(src_abs) :]))
    return out
