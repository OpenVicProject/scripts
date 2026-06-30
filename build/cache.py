# Copied from https://github.com/godotengine/godot/blob/77c0879cffe8cb7336fab2b7c18dcad2d9a0176c/methods.py#L815-L861
import atexit
import sys
from typing import cast

def show_progress(env):
    # Ninja has its own progress/tracking tool that clashes with ours.
    if env.get("ninja", False):
        return

    NODE_COUNT_FILENAME = env.Dir("#").srcnode().abspath + "/.scons_node_count"

    class ShowProgress:
        def __init__(self):
            self.count = 0
            self.max = 0
            try:
                with open(NODE_COUNT_FILENAME, "r", encoding="utf-8") as f:
                    self.max = int(f.readline())
            except OSError:
                pass

            # Progress reporting is not available in non-TTY environments since it
            # messes with the output (for example, when writing to a file).
            self.display = cast(bool, env["progress"] and sys.stdout.isatty())
            if self.display and not self.max:
                print("Performing initial build, progress percentage unavailable!")
                self.display = False

        def __call__(self, node, *args, **kw):
            self.count += 1
            if self.display:
                percent = int(min(self.count * 100 / self.max, 100))
                sys.stdout.write(f"\r[{percent:3d}%] ")
                sys.stdout.flush()

    from SCons.Script import Progress
    from SCons.Script.Main import GetBuildFailures

    progressor = ShowProgress()
    Progress(progressor)

    def progress_finish():
        if GetBuildFailures() or not progressor.count:
            return
        try:
            with open(NODE_COUNT_FILENAME, "w", encoding="utf-8", newline="\n") as f:
                f.write(f"{progressor.count}\n")
        except OSError:
            pass

    atexit.register(progress_finish)
