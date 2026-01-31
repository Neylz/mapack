#!/usr/bin/env python3
from typing import Optional

import os
import shutil
import zipfile
from tempfile import TemporaryDirectory

import click

# --- MAP ---
def process_datapacks(
    map_dir: str,
    keep_dotgit: bool,
    zip_datapacks: Optional[bool],
):
    dp_dir = os.path.join(map_dir, "datapacks")
    if not os.path.isdir(dp_dir):
        return

    for entry in os.listdir(dp_dir):
        entry_path = os.path.join(dp_dir, entry)
        if os.path.isdir(entry_path):
            # unzip datapack
            if zip_datapacks is True:
                shutil.make_archive(
                    os.path.splitext(entry_path)[0],
                    'zip',
                    entry_path
                )
                shutil.rmtree(entry_path)
        elif zipfile.is_zipfile(entry_path):
            # unzip datapack
            if zip_datapacks is False:
                with zipfile.ZipFile(entry_path, 'r') as zip_ref:
                    extract_path = os.path.splitext(entry_path)[0]
                    zip_ref.extractall(extract_path)
                os.remove(entry_path)



# --- RESOURCES ---




# --- TARGETS ---
def pack(
    target_name: str,  # 'default', 'realms', ...

    source_map: str, output_dir: str,

    map_name: Optional[str] = None,
    map_version: Optional[str] = None,
    map_icon: Optional[str] = None,

    resources_cpy: Optional[str] = None,    # copy or not a resources zip as resrources.zip, None to skip

    # features
    keep_dim_nether=False,
    keep_dim_end=False,
    keep_0b=False,
    keep_git_dirs=False,
    zip_datapacks: Optional[bool] = False, # None = skip, True = zip, False = unzip
):
    output_name = f"{
            target_name.capitalize() if target_name.casefold() not in [None, "default"] else ''
        }{map_name or 'map'} {map_version or ''}"

    with TemporaryDirectory() as workdir:
        # cpy source
        shutil.copytree(source_map, workdir, dirs_exist_ok=True)


        # unzip datapacks
        process_datapacks(
            map_dir=workdir,
            keep_git_dirs=keep_git_dirs,
            zip_datapacks=zip_datapacks,
            unzip_datapacks=not zip_datapacks,
        )



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
@click.option('--map-name', '-n', type=str, help='Name of the map.', default=None)
@click.option('--map-version', '-v', type=str, help='Version of the map.', default=None)
@click.option('--map-icon', '-i', type=click.Path(exists=True), help='Path to custom icon.png file for the map. Overrides existing one if present.', default=None)
@click.option('--resources-dir', '-rp', type=click.Path(exists=True), help='Path to resource pack directory.', default=None)
@click.option('--resources-git', '-rpg', type=str, prompt="dd", help='Git repository URL for resource pack. -rp has priority.', default=None)
@click.option('--resources-pack', '-rpg', is_flag=True, help='Pack resources (use scripts/pack.py).')
@click.option('--no-target-default', is_flag=True, help='Does not compile to a default Minecraft map.')
@click.option('--target-default', is_flag=True, help='Pack as a Minecraft map. (default behavior unless --no-target-default is set)')
@click.option('--target-realms', is_flag=True, help='Pack as a Minecraft Realms map.')
@click.option('--keep-dim-nether', is_flag=True, help='Keep the nether dimension.')
@click.option('--keep-dim-end', is_flag=True, help='Keep the end dimension.')
@click.option('--keep-0b', is_flag=True, help='Keep 0 bit files.')
@click.option('--publish-google-drive', is_flag=True, help='Publish the map to Google Drive.')
@click.option('--publish-pmc', is_flag=True, help='Publish the map to Planet Minecraft.')
@click.option('--publish-mapverse', is_flag=True, help='Publish the map to Mapverse.')
@click.option('--publish-atlas', is_flag=True, help='Publish the map to Realms\' Atlas.')
@click.option('--publish-minecraftmaps', is_flag=True, help='Publish the map to minecraftmaps.com.')
def cli(
    map_dir,
    output_dir,

    map_name=None,
    map_version=None,
    map_icon=None,

    resources_dir=None, resources_git=None,
    resources_pack=False,

    no_target_default=False,
    target_default=False,
    target_realms=False,

    keep_dim_nether=False,
    keep_dim_end=False,
    keep_0b=False,

    publish_google_drive=False,
    publish_pmc=False,
    publish_mapverse=False,
    publish_atlas=False,
    publish_minecraftmaps=False
):
    try:
        map_dir = os.path.abspath(map_dir)
    except Exception as e:
        click.echo(f"Error: Invalid map directory path: {e}")
        return

    # create output dir if not exists
    output_dir = os.path.abspath(output_dir)
    os.makedirs(output_dir, exist_ok=True)


    with TemporaryDirectory() as workdir_rp:
        # compile resource pack
        pass


    # == default target ==
    if not no_target_default:
            # cpy map to work dir
        pack(
            target_name="default",
            source_map=map_dir,
            output_dir=output_dir,
            map_name=map_name,
            map_version=map_version,
            map_icon=map_icon,
            resources_cpy=resources_dir,
            keep_dim_nether=keep_dim_nether,
            keep_dim_end=keep_dim_end,
            keep_0b=keep_0b,
            keep_git_dirs=False,
            zip_datapacks=False,
        )



    




if __name__ == "__main__":
    cli()