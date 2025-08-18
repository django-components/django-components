import os
import subprocess
from pathlib import Path
from typing import List, Optional, Sequence, Union

DEFAULT_ESBUILD_ARGS = [
    "--bundle",
    "--minify",
    # "--sourcemap",  # NOTE: Enable for debugging during development
    "--platform=browser",
    "--target=chrome80,firefox73,safari13,edge80",
]


# Compile a list of JS/TS files into a single minified file with esbuild
def compile_js_files_to_file(
    file_paths: Sequence[Union[Path, str]],
    out_file: Union[Path, str],
    esbuild_args: Optional[List[str]] = None,
) -> None:
    # Find Esbuild binary
    bin_name = "esbuild.cmd" if os.name == "nt" else "esbuild"
    esbuild_path = Path.cwd() / "node_modules" / ".bin" / bin_name

    # E.g. `esbuild js_file1.ts js_file2.ts js_file3.ts --bundle --minify --outfile=here.js`
    esbuild_cmd = [
        str(esbuild_path),
        *[str(filepath) for filepath in file_paths],
        *(esbuild_args if esbuild_args is not None else DEFAULT_ESBUILD_ARGS),
        # Compile into a single file
        f"--outfile={out_file}",
    ]

    # check=True should ensure that this raises an error if the subprocess fails.
    subprocess.run(esbuild_cmd, check=True)


# NOTE:
# - This script should be called from within django_components_js` dir!
# - Also you need to have esbuild installed. If not yet, run:
#   `npm install -D esbuild`
def build() -> None:
    entrypoint = "./src/index.ts"
    out_file = Path("../django_components/static/django_components/django_components.min.js")

    # Prepare output dir
    out_file.parent.mkdir(parents=True, exist_ok=True)

    # Compile JS
    compile_js_files_to_file(file_paths=[entrypoint], out_file=out_file)


if __name__ == "__main__":
    build()
