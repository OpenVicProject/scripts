from collections import OrderedDict
from io import TextIOWrapper


def get_license_info(src_copyright):
    class LicenseReader:
        def __init__(self, license_file: TextIOWrapper):
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


def license_builder(target, source, env):
    name_prefix = env.get("name_prefix", "project")
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

    src_copyright = get_license_info(str(source[0]))
    src_license = str(source[1])

    with open(src_license, "r", encoding="utf-8") as file:
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
                    f'\t\t{{ "{env.to_escaped_cstring(part["License"][0])}", '
                    + f"{{ &{copyright_data_name}[{part['file_index']}], {len(part['Files'])} }}, "
                    + f"{{ &{copyright_data_name}[{part['copyright_index']}], {len(part['Copyright'])} }} }},\n"
                )
                part_index += 1
        return result

    def copyright_info_str() -> str:
        result = ""
        for project_name, project in iter(src_copyright["projects"].items()):
            result += (
                f'\t\t{{ "{env.to_escaped_cstring(project_name)}", '
                + f"{{ &{copyright_parts_name}[{part_indexes[project_name]}], {len(project)} }} }},\n"
            )
        return result

    def license_list_str() -> str:
        result = ""
        for license in iter(src_copyright["licenses"]):
            result += (
                f'\t\t{{ "{env.to_escaped_cstring(license[0])}",'
                + f'\n\t\t  {env.to_raw_cstring([line if line != "." else "" for line in license[1:]])} }}, \n'
            )
        return result

    with open(str(target[0]), "wt", encoding="utf-8", newline="\n") as file:
        file.write("/* THIS FILE IS GENERATED. EDITS WILL BE LOST. */\n\n")
        file.write(
            f"""\
#pragma once

#include <array>
#include <span>
#include <string_view>

namespace OpenVic {{
	static constexpr std::string_view {license_text_name} = {{
		{env.to_raw_cstring(license_text)}
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
        )
