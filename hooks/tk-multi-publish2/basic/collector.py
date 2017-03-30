# Copyright (c) 2017 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

import os

import sgtk

HookBaseClass = sgtk.get_hook_baseclass()


class GenericSceneCollector(HookBaseClass):
    """
    A generic collector that handles files and general objects.
    """

    def process_current_scene(self, parent_item):
        """
        Analyzes the current scene open in a DCC and parents a subtree of items
        under the parent_item passed in.

        :param parent_item: Root item instance
        """

        # default implementation does not do anything
        pass

    def process_file(self, parent_item, path):
        """
        Analyzes the given file and creates one or more items
        to represent it.

        :param parent_item: Root item instance
        :param path: Path to analyze
        :returns: The main item that was created
        """

        # handle files and folders differently
        if os.path.isdir(path):
            self._collect_folder(parent_item, path)
        else:
            self._collect_file(parent_item, path)

    def _collect_file(self, parent_item, path):
        """
        Process the supplied file path.

        :param parent_item: parent item instance
        :param path: Path to analyze
        :returns: The item that was created
        """

        publisher = self.parent
        publisher.logger.debug("Collecting file: %s" % (path,))

        # break down the path into the necessary pieces for processing
        file_info = publisher.util.get_file_path_components(path)

        # use the extension to determine item type (image, video, etc.)
        file_extension = file_info["extension"]

        # get display info for the extension
        (display, name) = publisher.util.get_file_type_info(file_extension)
        item_type = "file.%s" % (name,)
        icon_name = name

        # create and populate the item
        file_item = parent_item.create_item(
            item_type,
            display,
            file_info["filename"]
        )
        file_item.set_icon_from_path(publisher.get_icon_path(icon_name))

        # if it is an image, use the path to generate the thumbnail
        if name == "image":
            file_item.set_thumbnail_from_path(path)

        # all we know about the file is its path. set the path in its
        # properties for the plugins to use for processing
        file_item.properties["path"] = path

    def _collect_folder(self, parent_item, folder):
        """
        Process the supplied folder path.

        :param parent_item: parent item instance
        :param path: Path to analyze
        :returns: The item that was created
        """

        publisher = self.parent
        publisher.logger.debug("Collecting folder: %s" % (folder,))

        # see if the folder contains one or more image sequences. the paths
        # returned will contain frame formatting strings such as "%04d"
        img_seq_paths= publisher.util.get_image_sequence_paths(folder)

        if not img_seq_paths:

            # does not contain image sequences. publish the folder
            folder_info = publisher.util.get_file_path_components(folder)

            # create and populate an item for the folder
            folder_item = parent_item.create_item(
                "file.folder",
                "Generic Folder",
                folder_info["filename"]
            )
            folder_item.set_icon_from_path(publisher.get_icon_path("folder"))

            # all we know about the file is its path. set the path in its
            # properties for the plugins to use for processing
            folder_item.properties["path"] = folder

        # at least one image sequence found. create an item
        for img_seq_path in img_seq_paths:

            # break each seq path down into its components
            seq_path_info = publisher.util.get_file_path_components(
                img_seq_path)

            # create and populate an item for the folder
            img_seq_item = parent_item.create_item(
                "file.image.sequence",
                "Image Sequence",
                seq_path_info["filename"]
            )
            img_seq_item.set_icon_from_path(
                publisher.get_icon_path("image_sequence")
            )

            # all we know about the file is its path. set the path in its
            # properties for the plugins to use for processing
            img_seq_item.properties["path"] = img_seq_path
