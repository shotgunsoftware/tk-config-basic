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

        publisher = self.parent
        publisher.engine.logger.debug("Processing file: %s" % (path,))

        # break down the path into the necessary pieces for processing
        components = publisher.util.get_file_path_components(path)

        # use the extension to determine category (image, video, etc.)
        file_extension = components["extension"]

        # get display info for the extension
        (display, name) = publisher.util.get_file_type_info(file_extension)
        category = "file.%s" % (name,)
        icon_name = name
        thumbnail = None

        if name == "image":
            thumbnail = path

        # create and populate the item
        file_item = parent_item.create_item(
            category,
            display,
            components["filename"]
        )
        file_item.set_icon_from_path(publisher.get_icon_path(icon_name))
        if thumbnail:
            file_item.set_thumbnail_from_path(thumbnail)

        # all we know about the file is its path. set the path in its
        # properties for the plugins to use for processing
        file_item.properties["path"] = path

        return file_item
