def setup_pch(env, header_rel, source_cpp_variant):
    if not env.get("use_pch", True):
        return

    handler = _select_handler(env)
    if handler is None:
        return

    name = handler(env, header_rel, source_cpp_variant)
    print(f"[PCH] enabled ({name}): {header_rel}")


def _select_handler(env):
    if env.get("is_msvc", False):
        return _msvc_pch
    # TODO: GCC/Clang/MinGW
    return None


def _msvc_pch(env, header_rel, source_cpp_variant):
    env["PCHSTOP"] = header_rel
    pch_pch, _pch_obj = env.PCH(source_cpp_variant)
    env["PCH"] = pch_pch
    env.Append(CCFLAGS=["/FI" + header_rel])
    return "msvc"
