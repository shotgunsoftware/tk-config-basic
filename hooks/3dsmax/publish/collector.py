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

class MaxSceneCollector(HookBaseClass):
    """
    Collector that operates on the max scene
    """

    def process_current_scene(self, parent_item):
        """
        Analyzes the current scene open in a DCC and parents a subtree of items
        under the parent_item passed in.

        :param parent_item: Root item instance
        """
        item = self.create_current_3dsmax_scene(parent_item)
        return item

    def process_file(self, parent_item, path):
        """
        Analyzes the given file and creates one or more items
        to represent it. Extends the base processing
        capabilities with a maya file detection which
        determines the maya project.

        :param parent_item: Root item instance
        :param path: Path to analyze
        :returns: The main item that was created
        """

        if path.endswith(".max"):

            # run base class logic to set basic properties for us
            item = super(MaxSceneCollector, self).process_file(parent_item, path)

            item.type = "file.3dsmax"
            item.display_type = "3dsMax File"
            item.set_icon_from_path(os.path.join(self.disk_location, "icons", "3dsmax.png"))

            folder = os.path.dirname(path)
            if os.path.basename(folder) == "scenes":
                # assume parent level is workspace root
                item.properties["project_root"] = os.path.dirname(folder)
            else:
                item.properties["project_root"] = None

        else:

            # run base class implementation
            item = super(MaxSceneCollector, self).process_file(parent_item, path)

        return item


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
        current_scene.set_icon_from_path(os.path.join(self.disk_location, "icons", "3dsmax.png"))
        return current_scene

