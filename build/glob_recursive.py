def GlobRecursive(pattern, nodes=["."], exclude=None):
    import fnmatch

    import SCons

    fs = SCons.Node.FS.get_default_fs()
    Glob = fs.Glob

    if isinstance(exclude, str):
        exclude = [exclude]

    results = []
    for node in nodes:
        nnodes = []
        for f in Glob(str(node) + "/*", source=True):
            if type(f) is SCons.Node.FS.Dir:
                nnodes.append(f)
        results += GlobRecursive(pattern, nnodes)
        results += Glob(str(node) + "/" + pattern, source=True)
        if isinstance(exclude, list):
            for val in results:
                for pat in exclude:
                    if fnmatch.fnmatch(str(val), pat):
                        results.remove(val)
    return results
