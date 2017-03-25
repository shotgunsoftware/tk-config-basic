# Copyright (c) 2017 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.
import sgtk
import os
import maya.cmds as cmds

HookBaseClass = sgtk.get_hook_baseclass()


class MayaSceneCollector(HookBaseClass):
    """
    Collector that operates on the maya scene
    """

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

        # run base class logic to set basic properties for us
        item = super(MayaSceneCollector, self).process_file(parent_item, path)

        if path.endswith(".ma") or path.endswith(".mb"):

            folder = os.path.dirname(path)
            if os.path.basename(folder) == "scenes":

                # assume parent level is workspace root
                project_root = os.path.dirname(folder)
                item.properties["project_root"] = os.path.dirname(folder)

                # collect associated files
                self.collect_alembic_caches(item, project_root)
                self.collect_playblasts(item, project_root)

        return item

    def process_current_scene(self, parent_item):
        """
        Analyzes the current scene open in a DCC and parents a subtree of items
        under the parent_item passed in.

        :param parent_item: Root item instance
        """
        # create an item representing the current maya scene
        item = self.collect_current_maya_scene(parent_item)

        # look for playblasts
        self.collect_playblasts(item, item.properties["project_root"])

        # look for caches
        self.collect_alembic_caches(item, item.properties["project_root"])

    def collect_current_maya_scene(self, parent_item):
        """
        Creates an item that represents the current maya scene.

        :param parent_item: Parent Item instance
        :returns: Item of type maya.scene
        """

        publisher = self.parent

        # get the path to the current file
        path = cmds.file(query=True, sn=True)

        # determine the display name for the item
        if path:
            path = os.path.abspath(path)
            display_name = os.path.basename(path)
        else:
            display_name = "Untitled Scene"
            # more pythonic empty file path
            path = None

        # discover the project root which helps in discovery of other
        # publishable items
        project_root = cmds.workspace(q=True, rootDirectory=True)

        # create the scene item for the publish hierarchy
        scene_item = parent_item.create_item(
            "maya.scene",
            "Current Maya Scene",
            display_name
        )

        scene_item.properties["path"] = path
        scene_item.properties["project_root"] = project_root
        scene_item.set_icon_from_path(publisher.get_icon_path("maya"))

        return scene_item

    def collect_alembic_caches(self, parent_item, project_root):
        """
        Creates items for alembic caches

        Looks for a 'project_root' property on the parent item, and if such
        exists, look for alembic caches in a 'cache/alembic' subfolder.

        :param parent_item: Parent Item instance
        :param str project_root: The maya project root to search for alembics

        :returns: List of alembic cache items
        """

        # use the workspace_root property on the parent to locate alembic caches
        items = []

        # ensure the alembic cache dir exists
        cache_dir = os.path.join(project_root, "cache", "alembic")
        if not os.path.exists(cache_dir):
            return items

        publisher = self.parent

        # look for alembic files in the cache directory
        for filename in os.listdir(cache_dir):
            cache_path = os.path.join(cache_dir, filename)

            # ensure this is an alembic cache
            if not cache_path.endswith(".abc"):
                continue

            # get file path parts for display
            file_info = publisher.util.get_file_path_components(cache_path)

            # create and populate the item
            item = parent_item.create_item(
                "cache.alembic",
                "Alembic Cache",
                file_info["filename_no_ext"]
            )
            item.properties["path"] = cache_path
            item.set_icon_from_path(publisher.get_icon_path("alembic"))
            items.append(item)

        return items

    def collect_playblasts(self, parent_item, project_root):
        """
        Creates items for quicktime playblasts.

        Looks for a 'project_root' property on the parent item, and if such
        exists, look for movie files in a 'movies' subfolder.

        :param parent_item: Parent Item instance
        :param str project_root: The maya project root to search for playblasts
        :returns: List of movie items
        """

        # use the workspace_root property on the parent to extract movies
        items = []

        # ensure the movies dir exists
        movies_dir = os.path.join(project_root, "movies")
        if not os.path.exists(movies_dir):
            return items

        publisher = self.parent

        # look for movie files in the movies directory
        for filename in os.listdir(movies_dir):
            movie_path = os.path.join(movies_dir, filename)

            # get file path parts for type checking and display
            file_info = publisher.util.get_file_path_components(movie_path)

            # ensure the file is of type video
            if not publisher.util.is_video(file_info["extension"]):
                continue

            # create the item
            item = parent_item.create_item(
                "maya.playblast",
                "Maya Playblast",  # override the display for specificity
                file_info["filename_no_ext"]
            )
            item.properties["path"] = movie_path
            item.set_icon_from_path(publisher.get_icon_path("movie"))
            items.append(item)

        return items

