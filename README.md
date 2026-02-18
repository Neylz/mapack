# Mapack (Minecraft Map Packer)

Config-driven CLI tool to build and export Minecraft map artifacts from a JSON/JSONC config file.

## Usage

```bash
mapack <config.jsonc>
```

## Documentation

To Be Written. (Soon™)


## Roadmap

(In no particular order, and subject to change)

- [ ] Add better error handling and reporting, especially for missing files
- [ ] Indicate in logs what export/pipeline is being executed (instead of just the artifact name)
- [ ] Add a "validate" command to check config files without building artifacts
- [ ] Json Schema for config validation
- [ ] Add support for more artifact types and transforms
    - [ ] Execute a python script as a transform
    - [ ] Reimplement the v1 features
    - [ ] Check dimensions validation/removal 
    - [ ] Reimplement the v1 features
- [ ] Add a way to select only a file, a list of files, or a subdirectory to export into the output artifact instead of the whole artifact workdir
- [ ] Publish artifacts
    - [ ] GWorkspace
    - [ ] Atlas
    - [ ] PMC
- [ ] CI/CD
- [ ] Plugins!
- [ ] 
