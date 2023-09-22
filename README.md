# OpenVicProject/scripts
Common Scons scripts repo for the [OpenVicProject repos](https://github.com/OpenVicProject)

## Required
* [scons](https://scons.org/)

## Usage
1. Call `env.SetupOptions()` and use the return value to add your options:
    ```py
    opts = env.SetupOptions()
    opts.Add(BoolVariable("example", "Is an example", false))
    ```
2. When options are finished call `env.FinalizeOptions()` then setup your scons script using env.
