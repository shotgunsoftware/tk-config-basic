# Copyright (c) 2017 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.
import MaxPlus
import sgtk
import os
import re
from pymxs import runtime as mxs_rt

HookBaseClass = sgtk.get_hook_baseclass()

class GenericSceneCollector(HookBaseClass):
    """
    Collector that operates on the maya scene
    """

    def process_current_scene(self, parent_item):
        item = self.create_current_3dsmax_scene(parent_item)
        return item

    def process_file(self, parent_item, path):

        file_name = os.path.basename(path)
        (file_name_no_ext, file_extension) = os.path.splitext(file_name)

        if file_extension in [".jpeg", ".jpg", ".png"]:
            file_item = parent_item.create_item("file.image", "Image File", file_name)
            file_item.set_thumbnail(path)
            file_item.set_icon(os.path.join(self.disk_location, "icons", "image.png"))

        elif file_extension in [".mov", ".mp4"]:
            file_item = parent_item.create_item("file.movie", "Movie File", file_name)
            file_item.set_icon(os.path.join(self.disk_location, "icons", "quicktime.png"))

        elif file_extension in [".max"]:
            file_item = parent_item.create_item("file.3dsmax", "3dsMax File", file_name)
            file_item.set_icon(os.path.join(self.disk_location, "icons", "3dsmax.png"))

            folder = os.path.dirname(path)
            if os.path.basename(folder) == "scenes":
                # assume parent level is workspace root
                file_item.properties["project_root"] = os.path.dirname(folder)
            else:
                file_item.properties["project_root"] = None

        else:
            file_item = parent_item.create_item("file", "Generic File", file_name)
            file_item.set_icon(os.path.join(self.disk_location, "icons", "page.png"))

        file_item.properties["extension"] = file_extension
        file_item.properties["path"] = path
        file_item.properties["filename"] = file_name

        # check if path matches pattern fooo.v123.ext
        version = re.search("(.*)\.v([0-9]+)\.[^\.]+$", file_name)
        if version:
            # strip all leading zeroes
            file_item.properties["prefix"] = version.group(1)
            version_no_leading_zeroes = version.group(2).lstrip("0")
            file_item.properties["version"] = int(version_no_leading_zeroes)
        else:
            file_item.properties["version"] = 0
            file_item.properties["prefix"] = file_name_no_ext

        return file_item

    def create_current_3dsmax_scene(self, parent_item):
        # get the main scene:
        scene_file_name = MaxPlus.FileManager.GetFileName()
        if scene_file_name:
            scene_file_name_and_path = MaxPlus.FileManager.GetFileNameAndPath();
        else:
            scene_file_name = "Untitled Scene"
            scene_file_name_and_path = None

        current_scene = parent_item.create_item("3dsmax.scene", "Current 3dsMax Scene", scene_file_name)
        current_scene.properties["path"] = scene_file_name_and_path
        current_scene.properties["project_root"] = mxs_rt.pathConfig.getCurrentProjectFolder()
        current_scene.set_icon(os.path.join(self.disk_location, "icons", "3dsmax.png"))
        return current_scene

