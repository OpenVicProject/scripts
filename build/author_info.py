def author_builder(target, source, env):
    name_prefix = env.get("name_prefix", "project")
    prefix_upper = name_prefix.upper()
    sections = env.get("sections", {"Developers": "AUTHORS_DEVELOPERS"})

    def get_buffer() -> bytes:
        with open(str(source[0]), "rb") as file:
            return file.read()

    buffer = get_buffer()

    reading = False

    with open(str(target[0]), "wt", encoding="utf-8", newline="\n") as file:
        file.write("/* THIS FILE IS GENERATED. EDITS WILL BE LOST. */\n\n")
        file.write(
            """\
#pragma once

#include <array>
#include <string_view>

namespace OpenVic {
"""
        )

        def close_section():
            file.write("\t});\n")

        for line in buffer.decode().splitlines():
            if line.startswith("    ") and reading:
                file.write(f'\t\t"{env.to_escaped_cstring(line).strip()}",\n')
            elif line.startswith("## "):
                if reading:
                    close_section()
                    file.write("\n")
                    reading = False
                section = sections.get(line[3:].strip(), None)
                if section:
                    file.write(
                        f"\tstatic constexpr std::array {prefix_upper}_{section} = std::to_array<std::string_view>({{\n"
                    )
                    reading = True

        if reading:
            close_section()

        file.write("}")
