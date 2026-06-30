def no_verbose(env):
    from build.color import Ansi, is_stdout_color

    colors = [Ansi.BLUE, Ansi.BOLD, Ansi.REGULAR, Ansi.RESET] if is_stdout_color() else ["", "", "", ""]

    # There is a space before "..." to ensure that source file names can be
    # Ctrl + clicked in the VS Code terminal.
    compile_source_message = "{}Compiling {}$SOURCE{} ...{}".format(*colors)
    java_compile_source_message = "{}Compiling {}$SOURCE{} ...{}".format(*colors)
    compile_shared_source_message = "{}Compiling shared {}$SOURCE{} ...{}".format(*colors)
    link_program_message = "{}Linking Program {}$TARGET{} ...{}".format(*colors)
    link_library_message = "{}Linking Static Library {}$TARGET{} ...{}".format(*colors)
    ranlib_library_message = "{}Ranlib Library {}$TARGET{} ...{}".format(*colors)
    link_shared_library_message = "{}Linking Shared Library {}$TARGET{} ...{}".format(*colors)
    java_library_message = "{}Creating Java Archive {}$TARGET{} ...{}".format(*colors)
    compiled_resource_message = "{}Creating Compiled Resource {}$TARGET{} ...{}".format(*colors)
    zip_archive_message = "{}Archiving {}$TARGET{} ...{}".format(*colors)
    precompile_header_message = "{}Precompiling {}$SOURCE{} ...{}".format(*colors)
    generated_file_message = "{}Generating {}$TARGET{} ...{}".format(*colors)

    env["CXXCOMSTR"] = compile_source_message
    env["CCCOMSTR"] = compile_source_message
    env["SWIFTCOMSTR"] = compile_source_message
    env["SHCCCOMSTR"] = compile_shared_source_message
    env["SHCXXCOMSTR"] = compile_shared_source_message
    env["ARCOMSTR"] = link_library_message
    env["RANLIBCOMSTR"] = ranlib_library_message
    env["SHLINKCOMSTR"] = link_shared_library_message
    env["LINKCOMSTR"] = link_program_message
    env["JARCOMSTR"] = java_library_message
    env["JAVACCOMSTR"] = java_compile_source_message
    env["RCCOMSTR"] = compiled_resource_message
    env["ZIPCOMSTR"] = zip_archive_message
    env["PCHCOMSTR"] = precompile_header_message
    env["GCHCOMSTR"] = precompile_header_message
    env["GCHSHCOMSTR"] = precompile_header_message
    env["GENCOMSTR"] = generated_file_message
