#!/usr/bin/env python
"""Standalone code generators for the OpenVic CMake builds.

Stdlib-only CLI generating the git/license/author info headers and the
foonathan/memory config headers. Outputs are written only when their content
changes so build systems don't see spurious mtime bumps.

Subcommands:
    commit-info        gen/commit_info.gen.hpp   (git tag/release/hash/timestamp)
    license-info       gen/license_info.gen.hpp  (COPYRIGHT + LICENSE.md)
    author-info        gen/author_info.gen.hpp   (AUTHORS.md sections)
    memory-config      foonathan/memory config_impl.hpp
    memory-node-sizes  foonathan/memory detail/container_node_sizes_impl.hpp
"""

import argparse
import os
import subprocess
import sys
from collections import OrderedDict
from typing import List, Union

# --- shared helpers ---


def to_raw_cstring(value: Union[str, List[str]]) -> str:
    MAX_LITERAL = 16380

    if isinstance(value, list):
        value = "\n".join(value) + "\n"

    split: List[bytes] = []
    offset = 0
    encoded = value.encode()

    while offset <= len(encoded):
        segment = encoded[offset : offset + MAX_LITERAL]
        offset += MAX_LITERAL
        if len(segment) == MAX_LITERAL:
            # Try to segment raw strings at double newlines to keep readable.
            pretty_break = segment.rfind(b"\n\n")
            if pretty_break != -1:
                segment = segment[: pretty_break + 1]
                offset -= MAX_LITERAL - pretty_break - 1
            # If none found, ensure we end with valid utf8.
            # https://github.com/halloleo/unicut/blob/master/truncate.py
            elif segment[-1] & 0b10000000:
                last_11xxxxxx_index = [i for i in range(-1, -5, -1) if segment[i] & 0b11000000 == 0b11000000][0]
                last_11xxxxxx = segment[last_11xxxxxx_index]
                if not last_11xxxxxx & 0b00100000:
                    last_char_length = 2
                elif not last_11xxxxxx & 0b0010000:
                    last_char_length = 3
                elif not last_11xxxxxx & 0b0001000:
                    last_char_length = 4

                if last_char_length > -last_11xxxxxx_index:
                    segment = segment[:last_11xxxxxx_index]
                    offset += last_11xxxxxx_index

        split += [segment]

    if len(split) == 1:
        return f'R"<!>({split[0].decode()})<!>"'
    else:
        # Wrap multiple segments in parenthesis to suppress `string-concatenation` warnings on clang.
        return "({})".format(" ".join(f'R"<!>({segment.decode()})<!>"' for segment in split))


C_ESCAPABLES = [
    ("\\", "\\\\"),
    ("\a", "\\a"),
    ("\b", "\\b"),
    ("\f", "\\f"),
    ("\n", "\\n"),
    ("\r", "\\r"),
    ("\t", "\\t"),
    ("\v", "\\v"),
    ('"', '\\"'),
]
C_ESCAPE_TABLE = str.maketrans(dict((x, y) for x, y in C_ESCAPABLES))


def to_escaped_cstring(value: str) -> str:
    return value.translate(C_ESCAPE_TABLE)


def write_if_changed(path: str, text: str, platform_newlines: bool = False) -> bool:
    """Write text to path (creating parent dirs), skipping the write when the
    on-disk bytes already match. Returns True when the file was (re)written."""
    if platform_newlines:
        data = text.replace("\n", os.linesep).encode("utf-8")
    else:
        data = text.encode("utf-8")

    try:
        with open(path, "rb") as file:
            if file.read() == data:
                return False
    except OSError:
        pass

    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "wb") as file:
        file.write(data)
    return True


# --- commit-info (ported from build/git_info.py) ---


def get_git_tag(prefix):
    tag_var_name = f"{prefix}_TAG"
    git_tag = ""
    if tag_var_name in os.environ:
        return os.environ[tag_var_name]
    else:
        git_tag = "<tag missing>"

    if os.path.exists(".git"):
        try:
            result = subprocess.check_output(["git", "describe", "--tags", "--abbrev=0"], encoding="utf-8").strip()
            if result != "":
                git_tag = result
        except (subprocess.CalledProcessError, OSError):
            # `git` not found in PATH.
            pass

    return git_tag


def get_git_release(prefix):
    release_var_name = f"{prefix}_RELEASE"
    git_release = ""
    if release_var_name in os.environ:
        return os.environ[release_var_name]
    else:
        git_release = "<release missing>"

    if os.path.exists(".git"):
        try:
            result = subprocess.check_output(
                ["gh", "release", "list", "--json", "name", "-q", ".[0] | .name"], encoding="utf-8"
            ).strip()
            if result != "":
                git_release = result
        except (subprocess.CalledProcessError, OSError):
            # `gh` not found in PATH.
            git_tag = get_git_tag(prefix)
            if git_tag != "<tag missing>":
                git_release = git_tag

    return git_release


def get_git_hash():
    # Parse Git hash if we're in a Git repo.
    git_hash = "0000000000000000000000000000000000000000"
    git_folder = ".git"

    if os.path.isfile(".git"):
        with open(".git", "r", encoding="utf-8") as file:
            module_folder = file.readline().strip()
        if module_folder.startswith("gitdir: "):
            git_folder = module_folder[8:]

    if os.path.isfile(os.path.join(git_folder, "HEAD")):
        with open(os.path.join(git_folder, "HEAD"), "r", encoding="utf8") as file:
            head = file.readline().strip()
        if head.startswith("ref: "):
            ref = head[5:]
            # If this directory is a Git worktree instead of a root clone.
            parts = git_folder.split("/")
            if len(parts) > 2 and parts[-2] == "worktrees":
                git_folder = "/".join(parts[0:-2])
            head = os.path.join(git_folder, ref)
            packedrefs = os.path.join(git_folder, "packed-refs")
            if os.path.isfile(head):
                with open(head, "r", encoding="utf-8") as file:
                    git_hash = file.readline().strip()
            elif os.path.isfile(packedrefs):
                # Git may pack refs into a single file. This code searches .git/packed-refs file for the current ref's hash.
                # https://mirrors.edge.kernel.org/pub/software/scm/git/docs/git-pack-refs.html
                for line in open(packedrefs, "r", encoding="utf-8").read().splitlines():
                    if line.startswith("#"):
                        continue
                    (line_hash, line_ref) = line.split(" ")
                    if ref == line_ref:
                        git_hash = line_hash
                        break
        else:
            git_hash = head

    # Get the UNIX timestamp of the build commit.
    git_timestamp = 0
    if os.path.exists(".git"):
        try:
            git_timestamp = subprocess.check_output(
                ["git", "log", "-1", "--pretty=format:%ct", "--no-show-signature", git_hash], encoding="utf-8"
            )
        except (subprocess.CalledProcessError, OSError):
            # `git` not found in PATH.
            pass

    return {
        "git_hash": git_hash,
        "git_timestamp": git_timestamp,
    }


def generate_commit_info(args) -> bool:
    os.chdir(args.repo_dir)
    prefix_upper = args.prefix.upper()
    git_info = {**get_git_hash(), "git_tag": get_git_tag(prefix_upper), "git_release": get_git_release(prefix_upper)}

    text = "/* THIS FILE IS GENERATED. EDITS WILL BE LOST. */\n\n"
    text += f"""\
#pragma once

#include <cstdint>
#include <string_view>

namespace OpenVic {{
	static constexpr std::string_view {prefix_upper}_TAG = "{git_info["git_tag"]}";
	static constexpr std::string_view {prefix_upper}_RELEASE = "{git_info["git_release"]}";
	static constexpr std::string_view {prefix_upper}_COMMIT_HASH = "{git_info["git_hash"]}";
	static constexpr const uint64_t {prefix_upper}_COMMIT_TIMESTAMP = {git_info["git_timestamp"]}ull;
}}
"""
    return write_if_changed(args.output, text)


# --- license-info (ported from build/license_info.py) ---


def get_license_info(src_copyright):
    class LicenseReader:
        def __init__(self, license_file):
            self._license_file = license_file
            self.line_num = 0
            self.current = self.next_line()

        def next_line(self):
            line = self._license_file.readline()
            self.line_num += 1
            while line.startswith("#"):
                line = self._license_file.readline()
                self.line_num += 1
            self.current = line
            return line

        def next_tag(self):
            if ":" not in self.current:
                return ("", [])
            tag, line = self.current.split(":", 1)
            lines = [line.strip()]
            while self.next_line() and self.current.startswith(" "):
                lines.append(self.current.strip())
            return (tag, lines)

    projects = OrderedDict()
    license_list = []

    with open(src_copyright, "r", encoding="utf-8") as copyright_file:
        reader = LicenseReader(copyright_file)
        part = {}
        while reader.current:
            tag, content = reader.next_tag()
            if tag in ("Files", "Copyright", "License"):
                part[tag] = content[:]
            elif tag == "Comment" and part:
                # attach non-empty part to named project
                projects[content[0]] = projects.get(content[0], []) + [part]

            if not tag or not reader.current:
                # end of a paragraph start a new part
                if "License" in part and "Files" not in part:
                    # no Files tag in this one, so assume standalone license
                    license_list.append(part["License"])
                part = {}
                reader.next_line()

    data_list: list = []
    for project in iter(projects.values()):
        for part in project:
            part["file_index"] = len(data_list)
            data_list += part["Files"]
            part["copyright_index"] = len(data_list)
            data_list += part["Copyright"]

    return {"data": data_list, "projects": projects, "parts": part, "licenses": license_list}


def generate_license_info(args) -> bool:
    name_prefix = args.prefix
    prefix_upper = name_prefix.upper()
    prefix_capital = name_prefix.capitalize()

    license_text_name = f"{prefix_upper}_LICENSE_TEXT"
    component_copyright_part_name = f"{prefix_capital}ComponentCopyrightPart"
    component_copyright_name = f"{prefix_capital}ComponentCopyright"
    copyright_data_name = f"{prefix_upper}_COPYRIGHT_DATA"
    copyright_parts_name = f"{prefix_upper}_COPYRIGHT_PARTS"
    copyright_info_name = f"{prefix_upper}_COPYRIGHT_INFO"
    license_name = f"{prefix_capital}License"
    licenses_name = f"{prefix_upper}_LICENSES"

    src_copyright = get_license_info(args.copyright)

    with open(args.license, "r", encoding="utf-8") as file:
        license_text = file.read()

    def copyright_data_str() -> str:
        result = ""
        for line in src_copyright["data"]:
            result += f'\t\t"{line}",\n'
        return result

    part_indexes = {}

    def copyright_part_str() -> str:
        part_index = 0
        result = ""
        for project_name, project in iter(src_copyright["projects"].items()):
            part_indexes[project_name] = part_index
            for part in project:
                result += (
                    f'\t\t{{ "{to_escaped_cstring(part["License"][0])}", '
                    + f"{{ &{copyright_data_name}[{part['file_index']}], {len(part['Files'])} }}, "
                    + f"{{ &{copyright_data_name}[{part['copyright_index']}], {len(part['Copyright'])} }} }},\n"
                )
                part_index += 1
        return result

    def copyright_info_str() -> str:
        result = ""
        for project_name, project in iter(src_copyright["projects"].items()):
            result += (
                f'\t\t{{ "{to_escaped_cstring(project_name)}", '
                + f"{{ &{copyright_parts_name}[{part_indexes[project_name]}], {len(project)} }} }},\n"
            )
        return result

    def license_list_str() -> str:
        result = ""
        for license in iter(src_copyright["licenses"]):
            result += (
                f'\t\t{{ "{to_escaped_cstring(license[0])}",'
                + f'\n\t\t  {to_raw_cstring([line if line != "." else "" for line in license[1:]])} }}, \n'
            )
        return result

    text = "/* THIS FILE IS GENERATED. EDITS WILL BE LOST. */\n\n"
    text += f"""\
#pragma once

#include <array>
#include <span>
#include <string_view>

namespace OpenVic {{
	static constexpr std::string_view {license_text_name} = {{
		{to_raw_cstring(license_text)}
	}};

	struct {component_copyright_part_name} {{
		std::string_view license;
		std::span<const std::string_view> files;
		std::span<const std::string_view> copyright_statements;
	}};

	struct {component_copyright_name} {{
		std::string_view name;
		std::span<const {component_copyright_part_name}> parts;
	}};

	static constexpr std::array {copyright_data_name} = std::to_array<std::string_view>({{
{copyright_data_str()}\t}});

	static constexpr std::array {copyright_parts_name} = std::to_array<{component_copyright_part_name}>({{
{copyright_part_str()}\t}});

	static constexpr std::array {copyright_info_name} = std::to_array<{component_copyright_name}>({{
{copyright_info_str()}\t}});

	struct {license_name} {{
		std::string_view license_name;
		std::string_view license_body;
	}};

	static constexpr std::array {licenses_name} = std::to_array<{license_name}>({{
{license_list_str()}\t}});
}}
"""
    return write_if_changed(args.output, text)


# --- author-info (ported from build/author_info.py) ---


def generate_author_info(args) -> bool:
    prefix_upper = args.prefix.upper()
    sections = OrderedDict()
    for section in args.sections or ["Developers=AUTHORS_DEVELOPERS"]:
        heading, _, macro = section.partition("=")
        sections[heading] = macro

    with open(args.authors, "rb") as file:
        buffer = file.read()

    reading = False
    lines_out = []

    text = "/* THIS FILE IS GENERATED. EDITS WILL BE LOST. */\n\n"
    text += """\
#pragma once

#include <array>
#include <string_view>

namespace OpenVic {
"""

    def close_section():
        lines_out.append("\t});\n")

    for line in buffer.decode().splitlines():
        if line.startswith("    ") and reading:
            lines_out.append(f'\t\t"{to_escaped_cstring(line).strip()}",\n')
        elif line.startswith("## "):
            if reading:
                close_section()
                lines_out.append("\n")
                reading = False
            section = sections.get(line[3:].strip(), None)
            if section:
                lines_out.append(
                    f"\tstatic constexpr std::array {prefix_upper}_{section} = std::to_array<std::string_view>({{\n"
                )
                reading = True

    if reading:
        close_section()

    text += "".join(lines_out)
    text += "}"
    return write_if_changed(args.output, text)


# --- memory-config / memory-node-sizes (ported from openvic-simulation deps/methods.py) ---


def generate_memory_config(args) -> bool:
    header = []

    header.append("// THIS FILE IS GENERATED. EDITS WILL BE LOST.")
    header.append("")

    header += """
// Copyright (C) 2015-2025 Jonathan Müller and foonathan/memory contributors
// SPDX-License-Identifier: Zlib

#ifndef FOONATHAN_MEMORY_IMPL_IN_CONFIG_HPP
#error "do not include this file directly, use config.hpp"
#endif

#include <cstddef>

//=== options ===//
// clang-format off
""".split("\n")

    for define in args.defines:
        key, _, val = define.partition("=")
        header.append(f"#define {key} {val}")

    header.append("// clang-format on")
    header.append("")

    return write_if_changed(args.output, "\n".join(header), platform_newlines=True)


def generate_memory_node_sizes(args) -> bool:
    header = []

    header.append("// THIS FILE IS GENERATED. EDITS WILL BE LOST.")
    header.append("")

    header += """
namespace detail
{
    // A probe type with sizeof == alignof == Alignment by construction, for
    // any power-of-two alignment. Fundamental types can't do this portably:
    // e.g. MinGW x64 (LLP64) has no align-8 type among long/long double.
    template <std::size_t Alignment>
    struct alignas(Alignment) alignment_probe
    {
    };

    template <std::size_t Alignment>
    struct alignment_type
    {
        using type = alignment_probe<Alignment>;
        static_assert(sizeof(type) == Alignment);
        static_assert(alignof(type) == Alignment);
    };

    template <std::size_t Alignment>
    using alignment_type_t = alignment_type<Alignment>::type;

    template <typename InitialType, typename T, bool SubtractTSize = true>
    static consteval std::size_t calculate_node_size_by_type()
    {
        static_assert(!std::is_same<InitialType, T>::value && (sizeof(InitialType) != sizeof(T)));
        static_assert(sizeof(T) > sizeof(InitialType));

        return sizeof(T) - (SubtractTSize ? sizeof(InitialType) : 0);
    }

    template <std::size_t Alignment, typename T, bool SubtractTSize = true>
    static consteval std::size_t calculate_node_size()
    {
        return calculate_node_size_by_type<alignment_type_t<Alignment>, T, SubtractTSize>();
    }

    template <std::size_t Alignment>
    using allocator_type = std::allocator<alignment_type_t<Alignment>>;
}
""".split("\n")

    containers = {
        "forward_list": [
            "calculate_node_size<Alignment, std::__1::__forward_list_node<alignment_type_t<Alignment>, void*>>()",
            "calculate_node_size<Alignment, std::_Fwd_list_node<alignment_type_t<Alignment>>>()",
            "calculate_node_size<Alignment, std::_Flist_node<alignment_type_t<Alignment>, void*>>()",
        ],
        "list": [
            "calculate_node_size<Alignment, std::__1::__list_node<alignment_type_t<Alignment>, void*>>()",
            "calculate_node_size<Alignment, std::_List_node<alignment_type_t<Alignment>>>()",
            "calculate_node_size<Alignment, std::_List_node<alignment_type_t<Alignment>, void*>>()",
        ],
        "set": [
            "calculate_node_size<Alignment, std::__1::__tree_node<alignment_type_t<Alignment>, void*>>()",
            "calculate_node_size<Alignment, std::_Rb_tree_node<alignment_type_t<Alignment>>>()",
            "calculate_node_size<Alignment, std::_Tree_node<alignment_type_t<Alignment>, void*>>()",
        ],
        "multiset": [],
        "unordered_set": [
            "calculate_node_size<Alignment, std::__1::__hash_node<alignment_type_t<Alignment>, void*>>()",
            "calculate_node_size<Alignment, typename std::__detail::_Hash_node<alignment_type_t<Alignment>, true>>()",
            "calculate_node_size<Alignment, std::_List_node<alignment_type_t<Alignment>, void*>>()",
        ],
        "unordered_multiset": [],
        "map": [
            """
calculate_node_size_by_type<
    std::__1::pair<const alignment_type_t<Alignment>, alignment_type_t<Alignment>>,
    std::__1::__tree_node<
        std::__1::__value_type<alignment_type_t<Alignment>, alignment_type_t<Alignment>>,
        void*>>()
""",
            """
calculate_node_size_by_type<
    std::pair<const alignment_type_t<Alignment>, alignment_type_t<Alignment>>,
    std::_Rb_tree_node<
        std::pair<const alignment_type_t<Alignment>, alignment_type_t<Alignment>>>>()
""",
            """
calculate_node_size_by_type<
    std::pair<const alignment_type_t<Alignment>, alignment_type_t<Alignment>>,
    std::_Tree_node<
        std::pair<const alignment_type_t<Alignment>, alignment_type_t<Alignment>>,
        void*>>()
""",
        ],
        "multimap": [],
        "unordered_map": [
            """
calculate_node_size_by_type<
    std::__1::pair<const alignment_type_t<Alignment>, alignment_type_t<Alignment>>,
    std::__1::__hash_node<std::__1::__hash_value_type<alignment_type_t<Alignment>,
                                                    alignment_type_t<Alignment>>,
                        void*>>()
""",
            """
calculate_node_size_by_type<
    std::pair<const alignment_type_t<Alignment>, alignment_type_t<Alignment>>,
    std::__detail::_Hash_node<
        std::pair<const alignment_type_t<Alignment>, alignment_type_t<Alignment>>,
        true>>()
""",
            """
calculate_node_size_by_type<
    std::pair<const alignment_type_t<Alignment>, alignment_type_t<Alignment>>,
    std::_List_node<
        std::pair<const alignment_type_t<Alignment>, alignment_type_t<Alignment>>,
        void*>>()
""",
        ],
        "unordered_multimap": [],
        "shared_ptr_stateless": [
            """
calculate_node_size<Alignment,
    std::__1::__shared_ptr_emplace<
        alignment_type_t<Alignment>,
        std::allocator<alignment_type_t<Alignment>>>,
    false>()
""",
            """
calculate_node_size<Alignment,
    std::_Sp_counted_ptr_inplace<alignment_type_t<Alignment>,
                                std::allocator<alignment_type_t<Alignment>>,
                                __gnu_cxx::_S_atomic>,
    false>()
""",
            """
calculate_node_size<
    Alignment,
    std::_Ref_count_obj_alloc3<std::remove_cv_t<alignment_type_t<Alignment>>,
                                allocator_type<Alignment>>,
    false>()
""",
        ],
        "shared_ptr_stateful": [
            """
calculate_node_size<Alignment,
    std::__1::__shared_ptr_emplace<
        alignment_type_t<Alignment>,
        std::pmr::polymorphic_allocator<alignment_type_t<Alignment>>>,
    false>()
""",
            """
calculate_node_size<Alignment,
    std::_Sp_counted_ptr_inplace<
        alignment_type_t<Alignment>,
        std::pmr::polymorphic_allocator<alignment_type_t<Alignment>>,
        __gnu_cxx::_S_atomic>,
    false>()
""",
            """
calculate_node_size<Alignment,
    std::_Ref_count_obj_alloc3<
        std::remove_cv_t<alignment_type_t<Alignment>>,
        std::pmr::polymorphic_allocator<alignment_type_t<Alignment>>>,
    false>()
""",
        ],
    }

    container_names = list(containers.keys())
    for i, container_name in enumerate(container_names):
        data = containers[container_name]
        if len(data) == 0:
            data = containers[container_names[i - 1]]

        header += f"""namespace detail
{{
#ifdef _LIBCPP_VERSION
    template <std::size_t Alignment>
    struct {container_name}_node_size
    : std::integral_constant<
          std::size_t,{data[0]}>
    {{
    }};
#elif defined(__GLIBCXX__)
    template <std::size_t Alignment>
    struct {container_name}_node_size
    : std::integral_constant<
          std::size_t,{data[1]}>
    {{
    }};
#elif defined(_MSC_VER)
    template <std::size_t Alignment>
    struct {container_name}_node_size
    : std::integral_constant<
          std::size_t,{data[2]}>
    {{
    }};
#else
    template <std::size_t Alignment>
    struct {container_name}_node_size
    : std::integral_constant<
          std::size_t,0>
    {{
        static_assert(Alignment == Alignment, "{container_name}_node_size not supported.");
    }};
#endif
}}

template <typename T>
struct {container_name}_node_size
: std::integral_constant<std::size_t,
    detail::round_up_to_multiple_of_alignment(detail::{container_name}_node_size<alignof(T)>::value + sizeof(T), alignof(void*))>
{{}};
""".split("\n")

    return write_if_changed(args.output, "\n".join(header), platform_newlines=True)


# --- CLI ---


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    subparsers = parser.add_subparsers(dest="command", required=True)

    p = subparsers.add_parser("commit-info", help="Generate commit_info.gen.hpp")
    p.add_argument("--prefix", required=True, help="Macro name prefix, e.g. game or sim")
    p.add_argument("--repo-dir", required=True, help="Repository root to read git metadata from")
    p.add_argument("-o", "--output", required=True)
    p.set_defaults(func=generate_commit_info)

    p = subparsers.add_parser("license-info", help="Generate license_info.gen.hpp")
    p.add_argument("--prefix", required=True)
    p.add_argument("--copyright", required=True, help="Debian-style COPYRIGHT file")
    p.add_argument("--license", required=True, help="LICENSE.md file")
    p.add_argument("-o", "--output", required=True)
    p.set_defaults(func=generate_license_info)

    p = subparsers.add_parser("author-info", help="Generate author_info.gen.hpp")
    p.add_argument("--prefix", required=True)
    p.add_argument("--authors", required=True, help="AUTHORS.md file")
    p.add_argument(
        "--section",
        dest="sections",
        action="append",
        metavar="HEADING=MACRO",
        help="Markdown section to macro suffix mapping, in order (repeatable)",
    )
    p.add_argument("-o", "--output", required=True)
    p.set_defaults(func=generate_author_info)

    p = subparsers.add_parser("memory-config", help="Generate foonathan/memory config_impl.hpp")
    p.add_argument(
        "--define",
        dest="defines",
        action="append",
        required=True,
        metavar="KEY=VALUE",
        help="Config define (repeatable)",
    )
    p.add_argument("-o", "--output", required=True)
    p.set_defaults(func=generate_memory_config)

    p = subparsers.add_parser("memory-node-sizes", help="Generate foonathan/memory container_node_sizes_impl.hpp")
    p.add_argument("-o", "--output", required=True)
    p.set_defaults(func=generate_memory_node_sizes)

    args = parser.parse_args()
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
