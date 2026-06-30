def GlobRecursive(pattern, nodes=["."], exclude=None):
    import os

    import SCons

    fs = SCons.Node.FS.get_default_fs()
    Glob = fs.Glob
    Dir = fs.Dir

    if not isinstance(nodes, list):
        nodes = [nodes]

    if isinstance(exclude, str):
        exclude = [exclude]

    results = []
    for node in nodes:
        node_str = str(node)

        for f in Glob(f"{node_str}/*", source=True):
            if type(f) is SCons.Node.FS.Dir:
                child = os.path.join(node_str, f.name)
                results += GlobRecursive(pattern, [child])

        results += Glob(f"{node_str}/{pattern}")

    if isinstance(exclude, list):
        val_to_remove = set()
        for e in exclude:
            for index in range(len(results)):
                val = results[index]
                for node in nodes:
                    if str(val) == str(Dir(node).File(e)):
                        val_to_remove.add(val)

        for val in val_to_remove:
            results.remove(val)

    return results


def GlobRecursiveVariant(env, pattern, src_root, variant_root, exclude=None):
    src_nodes = GlobRecursive(pattern, [src_root])
    src_abs = env.Dir(src_root).abspath.replace("\\", "/").rstrip("/") + "/"
    variant_prefix = env.Dir(variant_root).srcnode().abspath.replace("\\", "/").rstrip("/") + "/"
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
