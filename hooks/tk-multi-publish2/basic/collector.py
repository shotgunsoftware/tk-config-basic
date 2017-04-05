# Copyright (c) 2017 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

import mimetypes
import os

import sgtk

HookBaseClass = sgtk.get_hook_baseclass()

# This is a dictionary of file type info that allows the basic collector to
# identify common production file types and associate them with a display name,
# item type, and config icon.
COMMON_FILE_INFO = {
    "Alembic Cache": {
        "extensions": ["abc"],
        "icon": "alembic.png",
        "item_type": "file.alembic",
    },
    "3dsmax Scene": {
        "extensions": ["max"],
        "icon": "3dsmax.png",
        "item_type": "file.3dsmax",
    },
    "Hiero Project": {
        "extensions": ["hrox"],
        "icon": "hiero.png",
        "item_type": "file.hiero",
    },
    "Houdini Scene": {
        "extensions": ["hip", "hipnc"],
        "icon": "houdini.png",
        "item_type": "file.houdini",
    },
    "Maya Scene": {
        "extensions": ["ma", "mb"],
        "icon": "maya.png",
        "item_type": "file.maya",
    },
    "Nuke Script": {
        "extensions": ["nk"],
        "icon": "nuke.png",
        "item_type": "file.nuke",
    },
    "Photoshop Image": {
        "extensions": ["psd", "psb"],
        "icon": "photoshop.png",
        "item_type": "file.photoshop",
    },
    "Rendered Image": {
        "extensions": ["dpx", "exr"],
        "icon": "image_sequence.png",
        "item_type": "file.image",
    },
    "Texture": {
        "extensions": ["tiff", "tx", "tga", "dds"],
        "icon": "image.png",
        "item_type": "file.texture",
    },
}


class BasicSceneCollector(HookBaseClass):
    """
    A basic collector that handles files and general objects.
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

        # make sure the path is normalized. no trailing separator, separators
        # are appropriate for the current os, no double separators, etc.
        path = sgtk.util.ShotgunPath.normalize(path)

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

        # use the extension to determine item type
        filename = file_info["filename"]

        # get info for the extension
        (display_name, item_type, icon_path) = self._get_item_info(filename)
        publisher.logger.debug("ICON PATH: %s" % (icon_path,))

        # create and populate the item
        file_item = parent_item.create_item(item_type, display_name, filename)
        file_item.set_icon_from_path(icon_path)

        # if it is an image, use the path to generate the thumbnail
        if item_type == "file.image":
            file_item.set_thumbnail_from_path(path)

        # all we know about the file is its path. set the path in its
        # properties for the plugins to use for processing
        file_item.properties["path"] = path

    def _collect_folder(self, parent_item, folder):
        """
        Process the supplied folder path.

        :param parent_item: parent item instance
        :param folder: Path to analyze
        :returns: The item that was created
        """

        publisher = self.parent
        publisher.logger.debug("Collecting folder: %s" % (folder,))

        config_path = self.parent.sgtk.pipeline_configuration.get_path()

        # see if the folder contains one or more image sequences. the paths
        # returned will contain frame formatting strings such as "%04d"
        img_seq_paths = publisher.util.get_image_sequence_paths(folder)

        if not img_seq_paths:

            # does not contain image sequences. publish the folder
            folder_info = publisher.util.get_file_path_components(folder)

            # create and populate an item for the folder
            folder_item = parent_item.create_item(
                "file.folder",
                "Generic Folder",
                folder_info["filename"]
            )
            folder_item.set_icon_from_path(
                os.path.join(config_path, "config", "icons", "folder.png"))

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
                os.path.join(
                    config_path,
                    "config",
                    "icons",
                    "image_sequence.png"
                )
            )

            # all we know about the file is its path. set the path in its
            # properties for the plugins to use for processing
            img_seq_item.properties["path"] = img_seq_path

    def _get_item_info(self, filename):
        """
        Return a tuple of display name, item type, and icon path for the given
        filename.

        The method will try to identify the file as a common file type. If not,
        it will use the mimetype category. If the file still cannot be
        identified, it will fallback to a generic file type.

        :param filename: The file filename to identify type info for

        :return: A tuple of the form:

            (display_name, item_type, and icon_path)

        The item type will be of the form `file.<type>` where type is a specific
        common type or a generic classification of the file.
        """

        (_, extension) = os.path.splitext(filename)
        ext_no_dot = extension.lstrip(".")

        config_path = self.parent.sgtk.pipeline_configuration.get_path()

        # look for the extension in the common file type info dict
        for display_name in COMMON_FILE_INFO:
            type_info = COMMON_FILE_INFO[display_name]

            if ext_no_dot in type_info["extensions"]:

                # found the extension in the common types lookup. extract the
                # item type, icon path.
                item_type = type_info["item_type"]
                icon_name = type_info["icon"]
                icon_path = os.path.join(
                    config_path, "config", "icons", icon_name)

                # got everything we need. go ahead and return
                return display_name, item_type, icon_path

        # no match. check the extension's mimetype
        (category_type, _) = mimetypes.guess_type(filename)

        if category_type.startswith("image/"):
            # some type of image. return generic image type info.
            display_name = "Image"
            item_type = "file.image"
            icon_name = "image.png"

        elif category_type.startswith("video/"):
            # some type of movie. return generic movie type info.
            display_name = "Movie"
            item_type = "file.movie"
            icon_name = "movie.png"

        elif category_type.startswith("audio/"):
            # some type of audio. return generic audio type info.
            display_name = "Audio"
            item_type = "file.audio"
            icon_name = "audio.png"

        else:
            # fallback. just collect this as a generic file
            display_name = "File"
            item_type = "file.unknown"
            icon_name = "file.png"

        # construct a full path to the icon given the anem defined above
        icon_path = os.path.join(config_path, "config", "icons", icon_name)

        # everything should be populated, no matter what.
        return display_name, item_type, icon_path
