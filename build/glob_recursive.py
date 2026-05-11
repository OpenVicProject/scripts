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
