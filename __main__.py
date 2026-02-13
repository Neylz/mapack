#!/usr/bin/env python3
from typing import Optional

import logging
import os
import shutil
import subprocess
import sys
import zipfile
from tempfile import TemporaryDirectory

import click
import nbtlib
from nbtlib import String


logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("mappacker")

# --- MAP ---
def rename_map(level_dat_path: str, name: str):
    logger.info("rename_map: %s -> %s", level_dat_path, name)
    try:
        with nbtlib.load(level_dat_path) as f:
            f["Data"]["LevelName"] = String(name)

    except Exception as e:
        logger.warning("Failed to rename map in level.dat: %s", e)


def remove_dotgit(root_dir: str) -> None:
    logger.info("remove_dotgit: %s", root_dir)
    for dirpath, dirnames, _ in os.walk(root_dir):
        if ".git" in dirnames:
            git_path = os.path.join(dirpath, ".git")
            shutil.rmtree(git_path, ignore_errors=True)
            dirnames.remove(".git")


def remove_zero_byte_files(root_dir: str) -> None:
    logger.info("remove_zero_byte_files: %s", root_dir)
    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            try:
                if os.path.getsize(file_path) == 0:
                    os.remove(file_path)
            except OSError:
                continue


def remove_dimensions(root_dir: str, remove_nether: bool, remove_end: bool) -> None:
    logger.info("remove_dimensions: %s (nether=%s, end=%s)", root_dir, remove_nether, remove_end)
    paths_to_remove = []
    if remove_nether:
        paths_to_remove.extend(
            [
                os.path.join(root_dir, "DIM-1"),                                    # legacy folder
                os.path.join(root_dir, "dimensions", "minecraft", "the_nether"),    # 26.0+
            ]
        )
    if remove_end:
        paths_to_remove.extend(
            [
                os.path.join(root_dir, "DIM1"),                                     # legacy folder
                os.path.join(root_dir, "dimensions", "minecraft", "the_end"),       # 26.0+
            ]
        )

    for path in paths_to_remove:
        if os.path.isdir(path):
            shutil.rmtree(path, ignore_errors=True)


def copy_map_icon(workdir: str, map_icon: Optional[str]) -> None:
    logger.info("copy_map_icon: %s", workdir)
    if not map_icon:
        return
    shutil.copyfile(map_icon, os.path.join(workdir, "icon.png"))


def copy_resources(workdir: str, resources_cpy: Optional[str]) -> None:
    logger.info("copy_resources: %s", workdir)
    if not resources_cpy:
        return

    resources_zip = os.path.join(workdir, "resources.zip")
    if os.path.isdir(resources_cpy):
        shutil.make_archive(os.path.splitext(resources_zip)[0], "zip", resources_cpy)
    elif zipfile.is_zipfile(resources_cpy):
        shutil.copyfile(resources_cpy, resources_zip)

def remove_playerdata(root_dir: str) -> None:
    logger.info("remove_playerdata: %s", root_dir)
    paths_to_remove = [
        # legacy playerdata folders
        os.path.join(root_dir, "playerdata"),
        os.path.join(root_dir, "stats"),
        os.path.join(root_dir, "advancements"),

        # 26.0+ folder
        os.path.join(root_dir, "players")
    ]
    for path in paths_to_remove:
        if os.path.isdir(path):
            shutil.rmtree(path, ignore_errors=True)

def process_datapacks(
    map_dir: str,
    rm_dotgit: bool,
    zip_datapacks: Optional[bool],
):
    logger.info("process_datapacks: %s (rm_dotgit=%s, zip_datapacks=%s)", map_dir, rm_dotgit, zip_datapacks)
    """Zip or unzip datapacks in the map, and optionally remove .git folders inside them.
    
    zip_datapacks: Optional[bool]
        - None: skip this step, leave datapacks as they are (default)
        - True: zip all folders in datapacks/, and remove the original folders
        - False: unzip all zip files in datapacks/, and remove the original zip files
    """
    
    dp_dir = os.path.join(map_dir, "datapacks")
    if not os.path.isdir(dp_dir):
        return
    if zip_datapacks is None:
        return

    for entry in os.listdir(dp_dir):
        entry_path = os.path.join(dp_dir, entry)
        if os.path.isdir(entry_path):
            if rm_dotgit:
                remove_dotgit(entry_path)
            if zip_datapacks is True:
                shutil.make_archive(
                    os.path.splitext(entry_path)[0],
                    "zip",
                    entry_path,
                )
                shutil.rmtree(entry_path)
        elif zipfile.is_zipfile(entry_path):
            if zip_datapacks is False:
                with zipfile.ZipFile(entry_path, 'r') as zip_ref:
                    extract_path = os.path.splitext(entry_path)[0]
                    zip_ref.extractall(extract_path)
                os.remove(entry_path)
                if rm_dotgit:
                    remove_dotgit(extract_path)





# --- TARGETS ---
def pack(
    target_name: str,  # 'default', 'realms', ...

    source_map: str, output_dir: str,

    map_name: Optional[str] = None,
    map_version: Optional[str] = None,
    map_icon: Optional[str] = None,

    resources_cpy: Optional[str] = None,    # copy or not a resources zip as resrources.zip, None to skip

    # features
    f_rm_dim_nether=True,
    f_rm_dim_end=True,
    f_rm_0b=True,
    f_rm_dotgit=True,
    f_rm_playerdata=True,
    f_zip_datapacks: Optional[bool] = True, # None = skip, True = zip, False = unzip
):
    logger.info("pack: target=%s map=%s output=%s", target_name, source_map, output_dir)
    target_prefix = (
        f"{target_name.capitalize()} - "
        if target_name and target_name.casefold() not in ["default"]
        else ""
    )
    output_name = f"{target_prefix}{map_name or 'map'} {map_version or ''}".strip()

    with TemporaryDirectory() as workdir:
        # cpy source
        shutil.copytree(source_map, workdir, dirs_exist_ok=True)

        if map_name:
            rename_map(os.path.join(workdir, "level.dat"), map_name)


        # datapacks
        process_datapacks(
            map_dir=workdir,
            rm_dotgit=f_rm_dotgit,
            zip_datapacks=f_zip_datapacks,
        )

        # optional transforms
        if f_rm_dim_nether or f_rm_dim_end:
            remove_dimensions(workdir, f_rm_dim_nether, f_rm_dim_end)
        if f_rm_0b:
            remove_zero_byte_files(workdir)
        if f_rm_dotgit:
            remove_dotgit(workdir)
            if f_rm_playerdata:
                remove_playerdata(workdir)

        # map icon and resources
        copy_map_icon(workdir, map_icon)
        copy_resources(workdir, resources_cpy)



        # create zip
        shutil.make_archive(
            os.path.join(output_dir, output_name),
            'zip',
            workdir
        )





# --- CLI ---
@click.command()
@click.argument('map_dir', type=click.Path(exists=True))
@click.argument('output_dir', type=click.Path(), default="output")

@click.option('--preset', '-p', type=str, default=None, help='(None) Use a preset configuration. May override other options. Available presets: ["realms"].')

@click.option('--target', type=str, default="default", help='("default") Set target to build. Renames output files.')

@click.option('--map-name', '-n', type=str, default=None, help='(None) Name of the map.')
@click.option('--map-version', '-v', type=str, default=None, help='(None) Version of the map.')
@click.option('--map-icon', '-i', type=click.Path(exists=True), default=None, help='(None) Path to custom icon.png file for the map. Overrides existing one if present.')

@click.option('--resources-dir', '-rp', default=None, type=click.Path(exists=True), help='(None) Path to resource pack directory.')
@click.option('--resources-git', '-rpg', type=str, default=None, help='(None) Git repository URL for resource pack. -rp has priority.')
@click.option('--resources-pckg', is_flag=True, help='Pack resources (will try to use scripts/pack.py).')

@click.option('--feature-rm-dim-nether', 'f_rm_dim_nether', type=bool, default=True, help='(True) Remove the nether dimension.')
@click.option('--feature-rm-dim-end', 'f_rm_dim_end', type=bool, default=True, help='(True) Remove the end dimension.')
@click.option('--feature-rm-0b', 'f_rm_0b', type=bool, default=True, help='(True) Remove all 0-byte files from the map.')
@click.option('--feature-rm-dotgit', 'f_rm_dotgit', type=bool, default=True, help='(True) Remove all .git directories from the map & resource pack.')
@click.option('--feature-rm-playerdata', 'f_rm_playerdata', type=bool, default=True, help='(True) Remove playerdata/ folder from the map.')
@click.option('--feature-zip-datapacks', 'f_zip_datapacks', type=bool, default=True, help='(True) Zip (True) or unzip (False) all datapacks in the map. If None, this step will be skipped (--feature-rm-dotgit will be ignored on zipped DPs).')

@click.option('--publish-google-drive', type=bool, default=False, help='(False) Publish the map to Google Drive.')
@click.option('--publish-pmc', type=bool, default=False, help='(False) Publish the map to Planet Minecraft.')
@click.option('--publish-mapverse', type=bool, default=False, help='(False) Publish the map to Mapverse.')
@click.option('--publish-atlas', type=bool, default=False, help='(False) Publish the map to Realms\' Atlas.')
@click.option('--publish-minecraftmaps', type=bool, default=False, help='(False) Publish the map to minecraftmaps.com.')
def cli(
    map_dir,
    output_dir,

    preset=None,
    target="default",

    map_name=None,
    map_version=None,
    map_icon=None,

    resources_dir=None,
    resources_git=None,
    resources_pckg=False,

    f_rm_dim_nether=True,
    f_rm_dim_end=True,
    f_rm_0b=True,
    f_rm_dotgit=True,
    f_rm_playerdata=True,
    f_zip_datapacks=None,

    publish_google_drive=False,
    publish_pmc=False,
    publish_mapverse=False,
    publish_atlas=False,
    publish_minecraftmaps=False
):
    logger.info("cli: start")
    if preset is not None:
        click.echo(f"Using preset: {preset}")
        match preset.lower():
            case "realms":
                target = "realms"
                f_rm_0b = True
                f_rm_dotgit = True
                f_zip_datapacks = False
            case _:
                click.echo(f"Error: Unknown preset '{preset}'.\nExiting.")
                return
    

    try:
        map_dir = os.path.abspath(map_dir)
    except Exception as e:
        click.echo(f"Error: Invalid map directory path: {e}")
        return

    # create output dir if not exists
    output_dir = os.path.abspath(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    resources_source = os.path.abspath(resources_dir) if resources_dir else None
    with TemporaryDirectory() as workdir_rp:
        if not resources_source and resources_git:
            if not shutil.which("git"):
                click.echo("Error: 'git' is required to use --resources-git.")
                return
            try:
                subprocess.run(
                    ["git", "clone", resources_git, workdir_rp],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                resources_source = os.path.abspath(workdir_rp)
            except subprocess.CalledProcessError as e:
                click.echo(f"Error: Failed to clone resource pack: {e}")
                return

        if resources_source and resources_pckg:
            pack_candidates = [
                os.path.join(resources_source, "scripts", "pack.py"),
                os.path.join(resources_source, "pack.py"),
            ]
            pack_script = next((p for p in pack_candidates if os.path.isfile(p)), None)
            if pack_script:
                try:
                    subprocess.run(
                        [sys.executable, os.path.abspath(pack_script)],
                        cwd=resources_source,
                        check=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                except subprocess.CalledProcessError as e:
                    click.echo(f"Error: Resource pack script failed: {e}")
                    return
            packed_zip = os.path.join(resources_source, "resources.zip")
            if os.path.isfile(packed_zip):
                resources_source = packed_zip


    # cpy map to work dir
    pack(
        target_name=target,
        source_map=map_dir,
        output_dir=output_dir,
        map_name=map_name,
        map_version=map_version,
        map_icon=map_icon,
        resources_cpy=resources_source,
        f_rm_dim_nether=f_rm_dim_nether,
        f_rm_dim_end=f_rm_dim_end,
        f_rm_0b=f_rm_0b,
        f_rm_dotgit=f_rm_dotgit,
        f_rm_playerdata=f_rm_playerdata,
        f_zip_datapacks=f_zip_datapacks,
    )



    




if __name__ == "__main__":
    cli()